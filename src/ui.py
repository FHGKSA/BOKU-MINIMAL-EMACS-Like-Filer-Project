#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2pane TUI Filer - UI コンポーネント

このモジュールはファイラーのUI要素を実装します。
"""

import curses
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import stat
import time
import pwd
import grp


class FileItem:
    """ファイル項目クラス"""
    
    def __init__(self, path: str):
        """
        初期化
        
        Args:
            path: ファイルパス
        """
        self.path = Path(path)
        self.name = self.path.name
        self.is_link = self.path.is_symlink()
        self.selected = False
        
        # シンボリックリンクの処理
        self._handle_symlink()
        
        # is_dirの判定（シンボリックリンクの場合はリンク先を参照）
        self.is_dir = self._is_directory()
        
        # ファイル名と拡張子の分離
        self._split_name_extension()
        
        # ファイル情報取得
        self._get_file_info()

    def _split_name_extension(self):
        """ファイル名と拡張子の分離"""
        if self.is_dir:
            self.name_part = self.name
            self.extension = ""
        elif self.name.startswith('.') and '.' not in self.name[1:]:
            # 隠しファイル（.bashrcなど）
            self.name_part = self.name
            self.extension = ""
        elif '.' in self.name and not self.name.startswith('.'):
            # 通常ファイル
            self.name_part, self.extension = self.name.rsplit('.', 1)
        else:
            # 拡張子なしファイル
            self.name_part = self.name
            self.extension = ""

    def _handle_symlink(self):
        """シンボリックリンクの処理"""
        self.link_target = None
        self.is_broken_link = False
        
        if self.is_link:
            try:
                self.link_target = str(self.path.readlink())
                # リンク先の存在確認
                if not self.path.exists():
                    self.is_broken_link = True
            except (OSError, RuntimeError):
                self.is_broken_link = True
                self.link_target = "?"
    
    def _is_directory(self):
        """ディレクトリかどうかの判定（シンボリックリンク考慮）"""
        try:
            if self.is_link:
                # シンボリックリンクの場合はリンク先を確認
                return self.path.is_dir() and not self.is_broken_link
            else:
                return self.path.is_dir()
        except (OSError, RuntimeError):
            return False
    
    def _get_file_info(self):
        """ファイル情報の取得"""
        try:
            # シンボリックリンクの場合は適切な統計情報を取得
            if self.is_link and not self.is_broken_link:
                # リンク先の統計情報を取得
                stat_info = self.path.stat()
            elif self.is_link and self.is_broken_link:
                # 壊れたリンクの場合はリンク自体の統計情報
                stat_info = self.path.lstat()
            else:
                # 通常ファイルの場合
                stat_info = self.path.stat()
            
            self.size = stat_info.st_size
            self.mtime = stat_info.st_mtime
            self.mode = stat_info.st_mode
            self.uid = stat_info.st_uid  
            self.gid = stat_info.st_gid
            
            # 権限文字列
            self.permissions = stat.filemode(self.mode)
            
            # 所有者・グループ名（エラー時はID番号）
            try:
                self.owner = pwd.getpwuid(self.uid).pw_name
            except:
                self.owner = str(self.uid)
                
            try:
                self.group = grp.getgrgid(self.gid).gr_name
            except:
                self.group = str(self.gid)
                
        except (OSError, FileNotFoundError):
            # ファイルアクセスエラー時のデフォルト値
            self.size = 0
            self.mtime = 0
            self.mode = 0
            self.permissions = "----------"
            self.owner = "unknown"
            self.group = "unknown"

    def get_size_string(self) -> str:
        """ファイルサイズの文字列表現"""
        if self.is_dir:
            return "<DIR>"
        elif self.is_link and self.is_broken_link:
            return "<BROKEN>"
        elif self.is_link:
            return "<LINK>"
        
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                if unit == 'B':
                    return f"{size}B"
                else:
                    return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}PB"

    def get_mtime_string(self) -> str:
        """更新日時の文字列表現"""
        try:
            return time.strftime("%Y-%m-%d %H:%M", time.localtime(self.mtime))
        except:
            return "----/--/-- --:--"
    
    def get_display_name(self) -> str:
        """表示用のファイル名を取得"""
        if self.is_link:
            if self.is_broken_link:
                return f"{self.name} -> {self.link_target or '?'} (broken)"
            else:
                return f"{self.name} -> {self.link_target or '?'}"
        else:
            return self.name
    
    def get_display_name_part(self) -> str:
        """表示用の名前部分を取得（拡張子なし）"""
        if self.is_link:
            if self.is_broken_link:
                return f"{self.name_part}@!"
            else:
                return f"{self.name_part}@"
        else:
            return self.name_part


class FilePane:
    """ファイルペインクラス"""
    
    def __init__(self, start_y: int, start_x: int, height: int, width: int,
                 path: str, color_manager, active: bool = False):
        """
        初期化
        
        Args:
            start_y: 開始Y座標
            start_x: 開始X座標
            height: 高さ
            width: 幅
            path: 表示するディレクトリパス
            color_manager: 色管理オブジェクト
            active: アクティブペインか
        """
        self.start_y = start_y
        self.start_x = start_x
        self.height = height
        self.width = width
        self.current_path = Path(path)
        self.color_manager = color_manager
        self.active = active
        
        # ファイル一覧
        self.files: List[FileItem] = []
        self.cursor = 0
        self.scroll_offset = 0
        
        # 表示設定
        self.show_hidden = False
        self.sort_key = 'name'  # 'name', 'ext', 'size', 'mtime'
        self.sort_reverse = False
        
        # ファイルリスト更新
        self.refresh_files()

    def refresh_files(self):
        """ファイルリストの更新"""
        try:
            self.files = []
            
            # 親ディレクトリ (..) を最初に追加（ルートディレクトリでない場合）
            if self.current_path != Path("/"):
                parent_item = FileItem(str(self.current_path.parent))
                parent_item.name = ".."
                parent_item.name_part = ".."
                parent_item.extension = ""
                parent_item.is_dir = True
                self.files.append(parent_item)
            
            # ディレクトリの読み込み
            for item in self.current_path.iterdir():
                # 隠しファイルフィルタ
                if not self.show_hidden and item.name.startswith('.'):
                    continue
                
                self.files.append(FileItem(str(item)))
            
            # ソート
            self._sort_files()
            
            # カーソル位置調整
            if self.cursor >= len(self.files):
                self.cursor = max(0, len(self.files) - 1)
                
        except (OSError, PermissionError):
            self.files = []
            self.cursor = 0

    def _sort_files(self):
        """ファイルソート"""
        if self.sort_key == 'name':
            # ディレクトリを先頭にして、名前でソート
            self.files.sort(
                key=lambda x: (not x.is_dir, x.name_part.lower()),
                reverse=self.sort_reverse
            )
        elif self.sort_key == 'ext':
            # 拡張子でソート
            self.files.sort(
                key=lambda x: (not x.is_dir, x.extension.lower(), x.name_part.lower()),
                reverse=self.sort_reverse
            )
        elif self.sort_key == 'size':
            # サイズでソート
            self.files.sort(
                key=lambda x: (not x.is_dir, x.size),
                reverse=self.sort_reverse
            )
        elif self.sort_key == 'mtime':
            # 更新日時でソート
            self.files.sort(
                key=lambda x: (not x.is_dir, x.mtime),
                reverse=self.sort_reverse
            )

    def draw(self, stdscr):
        """ペインの描画"""
        # ペイン枠描画
        self._draw_header(stdscr)
        
        # ファイル一覧描画
        self._draw_file_list(stdscr)

    def _draw_header(self, stdscr):
        """ヘッダー描画"""
        # パス表示
        path_str = str(self.current_path)
        if len(path_str) > self.width - 2:
            path_str = "..." + path_str[-(self.width - 5):]
        
        # アクティブペインの強調
        if self.active:
            try:
                stdscr.addstr(
                    self.start_y, 
                    self.start_x, 
                    path_str.ljust(self.width)[:self.width], 
                    curses.A_REVERSE
                )
            except curses.error:
                pass
        else:
            try:
                stdscr.addstr(
                    self.start_y, 
                    self.start_x, 
                    path_str.ljust(self.width)[:self.width]
                )
            except curses.error:
                pass

    def _draw_file_list(self, stdscr):
        """ファイル一覧描画"""
        visible_height = self.height - 1  # ヘッダー分を除く
        
        # スクロール位置調整
        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + visible_height:
            self.scroll_offset = self.cursor - visible_height + 1

        # ファイル項目描画
        for i in range(visible_height):
            file_index = self.scroll_offset + i
            y = self.start_y + 1 + i
            
            if file_index >= len(self.files):
                # 空行をクリア
                try:
                    stdscr.addstr(y, self.start_x, " " * self.width)
                except curses.error:
                    pass
                continue
            
            file_item = self.files[file_index]
            self._draw_file_item(stdscr, y, file_item, file_index == self.cursor)

    def _draw_file_item(self, stdscr, y: int, file_item: FileItem, is_cursor: bool):
        """ファイル項目の描画"""
        # カラム幅計算（シンボリックリンク対応で動的調整）
        available_width = self.width - 24  # マーカー、サイズ、その他固定部分
        name_width = max(12, available_width // 2)
        ext_width = max(3, available_width // 4)
        size_width = 9
        
        # 状態マーカー
        if file_item.selected:
            marker = "[M]"
        elif is_cursor:
            marker = "[>]"
        else:
            marker = "[ ]"
        
        # 表示文字列構成（シンボリックリンク対応）
        name_str = file_item.get_display_name_part()
        
        # 名前部分の長さ制限
        if len(name_str) > name_width - 4:
            name_str = name_str[:name_width-7] + "..."
        
        ext_str = file_item.extension if not file_item.is_link else ""
        size_str = file_item.get_size_string()
        
        # シンボリックリンクの場合は特別な表示
        if file_item.is_link and file_item.link_target:
            # 短縮されたリンク先表示
            target = file_item.link_target
            if len(target) > ext_width:
                target = target[:ext_width-3] + "..."
            ext_str = f"→{target}"
        
        # 行の構成
        line = f"{marker} {name_str:<{name_width-4}} {ext_str:<{ext_width}} {size_str:>{size_width}}"
        line = line[:self.width]
        
        # カーソル行は反転表示
        attrs = 0
        if is_cursor and self.active:
            attrs = curses.A_REVERSE
        
        # 色分け適用
        color_pair = self.color_manager.get_file_color(file_item)
        
        try:
            stdscr.addstr(y, self.start_x, line.ljust(self.width)[:self.width], 
                         attrs | color_pair)
        except curses.error:
            pass

    def move_cursor_up(self):
        """カーソル上移動"""
        if self.cursor > 0:
            self.cursor -= 1

    def move_cursor_down(self):
        """カーソル下移動"""
        if self.cursor < len(self.files) - 1:
            self.cursor += 1

    def set_active(self, active: bool):
        """アクティブ状態設定"""
        self.active = active

    def get_current_file(self) -> Optional[FileItem]:
        """現在のファイル取得"""
        if 0 <= self.cursor < len(self.files):
            return self.files[self.cursor]
        return None

    def change_directory(self, new_path: str):
        """ディレクトリ変更"""
        try:
            new_path_obj = Path(new_path)
            
            # パスが存在し、ディレクトリかチェック
            if not new_path_obj.exists():
                raise OSError(f"パスが存在しません: {new_path}")
            
            if not new_path_obj.is_dir():
                raise OSError(f"ディレクトリではありません: {new_path}")
            
            # アクセス権限チェック
            if not os.access(str(new_path_obj), os.R_OK):
                raise OSError(f"読み取り権限がありません: {new_path}")
            
            # パス変更
            self.current_path = new_path_obj
            
            # ファイルリスト更新
            self.refresh_files()
            
            # カーソル位置リセット
            self.cursor = 0
            self.scroll_offset = 0
            
        except OSError as e:
            raise Exception(f"ディレクトリ変更に失敗: {str(e)}")
        except PermissionError as e:
            raise Exception(f"権限エラー: アクセス権限がありません")


class StatusBar:
    """ステータスバークラス"""
    
    def __init__(self, start_y: int, start_x: int, width: int, color_manager):
        """
        初期化
        
        Args:
            start_y: 開始Y座標
            start_x: 開始X座標  
            width: 幅
            color_manager: 色管理オブジェクト
        """
        self.start_y = start_y
        self.start_x = start_x
        self.width = width
        self.color_manager = color_manager

    def draw(self, stdscr, info: Dict):
        """ステータスバー描画"""
        # ステータス情報構成
        left_info = f"Left: {info.get('left_path', '')}"
        right_info = f"Right: {info.get('right_path', '')}"
        
        # 左右の情報を配置
        status_line = f"{left_info:<{self.width//2}} {right_info:>{self.width//2}}"
        status_line = status_line[:self.width]
        
        try:
            stdscr.addstr(
                self.start_y, 
                self.start_x, 
                status_line.ljust(self.width)[:self.width],
                curses.A_REVERSE
            )
        except curses.error:
            pass


class CommandLine:
    """コマンドラインクラス"""
    
    def __init__(self, start_y: int, start_x: int, width: int, color_manager):
        """
        初期化
        
        Args:
            start_y: 開始Y座標
            start_x: 開始X座標
            width: 幅
            color_manager: 色管理オブジェクト
        """
        self.start_y = start_y
        self.start_x = start_x
        self.width = width
        self.color_manager = color_manager
        self.message = ""

    def draw(self, stdscr, message: str = ""):
        """コマンドライン描画"""
        display_msg = message or self.message
        display_msg = display_msg[:self.width]
        
        try:
            stdscr.addstr(
                self.start_y,
                self.start_x,
                display_msg.ljust(self.width)[:self.width]
            )
        except curses.error:
            pass

    def clear(self):
        """メッセージクリア"""
        self.message = ""