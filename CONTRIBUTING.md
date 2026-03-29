# Contributing to BOKU MINIMAL EMACS-Like Filer Project

このプロジェクトへの貢献に興味をお持ちいただき、ありがとうございます！

## 開発方針

このプロジェクトは以下の原則に基づいて開発されています：

- **軽量性**: 高速起動と低メモリ使用を重視
- **Emacsスタイル**: 一貫したEmacsライクなキーバインド
- **安定性**: 堅牢で予測可能な動作
- **日本語対応**: UTF-8/Shift_JIS混在環境での安定動作
- **byobu互換**: tmux/screen環境での競合回避

## 開発環境

### 必要条件
- Python 3.7以上
- Linux（Ubuntu系推奨）
- cursesライブラリ対応ターミナル
- Git

### セットアップ
```bash
# リポジトリのクローン
git clone https://github.com/FHGKSA/BOKU-MINIMAL-EMACS-Like-Filer-Project.git
cd BOKU-MINIMAL-EMACS-Like-Filer-Project

# 実行権限の付与
chmod +x src/main.py
chmod +x run.sh

# 動作テスト
python3 test_basic.py

# 実行確認
./run.sh
```

## コントリビューション方法

### 1. Issue報告
バグ報告や機能要求は以下の形式でお願いします：

#### バグ報告
```markdown
**環境**
- OS: 
- Python版: 
- ターミナル: 

**問題の内容**
- 

**再現手順**
1. 
2. 
3. 

**期待される動作**
- 

**実際の動作**
- 
```

#### 機能要求
```markdown
**機能の概要**
- 

**使用場面**
- 

**実装案（あれば）**
- 
```

### 2. プルリクエスト

1. **フォークとクローン**
   ```bash
   # あなたのアカウントでフォーク後
   git clone https://github.com/your-username/BOKU-MINIMAL-EMACS-Like-Filer-Project.git
   ```

2. **ブランチ作成**
   ```bash
   git checkout -b feature/your-feature-name
   # または
   git checkout -b bugfix/issue-number
   ```

3. **開発とテスト**
   ```bash
   # コード変更
   vim src/your_file.py
   
   # テスト実行
   python3 test_basic.py
   
   # 動作確認
   ./run.sh
   ```

4. **コミットとプッシュ**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   git push origin feature/your-feature-name
   ```

5. **プルリクエスト作成**
   - 明確なタイトルと説明を記載
   - 関連するIssue番号を記載
   - テスト結果を報告

### 3. コミットメッセージ規約

```
type(scope): description

body (optional)

footer (optional)
```

**タイプ**:
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `style`: フォーマット
- `refactor`: リファクタリング
- `test`: テスト
- `chore`: その他

**例**:
```
feat(ui): add symlink display with broken link detection

- Add "@" marker for symlinks and "@!" for broken links
- Implement link target path display
- Add color coding for different link states

Closes #123
```

## コーディング規約

### Python規約
- PEP 8 準拠
- 型ヒント推奨（Python 3.7+）
- docstring必須（Google形式）
- 関数・クラス単位での適切な分割

### 命名規約
```python
# クラス: PascalCase
class FileManager:

# 関数・変数: snake_case  
def get_file_list():
    file_count = 10

# 定数: UPPER_SNAKE_CASE
MAX_FILE_SIZE = 1024 * 1024
```

### ファイル構成
```
src/
├── main.py          # エントリーポイント
├── filer.py         # メインファイラークラス
├── ui.py            # UIコンポーネント
├── colors.py        # 色管理
├── config.py        # 設定管理
└── file_ops.py      # ファイル操作
```

## テスト

### 基本テスト
```bash
# 全体動作テスト
python3 test_basic.py

# モジュール単位テスト
cd src && python3 -c "import filer, ui, colors, config, file_ops"
```

### 手動テスト項目
- [ ] ファイル一覧表示
- [ ] カーソル移動（↑↓←→, Ctrl+P/N/A/E）
- [ ] ディレクトリ移動（Enter）
- [ ] ペイン切り替え（TAB）
- [ ] シンボリックリンク表示
- [ ] 色分け動作
- [ ] 異なるターミナルサイズでの動作

## ヘルプ・サポート

- **バグ報告**: GitHub Issues
- **機能要求**: GitHub Issues
- **質問**: GitHub Discussions（準備中）

## ライセンス

このプロジェクトへの貢献は MIT License の下で公開されます。

## 謝辞

すべてのコントリビューターに感謝いたします！