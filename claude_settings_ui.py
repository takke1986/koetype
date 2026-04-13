"""Claude後処理設定ウィンドウ（別プロセスで起動）。"""

import sys
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

# 別プロセスとして起動されるため、パスを追加
sys.path.insert(0, str(Path(__file__).parent))

from config import load_settings, save_settings


def main() -> None:
    settings = load_settings()

    root = tk.Tk()
    root.title("Claude後処理の設定 — AquaVoice Local")
    root.geometry("480x320")
    root.resizable(False, False)

    pad = {"padx": 12, "pady": 6}

    # ---- プロバイダー選択 ----
    provider_frame = ttk.LabelFrame(root, text="APIプロバイダー", padding=10)
    provider_frame.pack(fill=tk.X, padx=12, pady=(12, 4))

    provider_var = tk.StringVar(value=settings.claude_provider)

    ttk.Radiobutton(
        provider_frame, text="Anthropic（直接）", variable=provider_var, value="anthropic",
        command=lambda: _on_provider_change()
    ).pack(anchor=tk.W)
    ttk.Radiobutton(
        provider_frame, text="Amazon Bedrock（AWSクレデンシャル使用）", variable=provider_var, value="bedrock",
        command=lambda: _on_provider_change()
    ).pack(anchor=tk.W, pady=(4, 0))

    # ---- Anthropic APIキー ----
    anthropic_frame = ttk.LabelFrame(root, text="Anthropic APIキー", padding=10)
    anthropic_frame.pack(fill=tk.X, padx=12, pady=4)

    api_key_var = tk.StringVar(value=settings.anthropic_api_key)
    api_key_entry = ttk.Entry(anthropic_frame, textvariable=api_key_var, width=50, show="*")
    api_key_entry.pack(fill=tk.X)
    ttk.Label(
        anthropic_frame, text="https://console.anthropic.com/settings/keys",
        foreground="gray", font=("", 10)
    ).pack(anchor=tk.W, pady=(2, 0))

    # ---- Bedrock設定 ----
    bedrock_frame = ttk.LabelFrame(root, text="Amazon Bedrock 設定", padding=10)
    bedrock_frame.pack(fill=tk.X, padx=12, pady=4)

    bedrock_frame.columnconfigure(1, weight=1)

    ttk.Label(bedrock_frame, text="リージョン:").grid(row=0, column=0, sticky=tk.W, pady=2)
    region_var = tk.StringVar(value=settings.aws_region)
    ttk.Entry(bedrock_frame, textvariable=region_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=(8, 0))

    ttk.Label(bedrock_frame, text="モデルID:").grid(row=1, column=0, sticky=tk.W, pady=2)
    model_var = tk.StringVar(value=settings.bedrock_model_id)
    ttk.Entry(bedrock_frame, textvariable=model_var, width=44).grid(row=1, column=1, sticky=tk.EW, padx=(8, 0))

    ttk.Label(
        bedrock_frame,
        text="AWSクレデンシャルは ~/.aws/credentials または環境変数から自動取得",
        foreground="gray", font=("", 10)
    ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

    def _on_provider_change() -> None:
        p = provider_var.get()
        if p == "anthropic":
            api_key_entry.config(state="normal")
            for child in bedrock_frame.winfo_children():
                try:
                    child.config(state="disabled")
                except tk.TclError:
                    pass
        else:
            api_key_entry.config(state="disabled")
            for child in bedrock_frame.winfo_children():
                try:
                    child.config(state="normal")
                except tk.TclError:
                    pass

    _on_provider_change()

    # ---- 保存ボタン ----
    def save() -> None:
        settings.claude_provider = provider_var.get()
        settings.anthropic_api_key = api_key_var.get().strip()
        settings.aws_region = region_var.get().strip()
        settings.bedrock_model_id = model_var.get().strip()

        if settings.claude_provider == "anthropic" and settings.claude_postprocess:
            if not settings.anthropic_api_key.startswith("sk-"):
                messagebox.showwarning("入力エラー", "Anthropic APIキーを正しく入力してください（sk-ant- で始まる文字列）", parent=root)
                return

        save_settings(settings)
        messagebox.showinfo("保存完了", "設定を保存しました。\nAquaVoice Local を再起動すると反映されます。", parent=root)
        root.destroy()

    btn_frame = ttk.Frame(root, padding=(12, 8, 12, 12))
    btn_frame.pack(fill=tk.X)
    ttk.Button(btn_frame, text="保存", command=save).pack(side=tk.RIGHT)
    ttk.Button(btn_frame, text="キャンセル", command=root.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    root.mainloop()


if __name__ == "__main__":
    main()
