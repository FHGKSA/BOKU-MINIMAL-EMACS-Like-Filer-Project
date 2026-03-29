# BOKU MINIMAL EMACS-Like Filer Project

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Version: Beta](https://img.shields.io/badge/version-0.2.1--beta-orange.svg)](VERSION)

Emacsスタイルのキーバインドを持つ2ペインTUIファイラー（Beta版）

![2pane TUI Filer Screenshot](/.github/demo.gif)

## 概要

このプロジェクトは、LinuxのMidnight CommanderやWindowsの「あふ」を参考にした2ペイン型のTUIファイラーです。Emacsスタイルのキーバインドを採用し、byobu(tmux)との競合を避けた設計になっています。

**注意**: これはBeta版です。基本機能は動作しますが、一部機能が未実装です。

## 🚀 主な特徴

- **2ペイン表示**: 左右のペインでファイル操作
- **Emacsキーバインド**: Ctrl+P/N (上下), Ctrl+A/B/E/F (ペイン移動)
- **ls --color=auto互換**: 標準的な色分け（環境依存文字不使用）
- **カーソル行強調**: 現在行を全行反転表示
- **拡張子分離**: ファイル名と拡張子を独立カラム表示
- **byobu対応**: F1-F12キーを使用せず競合回避
- **文字コード対応**: UTF-8/Shift_JIS混在環境サポート
- **軽量設計**: 高速起動と低メモリ使用

## 動作環境

- Python 3.7以上
- Linux (Ubuntu系を想定)
- cursesライブラリ対応ターミナル
- 最小ターミナルサイズ: 10行 x 40列

## 📦 インストール

### 前提条件
- Python 3.7以上
- Linux (Ubuntu系を想定)
- cursesライブラリ対応ターミナル
- 最小ターミナルサイズ: 10行 x 40列

### インストール手順

```bash
# リポジトリのクローン
git clone https://github.com/FHGKSA/BOKU-MINIMAL-EMACS-Like-Filer-Project.git
cd BOKU-MINIMAL-EMACS-Like-Filer-Project

# 実行権限の付与
chmod +x src/main.py
chmod +x run.sh

# 動作テスト（推奨）
python3 test_basic.py

# 実行
./run.sh
# または
python3 src/main.py
```

## 🎯 使用方法

### クイックスタート

### 基本操作

| キー | 動作 |
|------|------|
| `Ctrl+P`, `↑` | カーソル上移動 |
| `Ctrl+N`, `↓` | カーソル下移動 |
| `Ctrl+A`, `Ctrl+B`, `←` | 左ペイン移動 |
| `Ctrl+E`, `Ctrl+F`, `→` | 右ペイン移動 |
| `TAB` | ペイン切り替え (循環) |
| `Enter` | ファイル開く/ディレクトリ移動 |
| `Space` | ファイル選択 (マーク) |

**注意**: `..` を選択してEnterキーを押すと親ディレクトリに移動できます。

### ファイル操作

| キー | 動作 |
|------|------|
| `D` | ファイル削除 (確認ダイアログ) |
| `M` | ファイル移動 (確認ダイアログ) |
| `C` | ファイルコピー (確認ダイアログ) |
| `R` | ファイルリネーム (編集モード) |
| `Meta+N` | 新規ディレクトリ作成 (未実装) |

### ナビゲーション

| キー | 動作 |
|------|------|
| `Meta+G` | パス移動 (TAB補完付き) |
| `Ctrl+U` | 親ディレクトリ移動 |
| `Ctrl+H` | ホームディレクトリ移動 |

### 検索・ソート

| キー | 動作 |
|------|------|
| `Ctrl+S` | 下方向インクリメンタルサーチ |
| `Ctrl+R` | 上方向インクリメンタルサーチ |
| `Meta+1` | 名前ソート |
| `Meta+2` | 拡張子ソート |
| `Meta+3` | サイズソート |
| `Meta+4` | 日付ソート |

### システム

| キー | 動作 |
|------|------|
| `Ctrl+G` | コマンドキャンセル |
| `ESC ESC` | アプリケーション終了 |
| `Ctrl+?` | ヘルプ表示 |

## 編集モード (リネーム・パス入力時)

| キー | 動作 |
|------|------|
| `Ctrl+F` | カーソル右移動 |
| `Ctrl+B` | カーソル左移動 |
| `Ctrl+A` | 行頭移動 |
| `Ctrl+E` | 行末移動 |
| `Meta+F` | 単語後移動 |
| `Meta+B` | 単語前移動 |
| `Ctrl+D` | 文字削除 |
| `Ctrl+K` | 行末まで削除 |

### 🎨 表示機能

### ファイルタイプ別色分け

- **ディレクトリ**: 青 (太字)
- **実行ファイル**: 緑 (太字) 
- **シンボリックリンク**: 水色 (太字)
- **壊れたリンク**: 緑背景 (赤文字)
- **音楽ファイル**: マゼンタ
- **画像ファイル**: 黄色
- **動画ファイル**: 赤
- **プログラムファイル**: 緑
- **設定ファイル**: 水色
- **アーカイブファイル**: 赤 (太字)

### カラム表示

```
[状態] ファイル名     拡張子/リンク先  サイズ   更新日時        権限
[ ]    document      pdf         850KB    2026-03-28 15:30  -rw-r--r--
[M]    vacation      jpg         1.8MB    2026-03-27 10:15  -rw-r--r--
[>]    config@       →/etc/cfg   <LINK>   2026-03-26 14:20  lrwxrwxrwx
[ ]    broken@!      →missing   <BROKEN> 2026-03-25 09:00  lrwxrwxrwx
```

- `[ ]`: 通常ファイル
- `[M]`: マーク済みファイル  
- `[>]`: カーソル位置
- `[*]`: マーク済み+カーソル位置
- `@`: シンボリックリンクマーカー
- `@!`: 壊れたシンボリックリンク
- `→`: リンク先表示

## 設定

設定ファイルは `~/.config/2pane-filer/` ディレクトリに保存されます：

- `config.ini`: 基本設定
- `colors.conf`: 色設定  
- `keybinds.conf`: キーバインド設定

### 設定例 (config.ini)

```ini
[display]
use_color = true
show_hidden = false
cursor_highlight = full_line

[behavior]
confirm_delete = true
double_esc_exit = true
default_sort = name

[external]
default_editor = vi
default_shell = /bin/bash
```
## 🎆 v0.2.1-beta の新機能

### 🗺️ In-Windowダイアログシステム
- **長いパス対応**: ファイルパスが長い場合に画面中央に詳細ウィンドウを表示
- **直観的UI**: 転送元と転送先を看直的に表示
- **汎用設計**: 今後も様々な場面で活用可能

```
┌───────────────────────────────────┐
│        ファイルコピーの確認        │
│                                  │
│  転送元: /very/long/path/to/file  │
│       |                         │
│       |                         │
│  転送先: /another/long/path      │
│                                  │
│        [*はい] [ いいえ]        │
└───────────────────────────────────┘
```
## 🎯 v0.2.0-beta の新機能

### 🔄 ファイル操作機能
- **コピー(C)**: アクティブペイン→非アクティブペインへのファイルコピー
- **削除(D)**: ファイル/ディレクトリの削除（確認ダイアログ付き）
- **移動(M)**: ファイル/ディレクトリの移動（確認ダイアログ付き）
- **リネーム(R)**: インライン編集でのファイル名変更

### 📊 進捗表示システム
- **Mode行表示**: 操作の進捗状況をリアルタイム表示
- **確認ダイアログ**: 安全な操作のための確認システム
- **バックグラウンド処理**: UIをブロックしない非同期操作

### 🌏 日本語対応改善
- **全角文字サポート**: Unicode East Asian Width規格対応
- **正確な表示幅**: 日本語フォルダ名の正しい表示
- **動的レイアウト**: 端末幅に応じた最適なカラムサイズ

### 🏠 使いやすさ向上
- **ホームディレクトリ起動**: 起動時のデフォルトをホームディレクトリに変更
- **改良されたカラム表示**: `<DIR>`表示の位置修正
- **安定した表示**: 表示崩れの問題を解決

## 🔧 開発状況（v0.2.1-beta）

### ✅ 実装済み機能
- [x] **プロジェクト構造**: 完全なモジュール分離設計
- [x] **基本TUI画面**: 2ペイン表示、ステータスバー、コマンドライン
- [x] **カーソル移動**: EmacsスタイルとカーソルキーUI対応
- [x] **ディレクトリ移動**: Enterキーでのディレクトリ移動
- [x] **基本ファイル一覧**: ファイル・ディレクトリ表示、ソート機能
- [x] **シンボリックリンク対応**: 壊れたリンク検出、表示改善
- [x] **色分けシステム**: ls --color=auto互換の色分け
- [x] **ファイル操作**: コピー(C)、削除(D)、移動(M)、リネーム(R)
- [x] **進捗表示**: Mode行でのリアルタイム操作進捗表示
- [x] **確認ダイアログ**: 削除・移動・コピー時の安全確認
- [x] **日本語対応**: 全角文字の正確な表示幅計算
- [x] **ホームディレクトリ起動**: デフォルトでホームディレクトリから開始

### 🚧 次期実装予定
詳細は [TODO.md](TODO.md) を参照してください:
1. 画像ファイルビューア機能
2. 音楽ファイル再生機能  
3. バックグラウンドファイル操作
4. テキストエディタ機能

## 🤝 コントリビューション

コントリビューションを歓迎します！詳細な手順は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

### バグ報告・機能要求
- **Issues**: [GitHub Issues](https://github.com/FHGKSA/BOKU-MINIMAL-EMACS-Like-Filer-Project/issues)
- **Pull Request**: 歓迎します

### 開発者向けクイックスタート
```bash
# 開発モードでのセットアップ
git clone https://github.com/FHGKSA/BOKU-MINIMAL-EMACS-Like-Filer-Project.git
cd BOKU-MINIMAL-EMACS-Like-Filer-Project

# 動作テスト
python3 test_basic.py

# デバッグモード実行
python3 src/main.py --debug
```

## 📄 ライセンス

[MIT License](LICENSE) - 自由に使用、改変、再配布可能です。

## 🙏 謝辞

- **Midnight Commander**: ファイラーの基本設計の参考
- **GNU Emacs**: キーバインド設計の参考
- **Windows "あふ"**: UI/UX設計の参考

## 📞 サポート

- **バグ報告**: [GitHub Issues](https://github.com/FHGKSA/BOKU-MINIMAL-EMACS-Like-Filer-Project/issues)
- **質問・議論**: [GitHub Discussions](https://github.com/FHGKSA/BOKU-MINIMAL-EMACS-Like-Filer-Project/discussions) (準備中)

---

**重要**: これはBeta版です。本格的な使用前に十分なテストを行ってください。