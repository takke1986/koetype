"""
KoeType — メニューバー常駐の音声文字起こしアプリ

ホットキー: ⌘+Shift+Space で録音ON/OFF
結果はカーソル位置にそのまま貼り付け
"""

import subprocess
import sys
import threading
import time
from pathlib import Path

try:
    from ApplicationServices import AXIsProcessTrusted
    def _has_accessibility() -> bool:
        return bool(AXIsProcessTrusted())
except ImportError:
    def _has_accessibility() -> bool:
        return False

import numpy as np
import pyperclip
import rumps
from pynput import keyboard
from pynput.keyboard import Controller as KbController, Key

from audio_capture import AudioCapture
from config import apply_terms, load_settings, load_terms, save_settings
from postprocess import postprocess
from transcriber import Transcriber
from vad import CHUNK_SAMPLES, VADProcessor, is_hallucination

SAMPLE_RATE = 16000


def paste_text(text: str) -> None:
    """クリップボード経由でカーソル位置にテキストを挿入する。"""
    pyperclip.copy(text)
    time.sleep(0.1)
    kb = KbController()
    with kb.pressed(Key.cmd):
        kb.tap("v")


class AquaVoiceApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("🎙️", quit_button=None)

        self.settings = load_settings()
        self.transcriber: Transcriber | None = None
        self.audio = AudioCapture()
        self.is_recording = False

        # メニュー項目（参照を保持して後から更新）
        self._status = rumps.MenuItem("⏳ モデルをロード中...", callback=None)
        self._claude_item = rumps.MenuItem(
            self._claude_label(), callback=self.toggle_claude
        )

        self.menu = [
            self._status,
            None,
            self._claude_item,
            rumps.MenuItem("Claude後処理の設定...", callback=self.open_claude_settings),
            rumps.MenuItem("単語を登録...", callback=self.open_terms),
            rumps.MenuItem("マイク感度の調整...", callback=self.open_vad_settings),
            None,
            rumps.MenuItem("終了", callback=rumps.quit_application),
        ]

        # モデルをバックグラウンドでロード（起動を遅らせない）
        threading.Thread(target=self._load_model, daemon=True).start()

        # グローバルホットキー ⌘+Shift+Space（アクセシビリティ権限が必要）
        if _has_accessibility():
            hk = keyboard.GlobalHotKeys({"<cmd>+<shift>+<space>": self._on_hotkey})
            hk.daemon = True
            hk.start()
        else:
            self._status.title = "⚠️ アクセシビリティ権限が必要です"
            rumps.notification(
                "KoeType",
                "権限が必要です",
                "システム設定 → プライバシーとセキュリティ → アクセシビリティ と 入力監視 に KoeType を追加して再起動してください。",
            )

    # ---- 内部ユーティリティ ----

    def _claude_label(self) -> str:
        mark = "✓" if self.settings.claude_postprocess else "  "
        return f"{mark} Claude後処理"

    def _load_model(self) -> None:
        self.transcriber = Transcriber()
        self.title = "🎙️"
        self._status.title = "待機中（⌘+Shift+Space で開始）"

    # ---- ホットキー ----

    def _on_hotkey(self) -> None:
        if self.transcriber is None:
            return
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    # ---- 録音制御 ----

    def _start_recording(self) -> None:
        self.is_recording = True
        self.title = "🔴"
        self._status.title = "録音中..."
        self.audio.start()
        threading.Thread(target=self._process_loop, daemon=True).start()

    def _stop_recording(self) -> None:
        self.is_recording = False
        self.audio.stop()
        self.title = "🎙️"
        self._status.title = "待機中（⌘+Shift+Space で開始）"

    # ---- VAD + 推論ループ（バックグラウンドスレッド） ----

    def _process_loop(self) -> None:
        vad = VADProcessor(
            threshold=self.settings.vad_threshold,
            min_silence_ms=self.settings.min_silence_ms,
        )
        remainder = np.array([], dtype=np.float32)

        while self.is_recording:
            chunk = self.audio.get_chunk(timeout=0.1)
            if chunk is None:
                continue

            data = np.concatenate([remainder, chunk])
            n = len(data) // CHUNK_SAMPLES
            remainder = data[n * CHUNK_SAMPLES:]

            for i in range(n):
                c = data[i * CHUNK_SAMPLES: (i + 1) * CHUNK_SAMPLES]
                speaking_changed, audio = vad.process(c)

                if speaking_changed is True:
                    self.title = "🔴🎤"
                elif speaking_changed is False:
                    self.title = "⚙️"
                    self._status.title = "文字起こし中..."

                if audio is not None:
                    self._transcribe_and_insert(audio)
                    if self.is_recording:
                        self.title = "🔴"
                        self._status.title = "録音中..."

    def _transcribe_and_insert(self, audio: np.ndarray) -> None:
        terms = load_terms()
        print(f"[Debug] 音声長: {len(audio)/SAMPLE_RATE:.2f}s, 推論中...")
        text = self.transcriber.transcribe(audio, SAMPLE_RATE)
        print(f"[Debug] 認識結果: {repr(text)}")

        if not text:
            print("[Debug] 空文字のためスキップ")
            return
        if is_hallucination(text):
            print(f"[Debug] ハルシネーション判定でスキップ: {repr(text)}")
            return

        # 専門用語置換
        text = apply_terms(text, terms)

        # Claude後処理（オプション）
        has_creds = (
            self.settings.claude_provider == "bedrock"
            or bool(self.settings.anthropic_api_key)
        )
        if self.settings.claude_postprocess and has_creds:
            try:
                before = text
                text = postprocess(text, list(terms.values()), self.settings)
                print(f"[Claude] {self.settings.claude_provider}: {repr(before)} → {repr(text)}")
            except Exception as e:
                print(f"[Claude] エラー: {e}")

        paste_text(text)

    # ---- メニューコールバック ----

    def toggle_claude(self, _sender) -> None:
        # ONにするとき、Anthropic直接の場合はAPIキーが必要
        if not self.settings.claude_postprocess:
            if self.settings.claude_provider == "anthropic" and not self.settings.anthropic_api_key:
                response = rumps.Window(
                    title="Claude API キーを入力",
                    message="Anthropic APIキーを入力してください。\nhttps://console.anthropic.com/settings/keys\n\n※ Amazon Bedrockを使う場合は「Claude後処理の設定...」から変更できます。",
                    default_text="sk-ant-...",
                    ok="保存",
                    cancel="キャンセル",
                    dimensions=(400, 24),
                ).run()
                if not response.clicked or not response.text.strip().startswith("sk-"):
                    rumps.notification("KoeType", "", "APIキーが未設定のため Claude後処理をONにできません")
                    return
                self.settings.anthropic_api_key = response.text.strip()

        self.settings.claude_postprocess = not self.settings.claude_postprocess
        save_settings(self.settings)
        self._claude_item.title = self._claude_label()

    def open_claude_settings(self, _sender) -> None:
        subprocess.Popen([sys.executable, str(Path(__file__).parent / "claude_settings_ui.py")])

    def open_vad_settings(self, _sender) -> None:
        subprocess.Popen([sys.executable, str(Path(__file__).parent / "vad_settings_ui.py")])

    def open_terms(self, _sender) -> None:
        subprocess.Popen([sys.executable, str(Path(__file__).parent / "terms_ui.py")])


if __name__ == "__main__":
    AquaVoiceApp().run()
