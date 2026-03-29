#!/bin/bash
# 2pane TUI Filer 実行スクリプト

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Python3の確認
if ! command -v python3 &> /dev/null; then
    echo "エラー: Python3がインストールされていません。"
    echo "Ubuntu系の場合: sudo apt install python3"
    exit 1
fi

# Python バージョン確認
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.7"

if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)"; then
    echo "Python $PYTHON_VERSION を使用"
else
    echo "エラー: Python $REQUIRED_VERSION 以上が必要です。現在: $PYTHON_VERSION"
    exit 1
fi

# cursesサポート確認
if python3 -c "import curses" 2>/dev/null; then
    echo "cursesライブラリOK"
else
    echo "エラー: cursesライブラリがサポートされていません。"
    echo "Ubuntu系の場合: sudo apt install python3-dev"
    exit 1
fi

# ターミナルサイズ確認
if command -v stty &> /dev/null; then
    read rows cols < <(stty size 2>/dev/null)
    if [[ "$rows" -lt 10 || "$cols" -lt 40 ]]; then
        echo "警告: ターミナルサイズが小さいです (${rows}x${cols})"
        echo "推奨サイズ: 24行 x 80列以上"
    fi
fi

# メイン実行
echo "2pane TUI Filer を開始..."
exec python3 "$SCRIPT_DIR/src/main.py" "$@"