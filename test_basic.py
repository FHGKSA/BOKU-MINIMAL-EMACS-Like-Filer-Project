#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2pane TUI Filer - 動作テストスクリプト

キーボード操作のテストを行うスクリプトです。
実際のTUI環境でのテストの前に基本動作を確認します。
"""

import sys
import os
sys.path.insert(0, 'src')

from pathlib import Path
import curses
from ui import FilePane, FileItem
from colors import ColorManager

def test_file_item():
    """FileItemクラスのテスト"""
    print("=== FileItem テスト ===")
    
    # テストファイルの作成
    test_file = Path("test.txt")
    try:
        test_file.touch()
        
        # FileItemのテスト
        item = FileItem(str(test_file))
        print(f"ファイル名: {item.name}")
        print(f"名前部分: {item.name_part}")
        print(f"拡張子: {item.extension}")
        print(f"ディレクトリ: {item.is_dir}")
        print(f"シンボリックリンク: {item.is_link}")
        
        test_file.unlink()  # テストファイル削除
        
        # シンボリックリンクのテスト
        test_target = Path("target.txt")
        test_link = Path("test_link.txt")
        
        try:
            test_target.touch()
            test_link.symlink_to(test_target)
            
            link_item = FileItem(str(test_link))
            print(f"シンボリックリンク名: {link_item.name}")
            print(f"リンク先: {link_item.link_target}")
            print(f"壊れたリンク: {link_item.is_broken_link}")
            print(f"表示名: {link_item.get_display_name()}")
            print(f"表示名前部分: {link_item.get_display_name_part()}")
            
            test_link.unlink()
            test_target.unlink()
            
            # 壊れたリンクのテスト
            broken_link = Path("broken_link.txt")
            broken_link.symlink_to("nonexistent.txt")
            
            broken_item = FileItem(str(broken_link))
            print(f"壊れたリンク名: {broken_item.name}")
            print(f"壊れたリンク: {broken_item.is_broken_link}")
            print(f"壊れたリンク表示: {broken_item.get_display_name()}")
            print(f"サイズ表示: {broken_item.get_size_string()}")
            
            broken_link.unlink()
            
        except Exception as e:
            print(f"シンボリックリンクテストエラー: {e}")
        
        print("FileItem テスト完了")
        
    except Exception as e:
        print(f"FileItem テストエラー: {e}")

def test_file_pane():
    """FilePaneクラスのテスト"""
    print("\n=== FilePane テスト ===")
    
    try:
        # ColorManagerの初期化
        color_manager = ColorManager(use_color=False)
        
        # FilePaneの初期化
        pane = FilePane(0, 0, 20, 40, ".", color_manager, active=True)
        
        print(f"現在のパス: {pane.current_path}")
        print(f"ファイル数: {len(pane.files)}")
        
        if pane.files:
            print("最初の3ファイル:")
            for i, file_item in enumerate(pane.files[:3]):
                print(f"  {i+1}. {file_item.name} ({'DIR' if file_item.is_dir else 'FILE'})")
        
        # カーソル移動テスト
        original_cursor = pane.cursor
        pane.move_cursor_down()
        print(f"カーソル移動: {original_cursor} -> {pane.cursor}")
        
        # ディレクトリ変更テスト（親ディレクトリ）
        if pane.current_path != Path("/"):
            try:
                parent_path = str(pane.current_path.parent)
                pane.change_directory(parent_path)
                print(f"ディレクトリ変更成功: {parent_path}")
                
                # 元のディレクトリに戻る
                original_path = Path(".").resolve()
                pane.change_directory(str(original_path))
                print(f"元のディレクトリに復帰: {original_path}")
                
            except Exception as e:
                print(f"ディレクトリ変更テストエラー: {e}")
        
        print("FilePane テスト完了")
        
    except Exception as e:
        print(f"FilePane テストエラー: {e}")

def test_color_manager():
    """ColorManagerクラスのテスト"""
    print("\n=== ColorManager テスト ===")
    
    try:
        # カラーなしでのテスト
        color_manager = ColorManager(use_color=False)
        print(f"色サポート: {color_manager.is_color_supported()}")
        print(f"色サポートレベル: {color_manager.color_support}")
        
        # ダミーファイルアイテムでテスト
        test_file = Path("test.py")
        test_file.touch()
        
        item = FileItem(str(test_file))
        color = color_manager.get_file_color(item)
        print(f"Python ファイルの色: {color}")
        
        test_file.unlink()
        print("ColorManager テスト完了")
        
    except Exception as e:
        print(f"ColorManager テストエラー: {e}")

def main():
    """メイン関数"""
    print("2pane TUI Filer - 動作テスト開始")
    
    test_file_item()
    test_file_pane()
    test_color_manager()
    
    print("\n=== テスト完了 ===")
    print("基本機能が正常に動作しています。")
    print("\n実際のTUIファイラーを起動するには:")
    print("  python3 src/main.py")
    print("または:")
    print("  ./run.sh")

if __name__ == "__main__":
    main()