#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2pane TUI Filer - メインファイラークラス

このモジュールは2ペインファイラーの中核機能を実装します。
"""

import curses
import os
import sys
from pathlib import Path
from typing import Optional, Tuple, List
import locale

from ui import FilePane, StatusBar, CommandLine
from file_ops import FileOperations
from colors import ColorManager
from config import Config


class TwoPaneFiler:
    """2ペインTUIファイラーのメインクラス"""
    
    def __init__(self, left_path: str, right_path: str, 
                 use_color: bool = True, debug: bool = False):
        """
        初期化
        
        Args:
            left_path: 左ペインの初期パス
            right_path: 右ペインの初期パス 
            use_color: 色分けを使用するか
            debug: デバッグモードか
        """
        self.left_path = Path(left_path)
        self.right_path = Path(right_path)
        self.use_color = use_color
        self.debug = debug
        
        # 内部状態
        self.active_pane = 'left'  # 'left' or 'right'
        self.left_pane = None
        self.right_pane = None
        self.status_bar = None
        self.command_line = None
        self.should_exit = False
        
        # モード管理
        self.mode = 'normal'  # 'normal', 'search', 'edit', 'dialog'
        self.command_buffer = ""
        
        # コンポーネント
        self.config = None
        self.color_manager = None
        self.file_ops = None
        
        # 日本語対応
        locale.setlocale(locale.LC_ALL, '')

    def initialize_components(self, stdscr):
        """各コンポーネントの初期化"""
        self.stdscr = stdscr
        
        # cursesの基本設定
        curses.curs_set(0)  # カーソル非表示
        curses.noecho()     # 自動エコー無効
        curses.cbreak()     # 文字単位入力
        stdscr.keypad(True) # 特殊キー有効
        
        # 画面サイズ取得
        self.max_y, self.max_x = stdscr.getmaxyx()
        
        # 最小サイズチェック
        if self.max_y < 10 or self.max_x < 40:
            raise Exception(f"ターミナルサイズが小さすぎます: {self.max_y}x{self.max_x}")
        
        # コンフィグ初期化
        self.config = Config()
        
        # カラーマネージャー初期化
        self.color_manager = ColorManager(self.use_color)
        
        # ファイル操作マネージャー初期化
        self.file_ops = FileOperations()
        
        # UIコンポーネント初期化
        self._initialize_ui_components()

    def _initialize_ui_components(self):
        """UIコンポーネントの初期化"""
        # 画面レイアウト計算
        pane_width = (self.max_x - 1) // 2  # 中央の区切り線分を除く
        pane_height = self.max_y - 2        # ステータス行とコマンド行分を除く
        
        # 左ペイン
        self.left_pane = FilePane(
            start_y=0, 
            start_x=0, 
            height=pane_height,
            width=pane_width,
            path=str(self.left_path),
            color_manager=self.color_manager,
            active=True if self.active_pane == 'left' else False
        )
        
        # 右ペイン
        self.right_pane = FilePane(
            start_y=0,
            start_x=pane_width + 1,  # 区切り線の分を追加
            height=pane_height,
            width=pane_width,
            path=str(self.right_path),
            color_manager=self.color_manager,
            active=True if self.active_pane == 'right' else False
        )
        
        # ステータスバー
        self.status_bar = StatusBar(
            start_y=self.max_y - 2,
            start_x=0,
            width=self.max_x,
            color_manager=self.color_manager
        )
        
        # コマンドライン
        self.command_line = CommandLine(
            start_y=self.max_y - 1,
            start_x=0,
            width=self.max_x,
            color_manager=self.color_manager
        )

    def run(self, stdscr):
        """メインループ実行"""
        try:
            self.initialize_components(stdscr)
            self.draw_initial_screen()
            
            # メインループ
            while not self.should_exit:
                self.handle_input()
                self.update_display()
                
        except Exception as e:
            # デバッグモード時は詳細エラー表示
            if self.debug:
                import traceback
                error_msg = f"エラー: {str(e)}\n{traceback.format_exc()}"
            else:
                error_msg = f"エラー: {str(e)}"
            
            # cursesを終了してからエラー表示
            curses.endwin()
            print(error_msg, file=sys.stderr)
            sys.exit(1)

    def draw_initial_screen(self):
        """初期画面描画"""
        self.stdscr.clear()
        
        # ペイン描画
        self.left_pane.draw(self.stdscr)
        self.right_pane.draw(self.stdscr)
        
        # 中央区切り線
        self._draw_separator()
        
        # ステータスバー描画
        self.status_bar.draw(self.stdscr, self._get_status_info())
        
        # コマンドライン描画
        self.command_line.draw(self.stdscr, "2pane TUI Filer - Ready")
        
        self.stdscr.refresh()

    def _draw_separator(self):
        """ペイン間の区切り線描画"""
        sep_x = (self.max_x - 1) // 2
        
        for y in range(self.max_y - 2):
            try:
                self.stdscr.addch(y, sep_x, '|')
            except curses.error:
                pass  # 画面端での描画エラーを無視

    def handle_input(self):
        """入力処理"""
        try:
            key = self.stdscr.getch()
            
            # モード別入力処理
            if self.mode == 'normal':
                self._handle_normal_mode_input(key)
            elif self.mode == 'search':
                self._handle_search_mode_input(key)
            elif self.mode == 'edit':
                self._handle_edit_mode_input(key)
            elif self.mode == 'dialog':
                self._handle_dialog_mode_input(key)
                
        except curses.error:
            pass  # 入力エラーを無視

    def _handle_normal_mode_input(self, key):
        """ノーマルモードでの入力処理"""
        # Ctrl+G: キャンセル
        if key == 7:  # Ctrl+G
            self.command_buffer = ""
            self.command_line.clear()
            return
        
        # ESC: キャンセル（2回でアプリ終了確認）
        if key == 27:  # ESC
            self._handle_escape_key()
            return
        
        # カーソル移動 - Emacsスタイル
        if key == 16:  # Ctrl+P: 上
            self._move_cursor_up()
        elif key == 14:  # Ctrl+N: 下
            self._move_cursor_down()
        elif key in [1, 2]:  # Ctrl+A, Ctrl+B: 左ペイン
            self._switch_to_left_pane()
        elif key in [5, 6]:  # Ctrl+E, Ctrl+F: 右ペイン
            self._switch_to_right_pane()
        elif key == 9:  # TAB: ペイン切り替え
            self._toggle_active_pane()
        
        # カーソル移動 - カーソルキー
        elif key == curses.KEY_UP:
            self._move_cursor_up()
        elif key == curses.KEY_DOWN:
            self._move_cursor_down()
        elif key == curses.KEY_LEFT:
            self._switch_to_left_pane()
        elif key == curses.KEY_RIGHT:
            self._switch_to_right_pane()
        
        # ファイル操作
        elif key == ord('D') or key == ord('d'):
            self._delete_file()
        elif key == ord('M') or key == ord('m'):
            self._move_file()
        elif key == ord('C') or key == ord('c'):
            self._copy_file()
        elif key == ord('R') or key == ord('r'):
            self._rename_file()
        
        # その他のキー
        elif key == 10 or key == 13:  # Enter
            self._open_file()
        elif key == ord(' '):  # Space: ファイル選択
            self._toggle_file_selection()

    def _handle_escape_key(self):
        """ESCキーの処理（2回で終了確認）"""
        # 実装予定: ESC2回連打での終了確認
        self.should_exit = True

    def _move_cursor_up(self):
        """カーソル上移動"""
        active_pane = self.left_pane if self.active_pane == 'left' else self.right_pane
        active_pane.move_cursor_up()

    def _move_cursor_down(self):
        """カーソル下移動"""
        active_pane = self.left_pane if self.active_pane == 'left' else self.right_pane
        active_pane.move_cursor_down()

    def _switch_to_left_pane(self):
        """左ペインに切り替え"""
        if self.active_pane != 'left':
            self.active_pane = 'left'
            self.left_pane.set_active(True)
            self.right_pane.set_active(False)

    def _switch_to_right_pane(self):
        """右ペインに切り替え"""
        if self.active_pane != 'right':
            self.active_pane = 'right'
            self.left_pane.set_active(False)
            self.right_pane.set_active(True)

    def _toggle_active_pane(self):
        """アクティブペインの切り替え"""
        if self.active_pane == 'left':
            self._switch_to_right_pane()
        else:
            self._switch_to_left_pane()

    def _delete_file(self):
        """ファイル削除（実装予定）"""
        pass

    def _move_file(self):
        """ファイル移動（実装予定）"""  
        pass

    def _copy_file(self):
        """ファイルコピー（実装予定）"""
        pass

    def _rename_file(self):
        """ファイルリネーム（実装予定）"""
        pass

    def _open_file(self):
        """ファイル開く・ディレクトリ移動"""
        active_pane = self.left_pane if self.active_pane == 'left' else self.right_pane
        current_file = active_pane.get_current_file()
        
        if not current_file:
            return
        
        if current_file.is_dir:
            # ディレクトリの場合は移動
            try:
                new_path = str(current_file.path)
                active_pane.change_directory(new_path)
                
                # ステータス行で結果を表示
                self.command_line.draw(self.stdscr, f"Entered directory: {new_path}")
                
            except Exception as e:
                self.command_line.draw(self.stdscr, f"Error: {str(e)}")
        else:
            # ファイルの場合は将来実装予定
            self.command_line.draw(self.stdscr, f"File: {current_file.name} (opening not implemented yet)")

    def _toggle_file_selection(self):
        """ファイル選択切り替え（実装予定）"""
        pass

    def _handle_search_mode_input(self, key):
        """検索モードでの入力処理（実装予定）"""
        pass

    def _handle_edit_mode_input(self, key):
        """編集モードでの入力処理（実装予定）"""
        pass

    def _handle_dialog_mode_input(self, key):
        """ダイアログモードでの入力処理（実装予定）"""
        pass

    def update_display(self):
        """表示更新"""
        self.stdscr.clear()
        
        # ペイン描画
        self.left_pane.draw(self.stdscr)
        self.right_pane.draw(self.stdscr)
        
        # 区切り線
        self._draw_separator()
        
        # ステータスバー
        self.status_bar.draw(self.stdscr, self._get_status_info())
        
        # コマンドライン
        msg = f"Mode: {self.mode} | Active: {self.active_pane}"
        self.command_line.draw(self.stdscr, msg)
        
        self.stdscr.refresh()

    def _get_status_info(self) -> dict:
        """ステータス情報取得"""
        active_pane = self.left_pane if self.active_pane == 'left' else self.right_pane
        
        # 現在のパス取得
        left_current_path = str(self.left_pane.current_path) if self.left_pane else ""
        right_current_path = str(self.right_pane.current_path) if self.right_pane else ""
        
        return {
            'left_path': left_current_path,
            'right_path': right_current_path,
            'active_pane': self.active_pane,
            'current_path': str(active_pane.current_path) if active_pane else "",
            'mode': self.mode
        }