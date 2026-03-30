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
from typing import List, Optional, Tuple, Callable, Dict, Any
import time
import threading
from enum import Enum
import queue
import uuid


class FileOperationError(Exception):
    """ファイル操作エラー"""
    pass


class TransferStatus(Enum):
    """転送ステータス"""
    WAITING = "waiting"        # 待機中
    IN_PROGRESS = "in_progress"  # 実行中
    PAUSED = "paused"          # 一時停止
    COMPLETED = "completed"    # 完了
    FAILED = "failed"          # 失敗
    CANCELLED = "cancelled"    # キャンセル


class BackgroundTransfer:
    """バックグラウンド転送クラス"""
    
    def __init__(self, transfer_id: str, operation: str, src_path: str, 
                 dst_path: str, priority: int = 0):
        """
        初期化
        
        Args:
            transfer_id: 転送ID
            operation: 操作タイプ ('copy', 'move')
            src_path: 転送元パス
            dst_path: 転送先パス  
            priority: 優先度（高い数字が高優先度）
        """
        self.id = transfer_id
        self.operation = operation
        self.src_path = Path(src_path)
        self.dst_path = Path(dst_path)
        self.priority = priority
        
        # 転送状態
        self.status = TransferStatus.WAITING
        self.progress = 0.0  # 0.0 - 1.0
        self.bytes_transferred = 0
        self.total_bytes = 0
        self.transfer_speed = 0.0  # bytes/sec
        self.start_time = None
        self.estimated_time_remaining = 0
        
        # エラー情報
        self.error_message = ""
        
        # 制御用
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()
        
    def get_info(self) -> Dict[str, Any]:
        """転送情報を取得"""
        with self._lock:
            return {
                'id': self.id,
                'operation': self.operation,
                'src_path': str(self.src_path),
                'dst_path': str(self.dst_path),
                'status': self.status.value,
                'progress': self.progress,
                'bytes_transferred': self.bytes_transferred,
                'total_bytes': self.total_bytes,
                'transfer_speed': self.transfer_speed,
                'estimated_time_remaining': self.estimated_time_remaining,
                'error_message': self.error_message
            }
    
    def pause(self):
        """転送を一時停止"""
        with self._lock:
            if self.status == TransferStatus.IN_PROGRESS:
                self.status = TransferStatus.PAUSED
                self._pause_event.set()
    
    def resume(self):
        """転送を再開"""
        with self._lock:
            if self.status == TransferStatus.PAUSED:
                self.status = TransferStatus.IN_PROGRESS
                self._pause_event.clear()
    
    def cancel(self):
        """転送をキャンセル"""
        with self._lock:
            if self.status in [TransferStatus.WAITING, TransferStatus.IN_PROGRESS, TransferStatus.PAUSED]:
                self.status = TransferStatus.CANCELLED
                self._cancel_event.set()
    
    def execute(self):
        """転送を実行"""
        try:
            with self._lock:
                if self.status != TransferStatus.WAITING:
                    return
                self.status = TransferStatus.IN_PROGRESS
                self.start_time = time.time()
            
            # ファイルサイズを取得
            if self.src_path.is_file():
                self.total_bytes = self.src_path.stat().st_size
            elif self.src_path.is_dir():
                self.total_bytes = self._calculate_dir_size(self.src_path)
            
            # 転送実行
            if self.operation == 'copy':
                self._copy_with_progress()
            elif self.operation == 'move':
                self._move_with_progress()
            
            with self._lock:
                if not self._cancel_event.is_set():
                    self.status = TransferStatus.COMPLETED
                    self.progress = 1.0
                    
        except Exception as e:
            with self._lock:
                self.status = TransferStatus.FAILED
                self.error_message = str(e)
    
    def _calculate_dir_size(self, path: Path) -> int:
        """ディレクトリサイズ計算"""
        total_size = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                    except (OSError, FileNotFoundError):
                        pass
        except (OSError, PermissionError):
            pass
        return total_size
    
    def _copy_with_progress(self):
        """進捗付きコピー"""
        if self.src_path.is_file():
            self._copy_file_with_progress(self.src_path, self.dst_path)
        elif self.src_path.is_dir():
            self._copy_directory_with_progress(self.src_path, self.dst_path)
    
    def _move_with_progress(self):
        """進捗付き移動"""
        # 同一ファイルシステムなら高速移動
        if self.src_path.stat().st_dev == self.dst_path.parent.stat().st_dev:
            self.src_path.rename(self.dst_path)
            with self._lock:
                self.bytes_transferred = self.total_bytes
                self.progress = 1.0
        else:
            # 異なるファイルシステムならコピー後削除
            self._copy_with_progress()
            if not self._cancel_event.is_set():
                if self.src_path.is_file():
                    self.src_path.unlink()
                elif self.src_path.is_dir():
                    shutil.rmtree(str(self.src_path))
    
    def _copy_file_with_progress(self, src: Path, dst: Path):
        """ファイルを進捗付きでコピー"""
        # 親ディレクトリを作成
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        buffer_size = 64 * 1024  # 64KB
        
        with src.open('rb') as src_file, dst.open('wb') as dst_file:
            while not self._cancel_event.is_set():
                # 一時停止チェック
                while self._pause_event.is_set() and not self._cancel_event.is_set():
                    time.sleep(0.1)
                
                if self._cancel_event.is_set():
                    break
                
                chunk = src_file.read(buffer_size)
                if not chunk:
                    break
                
                dst_file.write(chunk)
                
                with self._lock:
                    self.bytes_transferred += len(chunk)
                    self.progress = min(1.0, self.bytes_transferred / self.total_bytes) if self.total_bytes > 0 else 0.0
                    
                    # 転送速度計算
                    elapsed_time = time.time() - self.start_time
                    if elapsed_time > 0:
                        self.transfer_speed = self.bytes_transferred / elapsed_time
                        
                        # 残り時間推定
                        if self.transfer_speed > 0 and self.progress > 0:
                            remaining_bytes = self.total_bytes - self.bytes_transferred
                            self.estimated_time_remaining = remaining_bytes / self.transfer_speed
    
    def _copy_directory_with_progress(self, src: Path, dst: Path):
        """ディレクトリを進捗付きでコピー"""
        dst.mkdir(parents=True, exist_ok=True)
        
        for item in src.rglob('*'):
            if self._cancel_event.is_set():
                break
                
            # 一時停止チェック
            while self._pause_event.is_set() and not self._cancel_event.is_set():
                time.sleep(0.1)
            
            relative_path = item.relative_to(src)
            dest_path = dst / relative_path
            
            try:
                if item.is_dir():
                    dest_path.mkdir(parents=True, exist_ok=True)
                elif item.is_file():
                    self._copy_file_with_progress(item, dest_path)
            except (OSError, PermissionError) as e:
                # エラーは記録するが処理は続行
                pass


