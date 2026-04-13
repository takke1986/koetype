#!/bin/bash
set -e

APP_NAME="KoeType"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLE="$PROJECT_DIR/$APP_NAME.app"
MACOS="$BUNDLE/Contents/MacOS"
RESOURCES="$BUNDLE/Contents/Resources"

# 既存のバンドルを削除
rm -rf "$BUNDLE"
mkdir -p "$MACOS" "$RESOURCES"

echo "🔨 $APP_NAME.app を構築中..."

# ---- ランチャースクリプト ----
cat > "$MACOS/KoeTypeLocal" << SCRIPT
#!/bin/bash

PROJECT_DIR="$PROJECT_DIR"

# uv のパスを探す（Finder起動時はPATHが限定的なため明示的に探す）
for UV_PATH in "\$HOME/.local/bin/uv" "/usr/local/bin/uv" "/opt/homebrew/bin/uv"; do
    if [ -f "\$UV_PATH" ]; then
        UV="\$UV_PATH"
        break
    fi
done

if [ -z "\${UV:-}" ]; then
    osascript -e 'display alert "KoeType" message "uv が見つかりません。\nターミナルで以下を実行してください:\ncurl -LsSf https://astral.sh/uv/install.sh | sh"'
    exit 1
fi

cd "\$PROJECT_DIR"
exec "\$UV" run python main.py
SCRIPT

chmod +x "$MACOS/KoeTypeLocal"

# ---- Info.plist ----
cat > "$BUNDLE/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>KoeTypeLocal</string>
    <key>CFBundleIdentifier</key>
    <string>com.taketaka.koetype</string>
    <key>CFBundleName</key>
    <string>KoeType</string>
    <key>CFBundleDisplayName</key>
    <string>KoeType</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>LSUIElement</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>NSMicrophoneUsageDescription</key>
    <string>音声文字起こしのためにマイクを使用します。</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>テキスト入力のために使用します。</string>
</dict>
</plist>
PLIST

echo ""
echo "✅ 完成: $BUNDLE"
echo ""
echo "【次のステップ】"
echo "  1. アプリを Applications にコピー:"
echo "     cp -r \"$BUNDLE\" /Applications/"
echo ""
echo "  2. /Applications/KoeType.app をダブルクリックして起動"
echo ""
echo "  3. システム設定 → プライバシーとセキュリティ で以下を許可:"
echo "     - アクセシビリティ  → KoeType"
echo "     - 入力監視          → KoeType"
echo "     - マイク            → KoeType"
echo ""
echo "  4. Terminal ではなく KoeType として権限を付与するため"
echo "     Terminal の権限は削除しても OK です"
