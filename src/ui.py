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
import unicodedata


def get_display_width(text: str) -> int:
    """文字列の実際の表示幅を計算（全角文字考慮）"""
    width = 0
    for char in text:
        # East Asian Widthを確認
        eaw = unicodedata.east_asian_width(char)
        if eaw in ('F', 'W'):  # Full-width or Wide
            width += 2
        elif eaw in ('H', 'Na', 'N'):  # Half-width, Narrow, Neutral
            width += 1
        else:  # Ambiguous
            width += 1  # デフォルトは1幅
    return width

def truncate_string_by_width(text: str, max_width: int, suffix: str = "...") -> str:
    """表示幅ベースで文字列を切り詰め"""
    if get_display_width(text) <= max_width:
        return text
    
    # サフィックスの幅を考慮
    suffix_width = get_display_width(suffix)
    if suffix_width >= max_width:
        return suffix[:max_width]
    
    target_width = max_width - suffix_width
    result = ""
    current_width = 0
    
    for char in text:
        char_width = get_display_width(char)
        if current_width + char_width > target_width:
            break
        result += char
        current_width += char_width
    
    return result + suffix


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
        """ファイル項目の描画（日本語対応改善）"""
        # 基本カラム幅計算
        marker_width = 4  # "[M] "
        size_width = 9    # "サイズ表示"
        time_width = 8    # "日時表示"
        
        # 利用可能幅から固定部分を引いて動的に調整
        fixed_width = marker_width + size_width + time_width + 6  # 間隔用
        available_width = max(20, self.width - fixed_width)
        
        # 名前と拡張子/リンク先の幅配分
        if file_item.is_link:
            # シンボリックリンクの場合はリンク先表示を優先
            name_width = max(8, int(available_width * 0.5))
            link_width = max(8, available_width - name_width - 2)
        else:
            # 通常ファイルの場合
            name_width = max(10, int(available_width * 0.65))
            ext_width = max(3, available_width - name_width - 1)
        
        # 状態マーカー
        if file_item.selected:
            marker = "[M]"
        elif is_cursor:
            marker = "[>]"
        else:
            marker = "[ ]"
        
        # 表示文字列構成
        name_str = file_item.get_display_name_part()
        
        # 名前部分の切り詰め（表示幅ベース）
        name_display = truncate_string_by_width(name_str, name_width - 1)
        
        # 拡張子/リンク先部分
        if file_item.is_link and file_item.link_target:
            # シンボリックリンクのリンク先表示
            target = file_item.link_target
            ext_display = truncate_string_by_width(f"→{target}", link_width)
        elif file_item.is_dir:
            # ディレクトリの場合
            ext_display = "<DIR>"
        else:
            # 通常ファイルの拡張子
            ext_display = file_item.extension if file_item.extension else ""
            ext_display = truncate_string_by_width(ext_display, ext_width if not file_item.is_link else link_width)
        
        # サイズ表示
        size_str = file_item.get_size_string()
        
        # 行の構成（幅を考虑したフォーマット）
        line_parts = []
        line_parts.append(marker)
        line_parts.append(" ")
        line_parts.append(name_display)
        
        # 名前部分の実際の表示幅を取得してパディング
        name_actual_width = get_display_width(name_display)
        name_padding = max(0, name_width - name_actual_width)
        line_parts.append(" " * name_padding)
        
        line_parts.append(" ")
        line_parts.append(ext_display)
        
        # 拡張子部分のパディング
        ext_actual_width = get_display_width(ext_display)
        if file_item.is_link:
            ext_padding = max(0, link_width - ext_actual_width)
        else:
            ext_padding = max(0, ext_width - ext_actual_width)
        line_parts.append(" " * ext_padding)
        
        line_parts.append(" ")
        line_parts.append(f"{size_str:>{size_width}}")
        
        line = "".join(line_parts)
        
        # 全体の幅制限
        if get_display_width(line) > self.width:
            line = truncate_string_by_width(line, self.width, "")
        
        # カーソル行は反転表示
        attrs = 0
        if is_cursor and self.active:
            attrs = curses.A_REVERSE
        
        # 色分け適用
        color_pair = self.color_manager.get_file_color(file_item)
        
        try:
            # 行の描画（幅を正確に埋める）
            display_line = line
            line_width = get_display_width(display_line)
            if line_width < self.width:
                display_line += " " * (self.width - line_width)
            
            stdscr.addstr(y, self.start_x, display_line[:self.width], 
                         attrs | color_pair)
        except curses.error:
            pass

    def move_cursor_up(self):
        """カーソル上移動（循環スクロール）"""
        if len(self.files) == 0:
            return
        if self.cursor > 0:
            self.cursor -= 1
        else:
            # 最初のファイルで上キーを押すと最後のファイルにループ
            self.cursor = len(self.files) - 1

    def move_cursor_down(self):
        """カーソル下移動（循環スクロール）"""
        if len(self.files) == 0:
            return
        if self.cursor < len(self.files) - 1:
            self.cursor += 1
        else:
            # 最後のファイルで下キーを押すと最初のファイルにループ
            self.cursor = 0

    def set_active(self, active: bool):
        """アクティブ状態設定"""
        self.active = active
        
    def go_to_parent_directory(self):
        """親ディレクトリに移動"""
        try:
            parent_path = self.current_path.parent
            # ルートディレクトリに達していない場合のみ移動
            if parent_path != self.current_path:
                self.change_directory(str(parent_path))
                return True
            return False
        except Exception as e:
            # エラーが発生した場合は移動しない
            return False

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