class TransferQueue:
    """転送キュークラス"""
    
    def __init__(self):
        """初期化"""
        self.transfers: Dict[str, BackgroundTransfer] = {}
        self._queue = queue.PriorityQueue()
        self._lock = threading.Lock()
        self._worker_thread = None
        self._stop_event = threading.Event()
        self._running = False
        
    def start(self):
        """キュー処理開始"""
        if not self._running:
            self._running = True
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()
    
    def stop(self):
        """キュー処理停止"""
        self._running = False
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)
    
    def add_transfer(self, operation: str, src_path: str, dst_path: str, 
                    priority: int = 0) -> str:
        """転送をキューに追加"""
        transfer_id = str(uuid.uuid4())
        transfer = BackgroundTransfer(transfer_id, operation, src_path, dst_path, priority)
        
        with self._lock:
            self.transfers[transfer_id] = transfer
            # 優先度の逆順でキューに追加（高優先度を先に処理）
            self._queue.put((-priority, transfer_id))
        
        return transfer_id
    
    def get_transfer(self, transfer_id: str) -> Optional[BackgroundTransfer]:
        """転送情報を取得"""
        with self._lock:
            return self.transfers.get(transfer_id)
    
    def get_all_transfers(self) -> List[Dict[str, Any]]:
        """全転送情報を取得"""
        with self._lock:
            return [transfer.get_info() for transfer in self.transfers.values()]
    
    def pause_transfer(self, transfer_id: str):
        """転送を一時停止"""
        transfer = self.get_transfer(transfer_id)
        if transfer:
            transfer.pause()
    
    def resume_transfer(self, transfer_id: str):
        """転送を再開"""
        transfer = self.get_transfer(transfer_id)
        if transfer:
            transfer.resume()
    
    def cancel_transfer(self, transfer_id: str):
        """転送をキャンセル"""
        transfer = self.get_transfer(transfer_id)
        if transfer:
            transfer.cancel()
    
    def remove_completed_transfers(self):
        """完了した転送をクリア"""
        with self._lock:
            completed_ids = [
                tid for tid, transfer in self.transfers.items()
                if transfer.status in [TransferStatus.COMPLETED, TransferStatus.FAILED, TransferStatus.CANCELLED]
            ]
            for tid in completed_ids:
                del self.transfers[tid]
    
    def _worker(self):
        """ワーカースレッド"""
        while not self._stop_event.is_set():
            try:
                # 1秒タイムアウトでキューから取得
                try:
                    priority, transfer_id = self._queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                transfer = self.get_transfer(transfer_id)
                if transfer and not self._stop_event.is_set():
                    transfer.execute()
                    
            except Exception as e:
                # ワーカーエラーは記録するが処理は継続
                pass


