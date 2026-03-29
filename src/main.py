#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2pane TUI Filer - メインエントリーポイント

このファイラーはLinuxのMidnight CommanderやWindowsの「あふ」を
参考にした2ペイン型のTUIファイラーです。

主な特徴:
- Emacsスタイルのキーバインド
- byobu(tmux)との競合回避
- ls --color=auto互換の色分け
- UTF-8/Shift_JIS混在環境対応
- 軽量で高速な動作
"""

import sys
import os
import curses
import argparse
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from filer import TwoPaneFiler


def parse_arguments():
    """コマンドライン引数の解析"""
    parser = argparse.ArgumentParser(
        description='2pane TUI Filer - Emacs風キーバインドの2ペインファイラー'
    )
    
    parser.add_argument(
        'left_path', 
        nargs='?', 
        default=os.getcwd(),
        help='左ペインの初期ディレクトリ（デフォルト: カレントディレクトリ）'
    )
    
    parser.add_argument(
        'right_path', 
        nargs='?', 
        default=os.getcwd(),
        help='右ペインの初期ディレクトリ（デフォルト: カレントディレクトリ）'
    )
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='色分けを無効にする'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='デバッグモードを有効にする'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='2pane TUI Filer v0.1.0'
    )
    
    return parser.parse_args()


def check_terminal_support():
    """ターミナルサポートの確認"""
    # 最小ターミナルサイズのチェック
    try:
        rows, cols = os.popen('stty size', 'r').read().split()
        if int(rows) < 10 or int(cols) < 40:
            print("警告: ターミナルサイズが小さすぎます（最小: 10行x40列）", 
                  file=sys.stderr)
            return False
    except:
        pass  # sttyが利用できない環境では無視

    # cursesサポートの確認
    try:
        curses.initscr()
        curses.endwin()
        return True
    except curses.error:
        print("エラー: cursesライブラリがサポートされていません", 
              file=sys.stderr)
        return False


def main():
    """メイン関数"""
    try:
        args = parse_arguments()
        
        # ターミナルサポートの確認
        if not check_terminal_support():
            sys.exit(1)
        
        # パスの検証
        left_path = Path(args.left_path).resolve()
        right_path = Path(args.right_path).resolve()
        
        if not left_path.exists() or not left_path.is_dir():
            print(f"エラー: 左ペインの初期パスが存在しません: {left_path}", 
                  file=sys.stderr)
            sys.exit(1)
            
        if not right_path.exists() or not right_path.is_dir():
            print(f"エラー: 右ペインの初期パスが存在しません: {right_path}", 
                  file=sys.stderr)
            sys.exit(1)
        
        # ファイラーの初期化と実行
        filer = TwoPaneFiler(
            left_path=str(left_path),
            right_path=str(right_path),
            use_color=not args.no_color,
            debug=args.debug
        )
        
        # cursesアプリケーションとして実行
        curses.wrapper(filer.run)
        
    except KeyboardInterrupt:
        print("\n中止されました。")
        sys.exit(0)
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()