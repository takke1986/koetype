# KoeType

macOS用のローカル音声文字起こしアプリ。音声データは外部に送信されません。

## 特徴

- **⌘+Shift+Space** でどのアプリからでも音声入力
- **Cohere Transcribe**（2Bパラメータ）をローカルで実行
- **silero-vad** による正確な音声区間検出
- **専門用語登録**機能（メニューバー → 単語を登録）
- **Claude API** による句読点・文法整形（オプション）
- 音声データは完全にローカル処理（プライバシー重視）

## 動作環境

- macOS 13 以上
- Apple Silicon（M1〜）推奨
- メモリ 16GB 以上推奨（モデルが約4GB使用）
- [uv](https://docs.astral.sh/uv/) がインストール済みであること

## セットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/takke1986/koetype.git
cd aquavoice-local
```

### 2. 依存関係をインストール

```bash
uv sync
```

### 3. HuggingFaceにログイン（初回のみ）

Cohere Transcribeはゲートリポジトリのため、以下が必要：

1. https://huggingface.co/CohereLabs/cohere-transcribe-03-2026 でアクセスを承認
2. https://huggingface.co/settings/tokens でトークンを作成（Read権限）
3. ログイン:

```bash
uv run hf auth login
```

### 4. .app を作成して起動

```bash
bash build_app.sh
cp -r "KoeType.app" /Applications/
```

`/Applications/KoeType.app` をダブルクリックで起動。

### 5. macOS 権限を付与（初回のみ）

**システム設定 → プライバシーとセキュリティ** で以下を許可：

| 権限 | 対象 |
|---|---|
| マイク | KoeType |
| アクセシビリティ | KoeType |
| 入力監視 | KoeType |

## 使い方

| 操作 | 動作 |
|---|---|
| ⌘+Shift+Space | 録音 ON / OFF |
| メニューバー 🎙️ → 単語を登録 | 専門用語の追加・削除 |
| メニューバー 🎙️ → Claude後処理 | 句読点補正の ON/OFF |

### メニューバーのアイコン

| アイコン | 状態 |
|---|---|
| 🎙️ | 待機中 |
| 🔴 | 録音中（発話待ち） |
| 🔴🎤 | 発話を検出中 |
| ⚙️ | 文字起こし処理中 |
| ⏳ | モデルロード中（起動直後） |

## Claude API 後処理（オプション）

句読点の自動追加や文法整形を行う場合：

1. メニューバー → **Claude後処理** をON
2. `~/.koetype/settings.json` を編集:

```json
{
  "claude_postprocess": true,
  "anthropic_api_key": "sk-ant-..."
}
```

## 設定ファイル

設定・単語辞書は `~/.koetype/` に保存されます。

```
~/.koetype/
├── settings.json   # アプリ設定
└── terms.json      # 専門用語辞書
```

## ライセンス

MIT
