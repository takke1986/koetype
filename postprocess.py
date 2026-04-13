"""Claude API による文字起こし後処理。Anthropic直接 / Amazon Bedrock 両対応。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import Settings

SYSTEM_PROMPT = """あなたは音声文字起こしの編集者です。
以下のルールに従って文章を整えてください。

【必ず行うこと】
- フィラーワードを除去する（えーと、えー、あの、まあ、なんか、そのー、うーん、あー 等）
- 言い直し・繰り返しを修正する（例：「これは、これはつまり」→「これはつまり」）
- 途中でやり直した箇所をきれいにまとめる（例：「明日、あ違う、来週の会議で」→「来週の会議で」）
- 句読点を適切に追加する

【やってはいけないこと】
- 意味・内容を変える
- 情報を追加・削除する（フィラー・言い直し以外）
- 敬語や文体を変える

整えた文章のみを返してください。説明や補足は不要です。"""


def postprocess(text: str, terms: list[str], settings: Settings) -> str:
    user_content = text
    if terms:
        user_content = f"【専門用語リスト】{', '.join(terms)}\n\n{text}"

    if settings.claude_provider == "bedrock":
        from anthropic import AnthropicBedrock
        client = AnthropicBedrock(aws_region=settings.aws_region)
        model = settings.bedrock_model_id
    else:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        model = "claude-haiku-4-5-20251001"  # 速度重視

    msg = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    return msg.content[0].text.strip()
