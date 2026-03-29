#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2pane TUI Filer - ファイル操作機能

このモジュールはファイル・ディレクトリの操作機能を実装します。
"""

import os
import shutil
import stat
from pathlib import Path
from typing import List, Optional, Tuple, Callable
import time
import threading


class FileOperationError(Exception):
    """ファイル操作エラー"""
    pass


class FileOperations:
    """ファイル操作クラス"""
    
    def __init__(self):
        """初期化"""
        self.operation_history = []
        self.max_history = 100

    def delete_file(self, file_path: str, confirm_callback: Optional[Callable] = None) -> bool:
        """
        ファイル削除
        
        Args:
            file_path: 削除するファイルパス
            confirm_callback: 確認コールバック関数
            
        Returns:
            削除成功時True
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileOperationError(f"ファイルが存在しません: {file_path}")
        
        # 確認コールバックがある場合は実行
        if confirm_callback:
            if not confirm_callback(f"削除しますか?\n{file_path}"):
                return False
        
        try:
            if path.is_dir():
                # ディレクトリの削除
                shutil.rmtree(str(path))
            else:
                # ファイルの削除
                path.unlink()
            
            # 履歴に記録
            self._add_to_history('delete', str(path))
            return True
            
        except OSError as e:
            raise FileOperationError(f"削除に失敗しました: {e}")

    def delete_files(self, file_paths: List[str], 
                    confirm_callback: Optional[Callable] = None,
                    progress_callback: Optional[Callable] = None) -> Tuple[int, List[str]]:
        """
        複数ファイルの削除
        
        Args:
            file_paths: 削除するファイルパスのリスト
            confirm_callback: 確認コールバック関数
            progress_callback: 進行状況コールバック関数
            
        Returns:
            (成功数, エラーファイルリスト)
        """
        if not file_paths:
            return 0, []
        
        # 確認コールバックがある場合は実行
        if confirm_callback:
            message = f"{len(file_paths)}個のファイル/ディレクトリを削除しますか?"
            if not confirm_callback(message):
                return 0, []
        
        success_count = 0
        error_files = []
        
        for i, file_path in enumerate(file_paths):
            try:
                if self.delete_file(file_path):
                    success_count += 1
                
                # 進行状況コールバック
                if progress_callback:
                    progress_callback(i + 1, len(file_paths), file_path)
                    
            except FileOperationError as e:
                error_files.append(str(e))
        
        return success_count, error_files

    def copy_file(self, src_path: str, dst_path: str, 
                 overwrite_callback: Optional[Callable] = None,
                 progress_callback: Optional[Callable] = None) -> bool:
        """
        ファイルコピー
        
        Args:
            src_path: コピー元パス
            dst_path: コピー先パス
            overwrite_callback: 上書き確認コールバック
            progress_callback: 進行状況コールバック
            
        Returns:
            コピー成功時True
        """
        src = Path(src_path)
        dst = Path(dst_path)
        
        if not src.exists():
            raise FileOperationError(f"コピー元が存在しません: {src_path}")
        
        # コピー先が存在する場合の確認
        if dst.exists():
            if overwrite_callback:
                if not overwrite_callback(f"上書きしますか?\n{dst_path}"):
                    return False
            else:
                raise FileOperationError(f"コピー先が既に存在します: {dst_path}")
        
        # 親ディレクトリの作成
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if src.is_dir():
                # ディレクトリのコピー
                self._copy_directory(src, dst, progress_callback)
            else:
                # ファイルのコピー
                self._copy_file_with_progress(src, dst, progress_callback)
            
            # 履歴に記録
            self._add_to_history('copy', f"{src_path} -> {dst_path}")
            return True
            
        except OSError as e:
            raise FileOperationError(f"コピーに失敗しました: {e}")

    def move_file(self, src_path: str, dst_path: str,
                 overwrite_callback: Optional[Callable] = None) -> bool:
        """
        ファイル移動
        
        Args:
            src_path: 移動元パス
            dst_path: 移動先パス
            overwrite_callback: 上書き確認コールバック
            
        Returns:
            移動成功時True
        """
        src = Path(src_path)
        dst = Path(dst_path)
        
        if not src.exists():
            raise FileOperationError(f"移動元が存在しません: {src_path}")
        
        # 移動先が存在する場合の確認
        if dst.exists():
            if overwrite_callback:
                if not overwrite_callback(f"上書きしますか?\n{dst_path}"):
                    return False
            else:
                raise FileOperationError(f"移動先が既に存在します: {dst_path}")
        
        # 親ディレクトリの作成
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            shutil.move(str(src), str(dst))
            
            # 履歴に記録
            self._add_to_history('move', f"{src_path} -> {dst_path}")
            return True
            
        except OSError as e:
            raise FileOperationError(f"移動に失敗しました: {e}")

    def rename_file(self, old_path: str, new_name: str) -> bool:
        """
        ファイルリネーム
        
        Args:
            old_path: 現在のファイルパス
            new_name: 新しいファイル名
            
        Returns:
            リネーム成功時True
        """
        old = Path(old_path)
        new = old.parent / new_name
        
        if not old.exists():
            raise FileOperationError(f"ファイルが存在しません: {old_path}")
        
        if new.exists():
            raise FileOperationError(f"同名のファイルが既に存在します: {new_name}")
        
        # ファイル名の妥当性チェック
        if not self._is_valid_filename(new_name):
            raise FileOperationError(f"無効なファイル名です: {new_name}")
        
        try:
            old.rename(new)
            
            # 履歴に記録
            self._add_to_history('rename', f"{old_path} -> {new}")
            return True
            
        except OSError as e:
            raise FileOperationError(f"リネームに失敗しました: {e}")

    def create_directory(self, dir_path: str) -> bool:
        """
        ディレクトリ作成
        
        Args:
            dir_path: 作成するディレクトリパス
            
        Returns:
            作成成功時True
        """
        path = Path(dir_path)
        
        if path.exists():
            raise FileOperationError(f"ディレクトリが既に存在します: {dir_path}")
        
        # ディレクトリ名の妥当性チェック
        if not self._is_valid_filename(path.name):
            raise FileOperationError(f"無効なディレクトリ名です: {path.name}")
        
        try:
            path.mkdir(parents=True, exist_ok=False)
            
            # 履歴に記録
            self._add_to_history('mkdir', dir_path)
            return True
            
        except OSError as e:
            raise FileOperationError(f"ディレクトリ作成に失敗しました: {e}")

    def get_disk_usage(self, path: str) -> Tuple[int, int, int]:
        """
        ディスク使用量取得
        
        Args:
            path: 対象パス
            
        Returns:
            (total, used, free) in bytes
        """
        try:
            stat_info = shutil.disk_usage(path)
            return stat_info.total, stat_info.used, stat_info.free
        except OSError:
            return 0, 0, 0

    def calculate_directory_size(self, dir_path: str,
                                progress_callback: Optional[Callable] = None) -> int:
        """
        ディレクトリサイズ計算
        
        Args:
            dir_path: ディレクトリパス
            progress_callback: 進行状況コールバック
            
        Returns:
            サイズ (bytes)
        """
        total_size = 0
        path = Path(dir_path)
        
        if not path.exists() or not path.is_dir():
            return 0
        
        try:
            for root, dirs, files in os.walk(str(path)):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        total_size += file_path.stat().st_size
                        
                        # 進行状況コールバック
                        if progress_callback:
                            progress_callback(str(file_path), total_size)
                            
                    except (OSError, FileNotFoundError):
                        # アクセス不可ファイルは無視
                        continue
                        
        except OSError:
            # ディレクトリアクセスエラー
            pass
        
        return total_size

    def _copy_file_with_progress(self, src: Path, dst: Path,
                                progress_callback: Optional[Callable] = None):
        """進行状況付きファイルコピー"""
        buffer_size = 64 * 1024  # 64KB
        
        with open(src, 'rb') as src_file:
            with open(dst, 'wb') as dst_file:
                copied = 0
                total_size = src.stat().st_size
                
                while True:
                    buffer = src_file.read(buffer_size)
                    if not buffer:
                        break
                    
                    dst_file.write(buffer)
                    copied += len(buffer)
                    
                    # 進行状況コールバック
                    if progress_callback:
                        progress_callback(copied, total_size, str(src))
        
        # メタデータのコピー
        shutil.copystat(str(src), str(dst))

    def _copy_directory(self, src: Path, dst: Path,
                       progress_callback: Optional[Callable] = None):
        """ディレクトリの再帰的コピー"""
        dst.mkdir(parents=True, exist_ok=True)
        
        for item in src.iterdir():
            dst_item = dst / item.name
            
            if item.is_dir():
                self._copy_directory(item, dst_item, progress_callback)
            else:
                self._copy_file_with_progress(item, dst_item, progress_callback)

    def _is_valid_filename(self, filename: str) -> bool:
        """ファイル名の妥当性チェック"""
        if not filename or filename.strip() == '':
            return False
        
        # 禁止文字のチェック（Unix/Linux基準）
        forbidden_chars = '\0'
        if any(char in filename for char in forbidden_chars):
            return False
        
        # 特殊名のチェック
        if filename in ['.', '..']:
            return False
        
        return True

    def _add_to_history(self, operation: str, details: str):
        """操作履歴への追加"""
        history_item = {
            'timestamp': time.time(),
            'operation': operation,
            'details': details
        }
        
        self.operation_history.append(history_item)
        
        # 履歴数制限
        if len(self.operation_history) > self.max_history:
            self.operation_history.pop(0)

    def get_operation_history(self) -> List[dict]:
        """操作履歴の取得"""
        return self.operation_history.copy()

    def can_access_path(self, path: str) -> bool:
        """パスアクセス可能性チェック"""
        try:
            path_obj = Path(path)
            return path_obj.exists() and os.access(str(path_obj), os.R_OK)
        except:
            return False

    def get_file_permissions(self, file_path: str) -> str:
        """ファイル権限の取得"""
        try:
            path = Path(file_path)
            mode = path.stat().st_mode
            return stat.filemode(mode)
        except:
            return "----------"

    def change_permissions(self, file_path: str, mode: int) -> bool:
        """ファイル権限の変更"""
        try:
            path = Path(file_path)
            path.chmod(mode)
            
            # 履歴に記録
            self._add_to_history('chmod', f"{file_path} -> {oct(mode)}")
            return True
            
        except OSError as e:
            raise FileOperationError(f"権限変更に失敗しました: {e}")