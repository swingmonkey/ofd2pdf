#!/usr/bin/env bash
# Download and extract taurusxin/Ofd2Pdf Windows EXE into bin/.
# This is primarily for Windows/Wine users; the backend expects Ofd2Pdf.exe.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$PROJECT_ROOT/bin"
ZIP_PATH="$BIN_DIR/Ofd2Pdf_1.2.zip"
EXE_PATH="$BIN_DIR/Ofd2Pdf.exe"
RELEASE_URL="https://github.com/taurusxin/Ofd2Pdf/releases/download/1.2.0.0/Ofd2Pdf_1.2.zip"

mkdir -p "$BIN_DIR"

if [ -f "$EXE_PATH" ]; then
    echo "Ofd2Pdf.exe already exists at $EXE_PATH"
    exit 0
fi

echo "Downloading $RELEASE_URL ..."
if command -v curl >/dev/null 2>&1; then
    curl -L --retry 3 -o "$ZIP_PATH" "$RELEASE_URL"
elif command -v wget >/dev/null 2>&1; then
    wget -O "$ZIP_PATH" "$RELEASE_URL"
else
    echo "Need curl or wget"
    exit 1
fi

echo "Extracting to $BIN_DIR ..."
unzip -o "$ZIP_PATH" -d "$BIN_DIR"
rm -f "$ZIP_PATH"

if [ ! -f "$EXE_PATH" ]; then
    NESTED=$(find "$BIN_DIR" -name "Ofd2Pdf.exe" | head -n1 || true)
    if [ -n "$NESTED" ]; then
        mv "$NESTED" "$EXE_PATH"
    else
        echo "Ofd2Pdf.exe not found after extraction"
        exit 1
    fi
fi

echo "Ofd2Pdf.exe installed at $EXE_PATH"
echo "Usage: ofd2pdf input.ofd -o output.pdf --backend taurusxin"
