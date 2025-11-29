# 🤖 Git Gemini Clicker

[![Python Version](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://www.python.org/)
[![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/shouni/git-gemini-clicker)](https://github.com/shouni/git-gemini-clicker/tags)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 概要 (About) - 研究開発・拡張用 AIコードレビューCLI

**Git Gemini Clicker** は、**Google Gemini の強力なAI**を活用して、ローカルGitリポジトリの差分（diff）に基づいたコードレビューを自動化する、Python製のコマンドラインツールです。

**`click` フレームワーク** と **`google-genai` SDK** を採用しており、AIロジックのカスタマイズや、Pythonエコシステムとの連携が容易な設計になっています。

-----

## 🔗 コアライブラリとの関係と機能比較

このプロジェクトは、Go言語で開発された**コアライブラリ** `Gemini Reviewer Core`の機能、特に「Git操作」「AI通信」「プロンプト管理」のロジックを参考にしつつ、**Pythonの特性を活かしたCLI**として再実装されています。

> [\!NOTE]
> **Go言語版との違いについて**
>
> このプロジェクトは **Python製のCLIツール** です。
> 高速な動作とシングルバイナリによる配布を重視する「実務利用」の場合は、Go言語版の **[Gemini Reviewer Core](https://github.com/shouni/gemini-reviewer-core)** を推奨します。

### 📊 機能・設計比較表

| 要素 | Git Gemini Clicker (Python CLI) | Gemini Reviewer Core (Go Library) |
| :--- | :--- | :--- |
| **言語 / 用途** | **Python / CLIツール** (プロトタイピング、R\&D) | **Go / コアライブラリ** (堅牢な基盤、Web/CLI共通) |
| **Git操作** | **ローカル `git` コマンド** (subprocess)。Go版と異なり、**ディレクトリ削除ではなく `fetch` + `reset --hard` で作業状態をクリーン**にします。 | **`go-git`** (Goネイティブ実装、`pkg/adapters`層)。クリーンアップは通常、一時ディレクトリの削除。 |
| **AI通信** | **`google-genai` SDK** (Python SDK) | **Go SDK/HTTPクライアント** (`pkg/adapters`層) |
| **カスタマイズ性** | LLMパラメータをCLIで詳細制御。**Pythonエコシステム**での拡張が容易。 | **依存性逆転 (DIP)** に基づく高い拡張性。 |
| **出力/公開** | **標準出力 (`stdout`)** へのテキスト出力のみ。 | **`Publisher` インターフェース** (`pkg/publisher`層)。HTML変換、GCS/S3への保存に対応。 |
| **配布/パフォーマンス** | `pip` または `venv` による配布。実行速度はGo版に劣る。 | **シングルバイナリ**配布。高速な実行速度。 |

-----

### 💡 主な特徴

* **🐍 Pythonネイティブ**: データサイエンスやMLエンジニアにとって馴染み深い Python で記述されており、ロジックの拡張や改変が容易です。
* **🧪 実験とR\&Dに最適**: **`--temperature`** や **`--max-tokens`** などのLLMパラメータをCLIから詳細に制御でき、プロンプトエンジニアリングの実験場として機能します。
* **🤖 AI駆動のレビュー**: **`detail`**（詳細レビュー）と **`release`**（リリースレビュー）の2つのサブコマンドで、目的に応じたフィードバックを取得できます。
* **🛡️ 堅牢な実装**: **指数バックオフ付きのリトライ・遅延メカニズム**を実装し、APIのレートリミットや一時的なエラーに強い設計です。
* **Gitリポジトリ対応**: SSH認証（`--ssh-key-path`）をサポートし、プライベートリポジトリのクローンとレビューが可能です。レビュー後には、**ローカルリポジトリを自動でベースブランチの最新状態にリセット**（クリーンアップ）し、常にクリーンな状態で次の操作に備えます。

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
````

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
| `--repo-url` | `-u` | **(必須)** レビュー対象の Git リポジトリの SSH URL | - |
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
    --temperature 0.2 \
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
