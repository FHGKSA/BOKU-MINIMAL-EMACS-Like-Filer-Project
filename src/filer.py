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

from ui import FilePane, StatusBar, CommandLine, InWindowDialog, TransferQueueView, get_display_width, truncate_string_by_width
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
        self.mode = 'normal'  # 'normal', 'search', 'edit', 'dialog', 'in_window', 'transfer_queue'
        self.command_buffer = ""
        
        # 操作状態
        self.operation_progress = None
        self.operation_message = ""
        self.operation_thread = None
        
        # 確認ダイアログ
        self.dialog_message = ""
        self.dialog_options = []
        self.dialog_selected = 0
        
        # In-Window ダイアログ
        self.in_window = None
        self.in_window_selected = 0
        
        # 転送キュー画面
        self.transfer_queue_view = None
        self.transfer_queue_selected = 0
        
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
            elif self.mode == 'in_window':
                self._handle_in_window_input(key)
            elif self.mode == 'transfer_queue':
                self._handle_transfer_queue_input(key)
                
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
            self._cursor_up_handled = True  # 重複処理フラグ
        elif key == 14:  # Ctrl+N: 下
            self._move_cursor_down()
        elif key == 1:  # Ctrl+A: 左ペイン
            self._switch_to_left_pane()
        elif key == 2:  # Ctrl+B: 左ペインで親ディレクトリ移動、右ペインで左ペイン切り替え
            if self.active_pane == 'left':
                self._go_to_parent_directory()
            else:
                self._switch_to_left_pane()
        elif key == 5:  # Ctrl+E: 右ペイン
            self._switch_to_right_pane()
        elif key == 6:  # Ctrl+F: 右ペインで親ディレクトリ移動、左ペインで右ペイン切り替え
            if self.active_pane == 'right':
                self._go_to_parent_directory()
            else:
                self._switch_to_right_pane()
        elif key == 9:  # TAB: ペイン切り替え
            self._toggle_active_pane()
        
        # カーソル移動 - カーソルキー
        elif key == curses.KEY_UP:
            self._move_cursor_up()
        elif key == curses.KEY_DOWN:
            self._move_cursor_down()
        elif key == curses.KEY_LEFT:
            # 左ペインで左キーは親ディレクトリ移動、右ペインでは左ペイン切り替え
            if self.active_pane == 'left':
                self._go_to_parent_directory()
            else:
                self._switch_to_left_pane()
        elif key == curses.KEY_RIGHT:
            # 右ペインで右キーは親ディレクトリ移動、左ペインでは右ペイン切り替え
            if self.active_pane == 'right':
                self._go_to_parent_directory()
            else:
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
        elif key == ord('K') or key == ord('k'):
            self._create_directory()
        
        # バックグラウンド転送制御
        elif key == 17:  # Ctrl+Q: 転送キュー表示
            self._show_transfer_queue()
        elif key == 16:  # Ctrl+P: 転送一時停止/再開（重複チェック後に処理）
            if hasattr(self, '_cursor_up_handled'):
                # すでにカーソル移動で処理済みの場合はスキップ
                delattr(self, '_cursor_up_handled')
            else:
                self._toggle_transfer_pause()
        elif key == 24:  # Ctrl+X: 転送キャンセル
            self._cancel_current_transfer()
        
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

    def _go_to_parent_directory(self):
        """親ディレクトリに移動"""
        active_pane = self.left_pane if self.active_pane == 'left' else self.right_pane
        
        try:
            if active_pane.go_to_parent_directory():
                # 親ディレクトリに移動成功
                self.command_line.draw(self.stdscr, f"親ディレクトリに移動: {active_pane.current_path}")
                # 1秒後にメッセージをクリア
                import time
                import threading
                def clear_message():
                    time.sleep(1)
                    self.command_line.draw(self.stdscr, "")
                threading.Thread(target=clear_message, daemon=True).start()
            else:
                # ルートディレクトリなど、移動できない場合
                self.command_line.draw(self.stdscr, "これ以上上に移動できません")
                # 1秒後にメッセージをクリア
                import time
                import threading
                def clear_message():
                    time.sleep(1)
                    self.command_line.draw(self.stdscr, "")
                threading.Thread(target=clear_message, daemon=True).start()
        except Exception as e:
            self.command_line.draw(self.stdscr, f"親ディレクトリ移動エラー: {str(e)}")

    def _delete_file(self):
        """ファイル削除"""
        active_pane = self.left_pane if self.active_pane == 'left' else self.right_pane
        current_file = active_pane.get_current_file()
        
        if not current_file:
            self.command_line.draw(self.stdscr, "削除するファイルが選択されていません")
            return
        
        # パスの長さをチェック（日本語対応）
        src_display = str(current_file.path)
        
        # 簡易ダイアログに収まるかチェック
        short_msg = f"削除: {current_file.name}"
        if get_display_width(short_msg) + 20 <= self.max_x:  # 選択肢分の余裕
            # 通常ダイアログ
            self.dialog_message = short_msg
            self.dialog_options = ["はい", "いいえ"]
            self.dialog_selected = 1  # デフォルトは「いいえ」
            self.mode = 'dialog'
        else:
            # In-windowダイアログ
            content = [
                f"削除対象: {src_display}",
                "",
                "⚠️  この操作は元に戻せません"
            ]
            self.in_window = InWindowDialog(
                title="ファイル削除の確認",
                content=content,
                options=["はい", "いいえ"],
                selected=1,  # デフォルトは「いいえ」
                color_manager=self.color_manager
            )
            self.mode = 'in_window'
        
        self.pending_operation = 'delete'
        self.pending_file = current_file

    def _move_file(self):
        """ファイル移動"""
        active_pane = self.left_pane if self.active_pane == 'left' else self.right_pane
        inactive_pane = self.right_pane if self.active_pane == 'left' else self.left_pane
        current_file = active_pane.get_current_file()
        
        if not current_file:
            self.command_line.draw(self.stdscr, "移動するファイルが選択されていません")
            return
        
        # 移動先パス
        dst_path = inactive_pane.current_path / current_file.name
        
        # ファイルサイズチェック（100MB以上でバックグラウンド転送を提案）
        large_file_threshold = 100 * 1024 * 1024  # 100MB
        is_large_file = False
        
        if current_file.is_dir:
            # ディレクトリの場合は常にバックグラウンド転送を提案
            is_large_file = True
        elif hasattr(current_file, 'size') and current_file.size > large_file_threshold:
            is_large_file = True
        
        # パスの長さをチェック（日本語対応）
        src_display = str(current_file.path)
        dst_display = str(dst_path)
        
        if is_large_file:
            # 大きなファイル/ディレクトリの場合はバックグラウンド転送オプションを提供
            content = [
                f"転送元: {src_display}",
                "     |",
                "     |",
                f"転送先: {dst_display}",
                "",
                "大容量ファイル/ディレクトリです。"
            ]
            self.in_window = InWindowDialog(
                title="ファイル移動の確認",
                content=content,
                options=["バックグラウンド", "通常", "キャンセル"],
                selected=0,
                color_manager=self.color_manager
            )
            self.mode = 'in_window'
            self.pending_operation = 'move'
            self.pending_file = current_file
            self.pending_dst = str(dst_path)
            self.pending_background = True
        else:
            # 通常サイズの場合は従来通り
            # 簡易ダイアログに収まるかチェック
            short_msg = f"移動: {current_file.name} → {inactive_pane.current_path.name}"
            if get_display_width(short_msg) + 20 <= self.max_x:  # 選択肢分の余裕
                # 通常ダイアログ
                self.dialog_message = short_msg
                self.dialog_options = ["はい", "いいえ"]
                self.dialog_selected = 1
                self.mode = 'dialog'
            else:
                # In-windowダイアログ
                content = [
                    f"転送元: {src_display}",
                    "     |",
                    "     |",
                    f"転送先: {dst_display}"
                ]
                self.in_window = InWindowDialog(
                    title="ファイル移動の確認",
                    content=content,
                    options=["はい", "いいえ"],
                    selected=1,
                    color_manager=self.color_manager
                )
                self.mode = 'in_window'
            
            self.pending_operation = 'move'
            self.pending_file = current_file
            self.pending_dst = str(dst_path)
            # 通常転送の場合はFalseをセット
            self.pending_background = False

    def _copy_file(self):
        """ファイルコピー"""
        active_pane = self.left_pane if self.active_pane == 'left' else self.right_pane
        inactive_pane = self.right_pane if self.active_pane == 'left' else self.left_pane
        current_file = active_pane.get_current_file()
        
        if not current_file:
            self.command_line.draw(self.stdscr, "コピーするファイルが選択されていません")
            return
        
        # コピー先パス
        dst_path = inactive_pane.current_path / current_file.name
        
        # ファイルサイズチェック（100MB以上でバックグラウンド転送を提案）
        large_file_threshold = 100 * 1024 * 1024  # 100MB
        is_large_file = False
        
        if current_file.is_dir:
            # ディレクトリの場合は常にバックグラウンド転送を提案
            is_large_file = True
        elif hasattr(current_file, 'size') and current_file.size > large_file_threshold:
            is_large_file = True
        
        # パスの長さをチェック（日本語対応）
        src_display = str(current_file.path)
        dst_display = str(dst_path)
        
        if is_large_file:
            # 大きなファイル/ディレクトリの場合はバックグラウンド転送オプションを提供
            content = [
                f"転送元: {src_display}",
                "     |",
                "     |", 
                f"転送先: {dst_display}",
                "",
                "大容量ファイル/ディレクトリです。"
            ]
            self.in_window = InWindowDialog(
                title="ファイルコピーの確認",
                content=content,
                options=["バックグラウンド", "通常", "キャンセル"],
                selected=0,
                color_manager=self.color_manager
            )
            self.mode = 'in_window'
            self.pending_operation = 'copy'
            self.pending_file = current_file
            self.pending_dst = str(dst_path)
            self.pending_background = True
        else:
            # 通常サイズの場合は従来通り
            # 簡易ダイアログに収まるかチェック
            short_msg = f"コピー: {current_file.name} → {inactive_pane.current_path.name}"
            if get_display_width(short_msg) + 20 <= self.max_x:  # 選択肢分の余裕
                # 通常ダイアログ
                self.dialog_message = short_msg
                self.dialog_options = ["はい", "いいえ"]
                self.dialog_selected = 0
                self.mode = 'dialog'
            else:
                # In-windowダイアログ
                content = [
                    f"転送元: {src_display}",
                    "     |",
                    "     |",
                    f"転送先: {dst_display}"
                ]
                self.in_window = InWindowDialog(
                    title="ファイルコピーの確認",
                    content=content,
                    options=["はい", "いいえ"],
                    selected=0,
                    color_manager=self.color_manager
                )
                self.mode = 'in_window'
            
            self.pending_operation = 'copy'
            self.pending_file = current_file
            self.pending_dst = str(dst_path)
            # 通常転送の場合はFalseをセット
            self.pending_background = False

    def _rename_file(self):
        """ファイルリネーム"""
        active_pane = self.left_pane if self.active_pane == 'left' else self.right_pane
        current_file = active_pane.get_current_file()
        
        if not current_file:
            self.command_line.draw(self.stdscr, "リネームするファイルが選択されていません")
            return
        
        # 編集モードに移行
        self.mode = 'edit'
        self.edit_buffer = current_file.name
        self.edit_cursor = len(self.edit_buffer)
        self.pending_operation = 'rename'
        self.pending_file = current_file
        self.command_line.draw(self.stdscr, f"新しい名前: {self.edit_buffer}")

    def _create_directory(self):
        """新規ディレクトリ作成"""
        active_pane = self.left_pane if self.active_pane == 'left' else self.right_pane
        
        # 編集モードに移行
        self.mode = 'edit'
        self.edit_buffer = ""
        self.edit_cursor = 0
        self.pending_operation = 'create_directory'
        self.pending_path = active_pane.current_path
        self.command_line.draw(self.stdscr, "ディレクトリ名: ")

    def _execute_edit_operation(self):
        """編集操作実行"""
        if self.pending_operation == 'rename' and hasattr(self, 'pending_file'):
            try:
                new_name = self.edit_buffer.strip()
                if not new_name or new_name == self.pending_file.name:
                    self.command_line.draw(self.stdscr, "リネームをキャンセルしました")
                else:
                    # リネーム実行
                    success = self.file_ops.rename_file(str(self.pending_file.path), new_name)
                    if success:
                        self.command_line.draw(self.stdscr, f"リネーム完了: {self.pending_file.name} → {new_name}")
                        # ペインの更新
                        active_pane = self.left_pane if self.active_pane == 'left' else self.right_pane
                        active_pane.refresh_files()
                    else:
                        self.command_line.draw(self.stdscr, "リネームに失敗しました")
            except Exception as e:
                self.command_line.draw(self.stdscr, f"エラー: {str(e)}")
        elif self.pending_operation == 'create_directory' and hasattr(self, 'pending_path'):
            try:
                dir_name = self.edit_buffer.strip()
                if not dir_name:
                    self.command_line.draw(self.stdscr, "ディレクトリ作成をキャンセルしました")
                else:
                    # ディレクトリ作成実行
                    dir_path = str(self.pending_path / dir_name)
                    success = self.file_ops.create_directory(dir_path)
                    if success:
                        self.command_line.draw(self.stdscr, f"ディレクトリ作成完了: {dir_name}")
                        # アクティブペインの更新
                        active_pane = self.left_pane if self.active_pane == 'left' else self.right_pane
                        active_pane.refresh_files()
                    else:
                        self.command_line.draw(self.stdscr, "ディレクトリ作成に失敗しました")
            except Exception as e:
                self.command_line.draw(self.stdscr, f"エラー: {str(e)}")
        
        self.mode = 'normal'
        self._clear_edit_mode()

    def _execute_dialog_operation(self):
        """ダイアログ操作実行"""
        try:
            if self.pending_operation == 'delete' and hasattr(self, 'pending_file'):
                # 削除実行
                self._start_delete_operation()
            elif self.pending_operation == 'copy' and hasattr(self, 'pending_file') and hasattr(self, 'pending_dst'):
                # コピー実行
                self._start_copy_operation()  
            elif self.pending_operation == 'move' and hasattr(self, 'pending_file') and hasattr(self, 'pending_dst'):
                # 移動実行
                self._start_move_operation()
        except Exception as e:
            self.command_line.draw(self.stdscr, f"エラー: {str(e)}")
        
        self.mode = 'normal'
        self._clear_dialog_mode()

    def _start_delete_operation(self):
        """削除操作開始"""
        import threading
        
        self.mode = 'operation'
        self.operation_message = f"削除中: {self.pending_file.name}"
        self.operation_progress = "0%"
        
        def delete_operation():
            try:
                success = self.file_ops.delete_file(str(self.pending_file.path))
                if success:
                    self.operation_progress = "100% 完了"
                    # ペインの更新
                    active_pane = self.left_pane if self.active_pane == 'left' else self.right_pane
                    active_pane.refresh_files()
                else:
                    self.operation_progress = "失敗"
                
                # 1秒後にノーマルモードに戻る
                import time
                time.sleep(1)
                self.mode = 'normal'
                self.operation_progress = None
                
            except Exception as e:
                self.operation_progress = f"エラー: {str(e)}"
                import time
                time.sleep(2)
                self.mode = 'normal'
                self.operation_progress = None
        
        thread = threading.Thread(target=delete_operation)
        thread.daemon = True
        thread.start()

    def _start_copy_operation(self):
        """コピー操作開始"""
        import threading
        
        # バックグラウンド転送かどうかチェック
        use_background = getattr(self, 'pending_background', False)
        
        if use_background:
            # バックグラウンド転送キューに追加
            try:
                transfer_id = self.file_ops.add_background_copy(
                    str(self.pending_file.path),
                    self.pending_dst
                )
                self.command_line.draw(
                    self.stdscr, 
                    f"バックグラウンド転送キューに追加: {self.pending_file.name} (ID: {transfer_id[:8]})"
                )
                # 2秒後にメッセージをクリア
                import time
                import threading
                def clear_message():
                    time.sleep(2)
                    self.command_line.draw(self.stdscr, "")
                threading.Thread(target=clear_message, daemon=True).start()
            except Exception as e:
                self.command_line.draw(self.stdscr, f"バックグラウンド転送追加エラー: {str(e)}")
        else:
            # 従来の同期転送
            self.mode = 'operation'
            self.operation_message = f"コピー中: {self.pending_file.name}"
            self.operation_progress = "0%"
            
            def progress_callback(current, total, filename):
                percent = int((current / total) * 100)
                self.operation_progress = f"{percent}% ({current}/{total})"
            
            def copy_operation():
                try:
                    success = self.file_ops.copy_file(
                        str(self.pending_file.path), 
                        self.pending_dst,
                        progress_callback=progress_callback
                    )
                    if success:
                        self.operation_progress = "100% 完了"
                        # ペインの更新
                        inactive_pane = self.right_pane if self.active_pane == 'left' else self.left_pane
                        inactive_pane.refresh_files()
                    else:
                        self.operation_progress = "失敗"
                    
                    # 1秒後にノーマルモードに戻る
                    import time
                    time.sleep(1)
                    self.mode = 'normal'
                    self.operation_progress = None
                    
                except Exception as e:
                    self.operation_progress = f"エラー: {str(e)}"
                    import time
                    time.sleep(2)
                    self.mode = 'normal'
                    self.operation_progress = None
            
            thread = threading.Thread(target=copy_operation)
            thread.daemon = True
            thread.start()

    def _start_move_operation(self):
        """移動操作開始"""
        import threading
        
        # バックグラウンド転送かどうかチェック
        use_background = getattr(self, 'pending_background', False)
        
        if use_background:
            # バックグラウンド転送キューに追加
            try:
                transfer_id = self.file_ops.add_background_move(
                    str(self.pending_file.path),
                    self.pending_dst
                )
                self.command_line.draw(
                    self.stdscr, 
                    f"バックグラウンド転送キューに追加: {self.pending_file.name} (ID: {transfer_id[:8]})"
                )
                # 2秒後にメッセージをクリア
                import time
                import threading
                def clear_message():
                    time.sleep(2)
                    self.command_line.draw(self.stdscr, "")
                threading.Thread(target=clear_message, daemon=True).start()
            except Exception as e:
                self.command_line.draw(self.stdscr, f"バックグラウンド転送追加エラー: {str(e)}")
        else:
            # 従来の同期移動
            self.mode = 'operation'
            self.operation_message = f"移動中: {self.pending_file.name}"
            self.operation_progress = "0%"
            
            def move_operation():
                try:
                    success = self.file_ops.move_file(str(self.pending_file.path), self.pending_dst)
                    if success:
                        self.operation_progress = "100% 完了"
                        # 両ペインの更新
                        self.left_pane.refresh_files()
                        self.right_pane.refresh_files()
                    else:
                        self.operation_progress = "失敗"
                    
                    # 1秒後にノーマルモードに戻る
                    import time
                    time.sleep(1)
                    self.mode = 'normal'
                    self.operation_progress = None
                    
                except Exception as e:
                    self.operation_progress = f"エラー: {str(e)}"
                    import time
                    time.sleep(2)
                    self.mode = 'normal'
                    self.operation_progress = None
            
            thread = threading.Thread(target=move_operation)
            thread.daemon = True
            thread.start()

    def _clear_edit_mode(self):
        """編集モードのクリア"""
        if hasattr(self, 'edit_buffer'):
            delattr(self, 'edit_buffer')
        if hasattr(self, 'edit_cursor'):
            delattr(self, 'edit_cursor')
        if hasattr(self, 'pending_operation'):
            delattr(self, 'pending_operation')
        if hasattr(self, 'pending_file'):
            delattr(self, 'pending_file')
        if hasattr(self, 'pending_path'):
            delattr(self, 'pending_path')

    def _clear_dialog_mode(self):
        """ダイアログモードのクリア"""
        self.dialog_message = ""
        self.dialog_options = []
        self.dialog_selected = 0
        if hasattr(self, 'pending_operation'):
            delattr(self, 'pending_operation')
        if hasattr(self, 'pending_file'):
            delattr(self, 'pending_file')
        if hasattr(self, 'pending_dst'):
            delattr(self, 'pending_dst')
        if hasattr(self, 'pending_background'):
            delattr(self, 'pending_background')
    
    def _clear_in_window_mode(self):
        """In-windowモードのクリア"""
        self.in_window = None
        self.in_window_selected = 0
        if hasattr(self, 'pending_operation'):
            delattr(self, 'pending_operation')
        if hasattr(self, 'pending_file'):
            delattr(self, 'pending_file')
        if hasattr(self, 'pending_dst'):
            delattr(self, 'pending_dst')
        if hasattr(self, 'pending_background'):
            delattr(self, 'pending_background')

    # バックグラウンド転送機能
    
    def _show_transfer_queue(self):
        """転送キュー表示"""
        from ui import TransferQueueView
        
        # 転送情報を取得
        transfers = self.file_ops.get_all_transfers()
        summary = self.file_ops.get_transfer_summary()
        
        self.transfer_queue_view = TransferQueueView(
            transfers=transfers,
            summary=summary,
            color_manager=self.color_manager
        )
        self.mode = 'transfer_queue'
        self.transfer_queue_selected = 0
    
    def _toggle_transfer_pause(self):
        """現在選択中の転送を一時停止/再開"""
        transfers = self.file_ops.get_all_transfers()
        active_transfers = [t for t in transfers if t['status'] in ['in_progress', 'paused']]
        
        if not active_transfers:
            self.command_line.draw(self.stdscr, "一時停止/再開可能な転送がありません")
            return
        
        # 最新の転送を対象とする
        transfer = active_transfers[0]
        transfer_id = transfer['id']
        
        if transfer['status'] == 'in_progress':
            success = self.file_ops.pause_transfer(transfer_id)
            if success:
                self.command_line.draw(self.stdscr, f"転送を一時停止しました: {transfer['src_path']}")
            else:
                self.command_line.draw(self.stdscr, "転送の一時停止に失敗しました")
        elif transfer['status'] == 'paused':
            success = self.file_ops.resume_transfer(transfer_id)
            if success:
                self.command_line.draw(self.stdscr, f"転送を再開しました: {transfer['src_path']}")
            else:
                self.command_line.draw(self.stdscr, "転送の再開に失敗しました")
    
    def _cancel_current_transfer(self):
        """現在選択中の転送をキャンセル"""
        transfers = self.file_ops.get_all_transfers()
        active_transfers = [t for t in transfers if t['status'] in ['waiting', 'in_progress', 'paused']]
        
        if not active_transfers:
            self.command_line.draw(self.stdscr, "キャンセル可能な転送がありません")
            return
        
        # 最新の転送を対象とする
        transfer = active_transfers[0]
        transfer_id = transfer['id']
        
        success = self.file_ops.cancel_transfer(transfer_id)
        if success:
            self.command_line.draw(self.stdscr, f"転送をキャンセルしました: {transfer['src_path']}")
        else:
            self.command_line.draw(self.stdscr, "転送のキャンセルに失敗しました")
    
    def _start_background_copy(self, src_path: str, dst_path: str, priority: int = 0):
        """バックグラウンドコピーを開始"""
        transfer_id = self.file_ops.start_background_copy(src_path, dst_path, priority)
        return transfer_id
    
    def _start_background_move(self, src_path: str, dst_path: str, priority: int = 0):
        """バックグラウンド移動を開始"""
        transfer_id = self.file_ops.start_background_move(src_path, dst_path, priority)
        return transfer_id
    
    def _handle_transfer_queue_input(self, key):
        """転送キューモード入力処理"""
        if key == 27:  # ESC: 戻る
            self.mode = 'normal'
            self.transfer_queue_view = None
        elif key == ord('q') or key == ord('Q'):  # Q: 戻る
            self.mode = 'normal'
            self.transfer_queue_view = None
        elif key == curses.KEY_UP or key == ord('k'):
            if self.transfer_queue_selected > 0:
                self.transfer_queue_selected -= 1
        elif key == curses.KEY_DOWN or key == ord('j'):
            transfers = self.file_ops.get_all_transfers()
            if self.transfer_queue_selected < len(transfers) - 1:
                self.transfer_queue_selected += 1
        elif key == ord('p') or key == ord('P'):  # P: 一時停止/再開
            self._pause_resume_selected_transfer()
        elif key == ord('c') or key == ord('C'):  # C: キャンセル
            self._cancel_selected_transfer()
        elif key == ord('d') or key == ord('D'):  # D: 削除（完了済みのみ）
            self._remove_selected_transfer()
        elif key == ord('r') or key == ord('R'):  # R: 画面更新
            self._refresh_transfer_queue()
    
    def _pause_resume_selected_transfer(self):
        """選択中の転送を一時停止/再開"""
        transfers = self.file_ops.get_all_transfers()
        if 0 <= self.transfer_queue_selected < len(transfers):
            transfer = transfers[self.transfer_queue_selected]
            transfer_id = transfer['id']
            
            if transfer['status'] == 'in_progress':
                self.file_ops.pause_transfer(transfer_id)
            elif transfer['status'] == 'paused':
                self.file_ops.resume_transfer(transfer_id)
    
    def _cancel_selected_transfer(self):
        """選択中の転送をキャンセル"""
        transfers = self.file_ops.get_all_transfers()
        if 0 <= self.transfer_queue_selected < len(transfers):
            transfer = transfers[self.transfer_queue_selected]
            transfer_id = transfer['id']
            
            if transfer['status'] in ['waiting', 'in_progress', 'paused']:
                self.file_ops.cancel_transfer(transfer_id)
    
    def _remove_selected_transfer(self):
        """選択中の転送を削除（完了済みのみ）"""
        transfers = self.file_ops.get_all_transfers()
        if 0 <= self.transfer_queue_selected < len(transfers):
            transfer = transfers[self.transfer_queue_selected]
            
            if transfer['status'] in ['completed', 'failed', 'cancelled']:
                # 完了した転送のみクリア可能
                self.file_ops.clear_completed_transfers()
    
    def _refresh_transfer_queue(self):
        """転送キュー画面を更新"""
        if self.transfer_queue_view:
            transfers = self.file_ops.get_all_transfers()
            summary = self.file_ops.get_transfer_summary()
            self.transfer_queue_view.update_data(transfers, summary)

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
        """編集モード入力処理"""
        if key == 27:  # ESC: キャンセル
            self.mode = 'normal'
            self._clear_edit_mode()
        elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:  # Enter: 実行
            self._execute_edit_operation()
        elif key == curses.KEY_BACKSPACE or key == 8 or key == 127:  # Backspace
            if self.edit_cursor > 0:
                self.edit_buffer = self.edit_buffer[:self.edit_cursor-1] + self.edit_buffer[self.edit_cursor:]
                self.edit_cursor -= 1
        elif key == 4:  # Ctrl+D: 文字削除
            if self.edit_cursor < len(self.edit_buffer):
                self.edit_buffer = self.edit_buffer[:self.edit_cursor] + self.edit_buffer[self.edit_cursor+1:]
        elif key == 1:  # Ctrl+A: 行頭
            self.edit_cursor = 0
        elif key == 5:  # Ctrl+E: 行末
            self.edit_cursor = len(self.edit_buffer)
        elif key == 6:  # Ctrl+F: 右移動
            if self.edit_cursor < len(self.edit_buffer):
                self.edit_cursor += 1
        elif key == 2:  # Ctrl+B: 左移動
            if self.edit_cursor > 0:
                self.edit_cursor -= 1
        elif key == 11:  # Ctrl+K: 行末まで削除
            self.edit_buffer = self.edit_buffer[:self.edit_cursor]
        elif 32 <= key <= 126:  # 印字可能文字
            char = chr(key)
            self.edit_buffer = self.edit_buffer[:self.edit_cursor] + char + self.edit_buffer[self.edit_cursor:]
            self.edit_cursor += 1
        
        # 編集中の表示更新
        cursor_pos = "◀" if self.edit_cursor == 0 else "▶" if self.edit_cursor == len(self.edit_buffer) else "|"
        display_text = self.edit_buffer[:self.edit_cursor] + cursor_pos + self.edit_buffer[self.edit_cursor:]
        self.command_line.draw(self.stdscr, f"新しい名前: {display_text}")

    def _handle_dialog_mode_input(self, key):
        """ダイアログモード入力処理"""
        if key == 27:  # ESC: キャンセル
            self.mode = 'normal'
            self._clear_dialog_mode()
        elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:  # Enter: 選択実行
            if self.dialog_selected == 0:  # 「はい」選択時
                self._execute_dialog_operation()
            else:
                self.mode = 'normal'
                self._clear_dialog_mode()
        elif key == curses.KEY_LEFT or key == ord('h'):
            self.dialog_selected = 0
        elif key == curses.KEY_RIGHT or key == ord('l'):
            self.dialog_selected = 1
        elif key == 9:  # TAB
            self.dialog_selected = 1 - self.dialog_selected

    def _handle_in_window_input(self, key):
        """In-windowダイアログモード入力処理"""
        if self.in_window:
            result = self.in_window.handle_input(key)
            if result == "continue":
                # 継続（選択肢変更など）
                pass
            elif result is None:
                # キャンセル
                self.mode = 'normal'
                self._clear_in_window_mode()
            else:
                # 選択肢が選ばれた
                if hasattr(self, 'pending_operation'):
                    if result == "はい":
                        # 通常の操作実行（バックグラウンド転送=False）
                        self.pending_background = False
                        self._execute_dialog_operation()
                    elif result == "バックグラウンド":
                        # バックグラウンド転送実行
                        self.pending_background = True
                        self._execute_dialog_operation()
                    elif result == "通常":
                        # 通常転送実行
                        self.pending_background = False
                        self._execute_dialog_operation()
                    # "キャンセル"やその他の場合は何もしない
                self.mode = 'normal'
                self._clear_in_window_mode()

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
        
        # コマンドライン - モード別表示
        if self.mode == 'operation' and self.operation_progress:
            msg = f"Mode: {self.mode} | {self.operation_message} | 進捗: {self.operation_progress}"
        elif self.mode == 'dialog':
            selected_indicator = [" ", " "]
            selected_indicator[self.dialog_selected] = "*"
            options_text = f"{selected_indicator[0]}{self.dialog_options[0]} {selected_indicator[1]}{self.dialog_options[1]}"
            
            # ダイアログメッセージの処理（改行除去・短縮）
            dialog_msg = self.dialog_message.replace('\n', ' ').replace('  ', ' ').strip()
            
            # 選択肢の表示幅を確保（日本語対応）
            options_display_width = get_display_width(options_text) + 3  # " | " 分も含む
            max_msg_width = max(15, self.max_x - options_display_width - 5)  # 余裕を持たせる
            
            # メッセージを表示幅ベースで切り詰め
            if get_display_width(dialog_msg) > max_msg_width:
                dialog_msg = truncate_string_by_width(dialog_msg, max_msg_width)
            
            msg = f"{dialog_msg} | {options_text}"
        elif self.mode == 'in_window' and self.in_window:
            # In-windowダイアログ表示
            self.in_window.draw(self.stdscr)
        elif self.mode == 'transfer_queue' and self.transfer_queue_view:
            # 転送キュー画面表示
            self.transfer_queue_view.draw(self.stdscr, self.transfer_queue_selected)
        else:
            msg = f"Mode: {self.mode} | Active: {self.active_pane}"
        
        # 通常のコマンドライン表示が必要な場合
        if self.mode not in ['in_window', 'transfer_queue']:
            if 'msg' not in locals():
                msg = f"Mode: {self.mode} | Active: {self.active_pane}"
            
            # アクティブ転送数を表示に含める
            active_count = self.file_ops.get_active_transfer_count()
            if active_count > 0:
                msg += f" | 転送中: {active_count}"
            
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