# FileOperationsクラスに転送キューを統合
class FileOperations:
    """ファイル操作クラス"""
    
    def __init__(self):
        """初期化"""
        self.operation_history = []
        self.max_history = 100
        
        # バックグラウンド転送キュー
        self.transfer_queue = TransferQueue()
        self.transfer_queue.start()

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

    # バックグラウンド転送機能
    
    def start_background_copy(self, src_path: str, dst_path: str, priority: int = 0) -> str:
        """
        バックグラウンドコピーを開始
        
        Args:
            src_path: コピー元パス
            dst_path: コピー先パス
            priority: 優先度（高い数字が高優先度）
            
        Returns:
            転送ID
        """
        transfer_id = self.transfer_queue.add_transfer('copy', src_path, dst_path, priority)
        self._add_to_history('background_copy_start', f"{src_path} -> {dst_path} (ID: {transfer_id})")
        return transfer_id
    
    def start_background_move(self, src_path: str, dst_path: str, priority: int = 0) -> str:
        """
        バックグラウンド移動を開始
        
        Args:
            src_path: 移動元パス
            dst_path: 移動先パス
            priority: 優先度（高い数字が高優先度）
            
        Returns:
            転送ID
        """
        transfer_id = self.transfer_queue.add_transfer('move', src_path, dst_path, priority)
        self._add_to_history('background_move_start', f"{src_path} -> {dst_path} (ID: {transfer_id})")
        return transfer_id
    
    def get_transfer_info(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """
        転送情報を取得
        
        Args:
            transfer_id: 転送ID
            
        Returns:
            転送情報辞書
        """
        transfer = self.transfer_queue.get_transfer(transfer_id)
        return transfer.get_info() if transfer else None
    
    def get_all_transfers(self) -> List[Dict[str, Any]]:
        """全転送情報を取得"""
        return self.transfer_queue.get_all_transfers()
    
    def pause_transfer(self, transfer_id: str) -> bool:
        """
        転送を一時停止
        
        Args:
            transfer_id: 転送ID
            
        Returns:
            成功時True
        """
        try:
            self.transfer_queue.pause_transfer(transfer_id)
            self._add_to_history('transfer_pause', f"Transfer paused (ID: {transfer_id})")
            return True
        except Exception:
            return False
    
    def resume_transfer(self, transfer_id: str) -> bool:
        """
        転送を再開
        
        Args:
            transfer_id: 転送ID
            
        Returns:
            成功時True
        """
        try:
            self.transfer_queue.resume_transfer(transfer_id)
            self._add_to_history('transfer_resume', f"Transfer resumed (ID: {transfer_id})")
            return True
        except Exception:
            return False
    
    def cancel_transfer(self, transfer_id: str) -> bool:
        """
        転送をキャンセル
        
        Args:
            transfer_id: 転送ID
            
        Returns:
            成功時True
        """
        try:
            self.transfer_queue.cancel_transfer(transfer_id)
            self._add_to_history('transfer_cancel', f"Transfer cancelled (ID: {transfer_id})")
            return True
        except Exception:
            return False
    
    def clear_completed_transfers(self):
        """完了した転送をクリア"""
        self.transfer_queue.remove_completed_transfers()
        self._add_to_history('transfers_clear', "Completed transfers cleared")
    
    def get_active_transfer_count(self) -> int:
        """アクティブな転送数を取得"""
        transfers = self.get_all_transfers()
        active_statuses = ['waiting', 'in_progress', 'paused']
        return len([t for t in transfers if t['status'] in active_statuses])
    
    def get_transfer_summary(self) -> Dict[str, int]:
        """転送状況サマリーを取得"""
        transfers = self.get_all_transfers()
        summary = {
            'waiting': 0,
            'in_progress': 0,
            'paused': 0,
            'completed': 0,
            'failed': 0,
            'cancelled': 0
        }
        
        for transfer in transfers:
            status = transfer['status']
            if status in summary:
                summary[status] += 1
        
        return summary
    
    def format_transfer_speed(self, bytes_per_sec: float) -> str:
        """転送速度を読みやすい形式でフォーマット"""
        if bytes_per_sec == 0:
            return "0 B/s"
        
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        unit_index = 0
        speed = bytes_per_sec
        
        while speed >= 1024 and unit_index < len(units) - 1:
            speed /= 1024
            unit_index += 1
        
        return f"{speed:.1f} {units[unit_index]}"
    
    def format_time_remaining(self, seconds: float) -> str:
        """残り時間を読みやすい形式でフォーマット"""
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
    
    def shutdown(self):
        """シャットダウン処理"""
        if hasattr(self, 'transfer_queue'):
            self.transfer_queue.stop()

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