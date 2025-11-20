# 🤖 Git Gemini Clicker

[![Python Version](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://www.python.org/)
[![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/shouni/git-gemini-clicker)](https://github.com/shouni/git-gemini-clicker/tags)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 概要 (About) - 研究開発・拡張用 AIコードレビューCLI

**Git Gemini Clicker** は、**Google Gemini の強力なAI**を活用して、ローカルGitリポジトリの差分（diff）に基づいたコードレビューを自動化する、Python製のコマンドラインツールです。

**`click` フレームワーク** と **`google-genai` SDK** を採用しており、AIロジックのカスタマイズや、Pythonエコシステムとの連携が容易な設計になっています。

> [\!NOTE]
> **Go言語版との違いについて**
>
> このプロジェクトは **Python製のCLIツール** です。
> 高速な動作とシングルバイナリによる配布を重視する「実務利用」の場合は、Go言語版の **[git-gemini-reviewer-go](https://github.com/shouni/git-gemini-reviewer-go)** を推奨します。
>
> **本ツール (`ggrc`) は、以下のようなケースに最適です。**
>
>   * **Python環境** (venv/pip) が既に整備されているプロジェクトへの導入
>   * **最新のAIモデルやパラメータ**を素早く試したい場合（プロトタイピング）
>   * コンパイル不要で、ロジックを動的に書き換えながら試行錯誤したい場合

### 💡 主な特徴

  * **🐍 Pythonネイティブ**: データサイエンスやMLエンジニアにとって馴染み深い Python で記述されており、ロジックの拡張や改変が容易です。
  * **🧪 実験とR\&Dに最適**: **`--temperature`** や **`--max-tokens`** などのLLMパラメータをCLIから詳細に制御でき、プロンプトエンジニアリングの実験場として機能します。
  * **🤖 AI駆動のレビュー**: **`detail`**（詳細レビュー）と **`release`**（リリースレビュー）の2つのサブコマンドで、目的に応じたフィードバックを取得できます。
  * **🛡️ 堅牢な実装**: **指数バックオフ付きのリトライ・遅延メカニズム**を実装し、APIのレートリミットや一時的なエラーに強い設計です。
  * **Gitリポジトリ対応**: SSH認証（`--ssh-key-path`）をサポートし、プライベートリポジトリのクローンとレビューが可能です。

-----

## ✨ 技術スタック (Technology Stack)

| 要素 | 技術 / ライブラリ | 役割 |
| :--- | :--- | :--- |
| **言語** | **Python 3.9+** | 開発言語。豊富なAIライブラリとの連携が可能。 |
| **CLI フレームワーク** | **Click** | 記述量が少なく、堅牢で直感的なCLIを作成するためのフレームワーク。 |
| **AI モデル** | **google-genai SDK** | Gemini APIへのアクセス。Python SDKならではの最新機能への追従性が強み。 |
| **Git 操作** | **Git コマンド (subprocess)** | ローカルの `git` コマンドを直接呼び出し、3点比較 (`A...B`) による正確な差分を取得。 |
| **パッケージ管理** | **pyproject.toml** | 現代的なPythonパッケージング標準。 |

-----

## 🛠️ インストールと環境設定

本ツールは、Pythonの仮想環境（venv）での利用を推奨します。

### 1\. インストール

ソースコードをクローンし、編集可能モード（`-e`）でインストールすることで、コードを修正しながら即座に実行結果を確認できます。

```bash
# 1. 仮想環境を作成・有効化
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 依存ライブラリをインストール
# -e . : 編集可能モードでインストールし、CLIコマンド 'ggrc' を有効化します
pip install -e .
```

### 2\. 環境変数の設定 (必須)

Gemini API を利用するために、API キーを環境変数に設定します。

```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

-----

## ⚙️ コマンドとオプション

インストール後、**`ggrc`** コマンドで起動できます。

### 🤖 レビューコマンド

| コマンド | 目的とレビュー観点 |
| :--- | :--- |
| **`detail`** | **詳細な技術レビュー**。コード品質、可読性、Pythonicな書き方やベストプラクティスからの逸脱に焦点を当てます。 |
| **`release`** | **本番リリース可否の判定**。致命的なバグ、セキュリティ脆弱性など、リリースをブロックすべき問題のみを指摘します。 |

### 🛠 主なオプション

| オプション | ショートカット | 説明 | デフォルト値 |
| :--- | :--- | :--- | :--- |
| `--git-clone-url` | `-u` | **(必須)** クローン対象のGitリポジトリURL | - |
| `--feature-branch` | `-f` | **(必須)** レビュー対象のブランチ/コミット | - |
| `--base-branch` | `-b` | 比較基準となるブランチ | `main` |
| `--temperature` | | LLMの応答のランダム性 (0.0 - 1.0) | `0.2` |
| `--max-tokens` | | LLMの最大出力トークン数 | `20480` |
| `--model` | `-m` | 使用する Gemini モデル名 | `gemini-2.5-flash` |
| `--ssh-key-path` | `-k` | SSH認証のための秘密鍵パス | `~/.ssh/id_rsa` |

-----

## 🚀 実行例 (Usage Examples)

### 1\. パラメータを調整して詳細レビュー (`detail`)

プロンプトの挙動実験として、Temperature（創造性）を上げて実行する例です。

```bash
ggrc detail \
    -u "ssh://git@github.com/your/repo.git" \
    -f "feature/new-algorithm" \
    --temperature 0.7 \
    --max-tokens 8192
```

### 2\. モデルを指定してリリース判定 (`release`)

より高性能なモデル (`gemini-2.5-pro`) を指定して、厳密なチェックを行う例です。

```bash
ggrc release \
    --model "gemini-2.5-pro" \
    -u "ssh://git@github.com/your/repo.git" \
    -f "release/v1.0.0" \
    --base-branch "develop"
```

### 3\. ヘルプの表示

```bash
ggrc --help
ggrc detail --help
```

-----

### 📜 ライセンス (License)

このプロジェクトは [MIT License](https://opensource.org/licenses/MIT) の下で公開されています。
