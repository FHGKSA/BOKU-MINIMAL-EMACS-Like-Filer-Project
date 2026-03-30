#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2pane TUI Filer - 色管理機能

このモジュールはls --color=auto互換の色分け機能を実装します。
"""

import curses
import os
import stat
from typing import Dict, Optional, Tuple


class ColorManager:
    """色管理クラス"""
    
    def __init__(self, use_color: bool = True):
        """
        初期化
        
        Args:
            use_color: 色分けを使用するか
        """
        self.use_color = use_color
        self.color_support = self._detect_color_support()
        self.color_pairs = {}
        self.ls_colors = {}
        
        if self.use_color and curses.has_colors():
            self._initialize_colors()
            self._load_ls_colors()

    def _detect_color_support(self) -> str:
        """色サポートレベルの検出"""
        if not self.use_color:
            return 'none'
        
        if not curses.has_colors():
            return 'none'
        
        # 色数の確認
        if curses.can_change_color():
            return '24bit'
        elif curses.COLORS >= 256:
            return '256color'
        elif curses.COLORS >= 16:
            return '16color'
        elif curses.COLORS >= 8:
            return '8color'
        else:
            return 'mono'

    def _initialize_colors(self):
        """色の初期化"""
        curses.start_color()
        curses.use_default_colors()
        
        # 基本色ペアの定義
        self._define_basic_color_pairs()

    def _define_basic_color_pairs(self):
        """基本色ペアの定義"""
        # カラーペアID管理
        pair_id = 1
        
        # ファイルタイプ別色定義
        color_definitions = {
            # ファイルタイプ
            'directory': (curses.COLOR_BLUE, -1),
            'executable': (curses.COLOR_GREEN, -1),
            'symlink': (curses.COLOR_CYAN, -1),
            'device': (curses.COLOR_YELLOW, -1),
            'pipe': (curses.COLOR_YELLOW, curses.COLOR_BLACK),
            'socket': (curses.COLOR_MAGENTA, -1),
            'broken_link': (curses.COLOR_WHITE, curses.COLOR_RED),  # 壊れたリンク
            
            # 拡張子別
            'archive': (curses.COLOR_RED, -1),
            'audio': (curses.COLOR_MAGENTA, -1),  
            'video': (curses.COLOR_RED, -1),
            'image': (curses.COLOR_YELLOW, -1),
            'document': (curses.COLOR_WHITE, -1),
            'programming': (curses.COLOR_GREEN, -1),
            'config': (curses.COLOR_CYAN, -1),
            'temporary': (90, -1),  # 暗いグレー（256色対応時）
            
            # サイズ別
            'size_small': (curses.COLOR_WHITE, -1),
            'size_medium': (curses.COLOR_GREEN, -1),
            'size_large': (curses.COLOR_YELLOW, -1),
            'size_huge': (curses.COLOR_RED, -1),
            
            # 日付別  
            'date_today': (curses.COLOR_GREEN, -1),
            'date_yesterday': (curses.COLOR_YELLOW, -1),
            'date_week': (curses.COLOR_WHITE, -1),
            'date_old': (curses.COLOR_BLACK, -1),
            
            # UI要素
            'cursor': (-1, curses.COLOR_WHITE),
            'selected': (curses.COLOR_WHITE, curses.COLOR_BLUE),
            'status': (curses.COLOR_WHITE, curses.COLOR_BLACK),
            
            # ダイアログ用
            'dialog_bg': (curses.COLOR_BLACK, curses.COLOR_WHITE),
            'dialog_title': (curses.COLOR_WHITE, curses.COLOR_BLUE),
            'dialog_text': (curses.COLOR_BLACK, curses.COLOR_WHITE),
            'dialog_options': (curses.COLOR_BLUE, curses.COLOR_WHITE),
            
            # 転送状態用（背景色あり）
            'transfer_waiting': (curses.COLOR_BLACK, curses.COLOR_YELLOW),
            'transfer_in_progress': (curses.COLOR_BLACK, curses.COLOR_GREEN),
            'transfer_paused': (curses.COLOR_WHITE, curses.COLOR_BLUE),
            'transfer_completed': (curses.COLOR_BLACK, curses.COLOR_CYAN),
            'transfer_failed': (curses.COLOR_WHITE, curses.COLOR_RED),
            'transfer_cancelled': (curses.COLOR_WHITE, curses.COLOR_MAGENTA),
        }
        
        # 色ペアの作成
        for name, (fg, bg) in color_definitions.items():
            try:
                curses.init_pair(pair_id, fg, bg)
                self.color_pairs[name] = curses.color_pair(pair_id)
                pair_id += 1
                
                # 最大色ペア数をチェック
                if pair_id >= curses.COLOR_PAIRS:
                    break
                    
            except curses.error:
                # 色設定エラー時はデフォルト色を使用
                self.color_pairs[name] = 0

    def _load_ls_colors(self):
        """LS_COLORS環境変数の読み込み"""
        ls_colors = os.environ.get('LS_COLORS', '')
        
        # デフォルトLS_COLORS設定
        default_ls_colors = {
            # ファイルタイプ
            'di': '1;34',    # ディレクトリ (青・太字)
            'ex': '1;32',    # 実行ファイル (緑・太字)
            'ln': '1;36',    # シンボリックリンク (水色・太字)
            'pi': '40;33',   # FIFO (黄色背景)
            'so': '1;35',    # ソケット (マゼンタ・太字)
            'bd': '40;33;1', # ブロックデバイス
            'cd': '40;33;1', # キャラクタデバイス
            'or': '40;31;1', # 壊れたリンク
            
            # 拡張子別  
            '*.zip': '1;31', '*.tar': '1;31', '*.gz': '1;31',  # アーカイブ
            '*.mp3': '35', '*.wav': '35', '*.flac': '35',      # 音声
            '*.mp4': '31', '*.avi': '31', '*.mkv': '31',       # 動画  
            '*.jpg': '33', '*.png': '33', '*.gif': '33',       # 画像
            '*.c': '32', '*.py': '32', '*.js': '32',           # プログラム
            '*.conf': '36', '*.json': '36', '*.yml': '36',     # 設定
            '*.tmp': '90', '*.bak': '90', '*.swp': '90',       # 一時
        }
        
        # 環境変数から設定を読み込み
        if ls_colors:
            for item in ls_colors.split(':'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    default_ls_colors[key] = value
        
        self.ls_colors = default_ls_colors

    def get_file_color(self, file_item) -> int:
        """ファイル項目の色を取得"""
        if not self.use_color or self.color_support == 'none':
            return 0
        
        # ファイルタイプによる判定
        if file_item.is_link:
            # シンボリックリンクの場合
            if hasattr(file_item, 'is_broken_link') and file_item.is_broken_link:
                return self.color_pairs.get('broken_link', 0)
            else:
                return self.color_pairs.get('symlink', 0)
        elif file_item.is_dir:
            return self.color_pairs.get('directory', 0)
        elif self._is_executable(file_item):
            return self.color_pairs.get('executable', 0)
        
        # 拡張子による判定  
        ext = file_item.extension.lower()
        if ext:
            if ext in ['zip', 'tar', 'gz', 'bz2', 'xz', '7z', 'rar']:
                return self.color_pairs.get('archive', 0)
            elif ext in ['mp3', 'wav', 'flac', 'ogg', 'aac', 'm4a']:
                return self.color_pairs.get('audio', 0)
            elif ext in ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'webm']:
                return self.color_pairs.get('video', 0)
            elif ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp']:
                return self.color_pairs.get('image', 0)
            elif ext in ['py', 'js', 'html', 'css', 'c', 'cpp', 'java', 'rs']:
                return self.color_pairs.get('programming', 0)
            elif ext in ['conf', 'cfg', 'ini', 'json', 'yml', 'yaml', 'xml']:
                return self.color_pairs.get('config', 0)
            elif ext in ['tmp', 'bak', 'swp', '~']:
                return self.color_pairs.get('temporary', 0)
            elif ext in ['txt', 'md', 'pdf', 'doc', 'docx', 'odt']:
                return self.color_pairs.get('document', 0)
        
        # デフォルト色
        return 0

    def _is_executable(self, file_item) -> bool:
        """実行可能ファイルかどうかの判定"""
        try:
            # Unix権限での実行可能判定
            if file_item.mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                return True
            
            # 実行可能拡張子での判定
            ext = file_item.extension.lower()
            executable_exts = ['exe', 'msi', 'bin', 'run', 'appimage', 'deb', 'rpm']
            return ext in executable_exts
            
        except:
            return False

    def get_size_color(self, size: int) -> int:
        """ファイルサイズの色を取得"""
        if not self.use_color or self.color_support == 'none':
            return 0
        
        if size == 0:
            return self.color_pairs.get('size_small', 0)
        elif size < 1024:  # < 1KB
            return self.color_pairs.get('size_small', 0)
        elif size < 1024 * 1024:  # < 1MB
            return self.color_pairs.get('size_medium', 0)
        elif size < 100 * 1024 * 1024:  # < 100MB
            return self.color_pairs.get('size_large', 0)
        else:  # >= 100MB
            return self.color_pairs.get('size_huge', 0)

    def get_date_color(self, mtime: float) -> int:
        """更新日時の色を取得"""
        if not self.use_color or self.color_support == 'none':
            return 0
        
        import time
        now = time.time()
        diff = now - mtime
        
        if diff < 86400:  # 24時間以内
            return self.color_pairs.get('date_today', 0)
        elif diff < 2 * 86400:  # 48時間以内
            return self.color_pairs.get('date_yesterday', 0)  
        elif diff < 7 * 86400:  # 1週間以内
            return self.color_pairs.get('date_week', 0)
        else:  # それ以前
            return self.color_pairs.get('date_old', 0)

    def get_cursor_color(self) -> int:
        """カーソル行の色を取得"""
        return self.color_pairs.get('cursor', curses.A_REVERSE)

    def get_selected_color(self) -> int:
        """選択済みファイルの色を取得"""
        return self.color_pairs.get('selected', 0)

    def get_dialog_color(self, element: str) -> int:
        """ダイアログ要素の色を取得"""
        dialog_color_map = {
            'background': 'dialog_bg',
            'title': 'dialog_title', 
            'text': 'dialog_text',
            'options': 'dialog_options'
        }
        color_name = dialog_color_map.get(element, 'dialog_text')
        return self.color_pairs.get(color_name, curses.A_REVERSE)

    def get_transfer_color(self, status: str) -> int:
        """転送状態の色を取得"""
        transfer_color_map = {
            'waiting': 'transfer_waiting',
            'in_progress': 'transfer_in_progress',
            'paused': 'transfer_paused',
            'completed': 'transfer_completed',
            'failed': 'transfer_failed',
            'cancelled': 'transfer_cancelled'
        }
        color_name = transfer_color_map.get(status, 'transfer_waiting')
        return self.color_pairs.get(color_name, 0)

    def is_color_supported(self) -> bool:
        """色分けがサポートされているかの判定"""
        return self.use_color and self.color_support != 'none'

    def get_fallback_marker(self, file_item) -> str:
        """色非対応環境でのマーカー取得"""
        if file_item.is_dir:
            return "/"
        elif file_item.is_link:
            return "@"
        elif self._is_executable(file_item):
            return "*"
        else:
            return ""