class InWindowDialog:
    """画面中央表示ダイアログクラス"""
    
    def __init__(self, title: str, content: List[str], options: List[str], 
                 selected: int = 0, color_manager=None):
        """
        初期化
        
        Args:
            title: ダイアログタイトル
            content: 表示する内容行のリスト
            options: 選択肢のリスト  
            selected: 選択されている選択肢のインデックス
            color_manager: 色管理オブジェクト
        """
        self.title = title
        self.content = content
        self.options = options
        self.selected = selected
        self.color_manager = color_manager
        
        # ウィンドウサイズ計算
        self._calculate_window_size()
    
    def _calculate_window_size(self):
        """ウィンドウサイズの計算"""
        # 最小サイズ
        min_width = 40
        min_height = 8
        
        # コンテンツからサイズを計算
        content_width = max([get_display_width(line) for line in self.content + [self.title]] + [20])
        options_text = "  ".join([f"[{opt}]" for opt in self.options])
        options_width = get_display_width(options_text)
        
        # 必要な幅（枠+パディング込み）
        self.width = max(min_width, content_width + 4, options_width + 4)
        self.height = max(min_height, len(self.content) + 6)  # タイトル+枠+選択肢+余白
        
        # 最大サイズ制限（画面の80%まで）
        max_width = int(curses.COLS * 0.8)
        max_height = int(curses.LINES * 0.8)
        
        self.width = min(self.width, max_width)
        self.height = min(self.height, max_height)
    
    def draw(self, stdscr):
        """ダイアログの描画"""
        # 画面中央に配置
        start_y = max(0, (curses.LINES - self.height) // 2)
        start_x = max(0, (curses.COLS - self.width) // 2)
        
        # 背景をクリア（影効果）
        try:
            for y in range(start_y, min(curses.LINES, start_y + self.height + 1)):
                for x in range(start_x, min(curses.COLS, start_x + self.width + 2)):
                    if y < curses.LINES and x < curses.COLS:
                        stdscr.addch(y, x, ' ', curses.A_REVERSE)
        except curses.error:
            pass
        
        # ウィンドウ枠の描画
        self._draw_frame(stdscr, start_y, start_x)
        
        # タイトル描画
        title_x = start_x + (self.width - get_display_width(self.title)) // 2
        try:
            # タイトル用の色を使用
            title_color = self.color_manager.get_dialog_color('title') if self.color_manager else curses.A_BOLD | curses.A_REVERSE
            stdscr.addstr(start_y + 1, title_x, self.title, title_color)
        except curses.error:
            pass
        
        # コンテンツ描画
        text_color = self.color_manager.get_dialog_color('text') if self.color_manager else curses.A_REVERSE
        for i, line in enumerate(self.content):
            if i >= self.height - 5:  # 選択肢用のスペースを確保
                break
            y = start_y + 3 + i
            # 左揃えでコンテンツを表示、背景色付き
            try:
                display_line = truncate_string_by_width(line, self.width - 4)
                stdscr.addstr(y, start_x + 2, display_line, text_color)
            except curses.error:
                pass
        
        # 選択肢描画
        self._draw_options(stdscr, start_y, start_x)
    
    def _draw_frame(self, stdscr, start_y: int, start_x: int):
        """ウィンドウ枠の描画"""
        # 上下の線
        try:
            stdscr.addstr(start_y, start_x, "┌" + "─" * (self.width - 2) + "┐")
            stdscr.addstr(start_y + self.height - 1, start_x, "└" + "─" * (self.width - 2) + "┘")
        except curses.error:
            # ASCII fallback
            try:
                stdscr.addstr(start_y, start_x, "+" + "-" * (self.width - 2) + "+")
                stdscr.addstr(start_y + self.height - 1, start_x, "+" + "-" * (self.width - 2) + "+")
            except curses.error:
                pass
        
        # 左右の線
        for y in range(start_y + 1, start_y + self.height - 1):
            try:
                stdscr.addch(y, start_x, "│")
                stdscr.addch(y, start_x + self.width - 1, "│")
            except curses.error:
                try:
                    stdscr.addch(y, start_x, "|")
                    stdscr.addch(y, start_x + self.width - 1, "|")
                except curses.error:
                    pass
    
    def _draw_options(self, stdscr, start_y: int, start_x: int):
        """選択肢の描画"""
        options_y = start_y + self.height - 3
        
        # 選択肢を中央揃えで配置
        options_parts = []
        for i, option in enumerate(self.options):
            if i == self.selected:
                options_parts.append(f"[*{option}]")
            else:
                options_parts.append(f"[ {option}]")
        
        options_text = "  ".join(options_parts)
        options_x = start_x + (self.width - get_display_width(options_text)) // 2
        
        try:
            # 選択肢用の色を使用
            options_color = self.color_manager.get_dialog_color('options') if self.color_manager else curses.A_BOLD | curses.A_REVERSE
            stdscr.addstr(options_y, options_x, options_text, options_color)
        except curses.error:
            pass
    
    def handle_input(self, key: int) -> Optional[str]:
        """
        入力処理
        
        Args:
            key: 入力されたキー
            
        Returns:
            選択された選択肢、キャンセルの場合はNone
        """
        if key == 27:  # ESC
            return None
        elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:  # Enter
            return self.options[self.selected]
        elif key == curses.KEY_LEFT or key == ord('h'):
            self.selected = max(0, self.selected - 1)
        elif key == curses.KEY_RIGHT or key == ord('l'):
            self.selected = min(len(self.options) - 1, self.selected + 1)
        elif key == 9:  # TAB
            self.selected = (self.selected + 1) % len(self.options)
        
        return "continue"


class TransferQueueView:
    """転送キュービュークラス"""
    
    def __init__(self, transfers: List[Dict], summary: Dict, color_manager=None):
        """
        初期化
        
        Args:
            transfers: 転送情報リスト
            summary: 転送サマリー情報
            color_manager: 色管理オブジェクト
        """
        self.transfers = transfers
        self.summary = summary
        self.color_manager = color_manager
        self.scroll_offset = 0
        
    def update_data(self, transfers: List[Dict], summary: Dict):
        """データを更新"""
        self.transfers = transfers
        self.summary = summary
    
    def draw(self, stdscr, selected: int):
        """転送キュー画面の描画"""
        stdscr.clear()
        
        max_y, max_x = stdscr.getmaxyx()
        
        # タイトル表示
        title = "転送キュー管理"
        try:
            title_color = self.color_manager.get_dialog_color('title') if self.color_manager else curses.A_BOLD | curses.A_REVERSE
            stdscr.addstr(0, (max_x - get_display_width(title)) // 2, title, title_color)
        except curses.error:
            pass
        
        # サマリー表示
        summary_y = 2
        summary_lines = [
            f"待機中: {self.summary.get('waiting', 0)}  実行中: {self.summary.get('in_progress', 0)}  一時停止: {self.summary.get('paused', 0)}",
            f"完了: {self.summary.get('completed', 0)}  失敗: {self.summary.get('failed', 0)}  キャンセル: {self.summary.get('cancelled', 0)}"
        ]
        
        summary_color = self.color_manager.get_dialog_color('text') if self.color_manager else curses.A_REVERSE
        for i, line in enumerate(summary_lines):
            try:
                stdscr.addstr(summary_y + i, 2, line, summary_color)
            except curses.error:
                pass
        
        # ヘッダー表示
        header_y = 5
        headers = ["状態", "操作", "ソース", "ターゲット", "進捗", "速度", "残り時間"]
        header_widths = [8, 6, 25, 25, 10, 12, 10]
        
        header_line = ""
        for i, (header, width) in enumerate(zip(headers, header_widths)):
            header_line += f"{header:<{width}} "
        
        try:
            header_color = self.color_manager.get_dialog_color('title') if self.color_manager else curses.A_REVERSE
            stdscr.addstr(header_y, 2, header_line, header_color)
        except curses.error:
            pass
        
        # 区切り線
        separator = "-" * (max_x - 4)
        try:
            separator_color = self.color_manager.get_dialog_color('text') if self.color_manager else curses.A_REVERSE
            stdscr.addstr(header_y + 1, 2, separator, separator_color)
        except curses.error:
            pass
        
        # 転送一覧表示
        list_start_y = header_y + 2
        visible_height = max_y - list_start_y - 3  # フッター用スペース
        
        # スクロール調整
        if selected < self.scroll_offset:
            self.scroll_offset = selected
        elif selected >= self.scroll_offset + visible_height:
            self.scroll_offset = selected - visible_height + 1
        
        for i in range(visible_height):
            transfer_index = self.scroll_offset + i
            if transfer_index >= len(self.transfers):
                break
            
            transfer = self.transfers[transfer_index]
            y = list_start_y + i
            
            # 選択行の強調
            attrs = curses.A_REVERSE if transfer_index == selected else 0
            
            # 状態表示
            status_text = self._get_status_display(transfer['status'])
            
            # 進捗表示
            progress_text = f"{transfer['progress']*100:5.1f}%"
            if transfer['status'] == 'in_progress':
                # 進捗バーを追加
                bar_width = 8
                filled = int(transfer['progress'] * bar_width)
                progress_bar = "█" * filled + "░" * (bar_width - filled)
                progress_text = f"{progress_bar} {transfer['progress']*100:3.0f}%"
            
            # 速度表示
            if transfer['transfer_speed'] > 0:
                speed_text = self._format_speed(transfer['transfer_speed'])
            else:
                speed_text = "--"
            
            # 残り時間表示
            if transfer['estimated_time_remaining'] > 0:
                time_text = self._format_time_remaining(transfer['estimated_time_remaining'])
            else:
                time_text = "--"
            
            # パス表示（短縮）
            src_display = truncate_string_by_width(transfer['src_path'], 23)
            dst_display = truncate_string_by_width(transfer['dst_path'], 23)
            
            # 行の構成
            line_parts = [
                f"{status_text:<8}",
                f"{transfer['operation']:<6}",
                f"{src_display:<25}",
                f"{dst_display:<25}",
                f"{progress_text:<10}",
                f"{speed_text:<12}",
                f"{time_text:<10}"
            ]
            
            line = " ".join(line_parts)
            
            try:
                # 色分け
                color_pair = self._get_transfer_color(transfer['status'])
                stdscr.addstr(y, 2, line[:max_x-3], attrs | color_pair)
            except curses.error:
                pass
        
        # フッター表示
        footer_y = max_y - 2
        footer_lines = [
            "操作: [P]一時停止/再開 [C]キャンセル [D]削除(完了済み) [R]更新 [Q]戻る",
            "矢印キーで選択移動"
        ]
        
        footer_color = self.color_manager.get_dialog_color('text') if self.color_manager else curses.A_REVERSE
        for i, line in enumerate(footer_lines):
            try:
                stdscr.addstr(footer_y + i, 2, line, footer_color)
            except curses.error:
                pass
        
        stdscr.refresh()
    
    def _get_status_display(self, status: str) -> str:
        """状態表示文字列を取得"""
        status_map = {
            'waiting': '待機中',
            'in_progress': '実行中',
            'paused': '一時停止',
            'completed': '完了',
            'failed': '失敗',
            'cancelled': 'キャンセル'
        }
        return status_map.get(status, status)
    
    def _get_transfer_color(self, status: str) -> int:
        """転送状態に応じた色を取得"""
        if not self.color_manager:
            return 0
        
        # ColorManagerの新しいメソッドを使用
        return self.color_manager.get_transfer_color(status)
    
    def _format_speed(self, bytes_per_sec: float) -> str:
        """転送速度をフォーマット"""
        if bytes_per_sec == 0:
            return "0 B/s"
        
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        unit_index = 0
        speed = bytes_per_sec
        
        while speed >= 1024 and unit_index < len(units) - 1:
            speed /= 1024
            unit_index += 1
        
        return f"{speed:.1f} {units[unit_index]}"
    
    def _format_time_remaining(self, seconds: float) -> str:
        """残り時間をフォーマット"""
        if seconds <= 0:
            return "--:--"
        
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}:{minutes:02d}:00"


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