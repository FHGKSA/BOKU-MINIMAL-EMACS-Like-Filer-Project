#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2pane TUI Filer - 設定管理

このモジュールは設定ファイルの読み込みと管理を行います。
"""

import os
import configparser
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """設定管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.ini"
        self.colors_file = self.config_dir / "colors.conf"
        self.keybinds_file = self.config_dir / "keybinds.conf"
        
        # デフォルト設定
        self.defaults = self._get_default_config()
        
        # 現在の設定
        self.settings = self.defaults.copy()
        
        # 設定ファイルの読み込み
        self._load_config()

    def _get_config_dir(self) -> Path:
        """設定ディレクトリの取得"""
        # XDG Base Directory準拠
        xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
        if xdg_config_home:
            config_dir = Path(xdg_config_home) / '2pane-filer'
        else:
            config_dir = Path.home() / '.config' / '2pane-filer'
        
        # ディレクトリの作成
        config_dir.mkdir(parents=True, exist_ok=True)
        
        return config_dir

    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定の取得"""
        return {
            # 表示設定
            'use_color': True,
            'show_hidden': False,
            'show_permissions': True,
            'column_separator': ' ',
            'cursor_highlight': 'full_line',  # full_line, marker_only, none
            'preserve_colors_on_cursor': True,
            
            # ソート設定
            'default_sort': 'name',  # name, ext, size, mtime
            'sort_directories_first': True,
            'case_sensitive_sort': False,
            
            # 動作設定
            'confirm_delete': True,
            'confirm_overwrite': True,
            'follow_symlinks': False,
            'auto_refresh': True,
            'double_esc_exit': True,
            
            # 外部プログラム
            'default_editor': os.environ.get('EDITOR', 'vi'),
            'default_shell': os.environ.get('SHELL', '/bin/bash'),
            
            # 文字コード設定
            'encoding': 'utf-8',
            'fallback_encoding': 'shift_jis',
            
            # パフォーマンス
            'max_files_display': 10000,
            'refresh_interval': 1.0,
            
            # デバッグ
            'debug_mode': False,
            'log_file': str(self.config_dir / 'debug.log'),
        }

    def _load_config(self):
        """設定ファイルの読み込み"""
        if not self.config_file.exists():
            self._create_default_config()
            return
        
        try:
            config = configparser.ConfigParser()
            config.read(self.config_file, encoding='utf-8')
            
            # 各セクションから設定を読み込み
            if 'display' in config:
                self._load_section(config['display'], 'display')
            
            if 'behavior' in config:
                self._load_section(config['behavior'], 'behavior')
            
            if 'external' in config:
                self._load_section(config['external'], 'external')
            
            if 'encoding' in config:
                self._load_section(config['encoding'], 'encoding')
                
        except Exception as e:
            print(f"設定ファイル読み込みエラー: {e}")
            # エラー時はデフォルト設定を使用

    def _load_section(self, section: configparser.SectionProxy, section_name: str):
        """設定セクションの読み込み"""
        for key, value in section.items():
            if key in self.settings:
                # 型に応じて変換
                default_value = self.defaults[key]
                try:
                    if isinstance(default_value, bool):
                        self.settings[key] = section.getboolean(key)
                    elif isinstance(default_value, int):
                        self.settings[key] = section.getint(key)
                    elif isinstance(default_value, float):
                        self.settings[key] = section.getfloat(key)
                    else:
                        self.settings[key] = value
                except ValueError:
                    # 変換エラー時はデフォルト値を使用
                    pass

    def _create_default_config(self):
        """デフォルト設定ファイルの作成"""
        config = configparser.ConfigParser()
        
        # 表示設定
        config['display'] = {
            'use_color': str(self.defaults['use_color']),
            'show_hidden': str(self.defaults['show_hidden']),
            'show_permissions': str(self.defaults['show_permissions']),
            'column_separator': self.defaults['column_separator'],
            'cursor_highlight': self.defaults['cursor_highlight'],
            'preserve_colors_on_cursor': str(self.defaults['preserve_colors_on_cursor']),
        }
        
        # 動作設定
        config['behavior'] = {
            'default_sort': self.defaults['default_sort'],
            'sort_directories_first': str(self.defaults['sort_directories_first']),
            'case_sensitive_sort': str(self.defaults['case_sensitive_sort']),
            'confirm_delete': str(self.defaults['confirm_delete']),
            'confirm_overwrite': str(self.defaults['confirm_overwrite']),
            'follow_symlinks': str(self.defaults['follow_symlinks']),
            'auto_refresh': str(self.defaults['auto_refresh']),
            'double_esc_exit': str(self.defaults['double_esc_exit']),
        }
        
        # 外部プログラム
        config['external'] = {
            'default_editor': self.defaults['default_editor'],
            'default_shell': self.defaults['default_shell'],
        }
        
        # 文字コード設定
        config['encoding'] = {
            'encoding': self.defaults['encoding'],
            'fallback_encoding': self.defaults['fallback_encoding'],
        }
        
        # パフォーマンス設定
        config['performance'] = {
            'max_files_display': str(self.defaults['max_files_display']),
            'refresh_interval': str(self.defaults['refresh_interval']),
        }
        
        # デバッグ設定
        config['debug'] = {
            'debug_mode': str(self.defaults['debug_mode']),
            'log_file': self.defaults['log_file'],
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
        except Exception as e:
            print(f"設定ファイル作成エラー: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """設定値の取得"""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        """設定値の設定"""
        self.settings[key] = value

    def save(self):
        """設定の保存"""
        config = configparser.ConfigParser()
        
        # 現在の設定を各セクションに分類
        display_keys = ['use_color', 'show_hidden', 'show_permissions', 
                       'column_separator', 'cursor_highlight', 
                       'preserve_colors_on_cursor']
        behavior_keys = ['default_sort', 'sort_directories_first', 
                        'case_sensitive_sort', 'confirm_delete', 
                        'confirm_overwrite', 'follow_symlinks', 
                        'auto_refresh', 'double_esc_exit']
        external_keys = ['default_editor', 'default_shell']
        encoding_keys = ['encoding', 'fallback_encoding']
        performance_keys = ['max_files_display', 'refresh_interval']
        debug_keys = ['debug_mode', 'log_file']
        
        # セクション毎に設定を書き込み
        config['display'] = {k: str(self.settings[k]) for k in display_keys 
                            if k in self.settings}
        config['behavior'] = {k: str(self.settings[k]) for k in behavior_keys 
                             if k in self.settings}
        config['external'] = {k: str(self.settings[k]) for k in external_keys 
                             if k in self.settings}
        config['encoding'] = {k: str(self.settings[k]) for k in encoding_keys 
                             if k in self.settings}
        config['performance'] = {k: str(self.settings[k]) for k in performance_keys 
                                if k in self.settings}
        config['debug'] = {k: str(self.settings[k]) for k in debug_keys 
                          if k in self.settings}
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
        except Exception as e:
            print(f"設定ファイル保存エラー: {e}")

    def get_colors_config_path(self) -> Path:
        """色設定ファイルパスの取得"""
        return self.colors_file

    def get_keybinds_config_path(self) -> Path:
        """キーバインド設定ファイルパスの取得"""
        return self.keybinds_file

    def is_debug_mode(self) -> bool:
        """デバッグモードかどうか"""
        return self.get('debug_mode', False)

    def should_use_color(self) -> bool:
        """色分けを使用するか"""
        return self.get('use_color', True)

    def should_show_hidden(self) -> bool:
        """隠しファイルを表示するか"""
        return self.get('show_hidden', False)

    def should_confirm_delete(self) -> bool:
        """削除時に確認するか"""
        return self.get('confirm_delete', True)

    def get_default_editor(self) -> str:
        """デフォルトエディタ取得"""
        return self.get('default_editor', 'vi')

    def get_default_sort(self) -> str:
        """デフォルトソート方式取得"""
        return self.get('default_sort', 'name')