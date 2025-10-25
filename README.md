# 🤖 Git Gemini Reviewer Fire

[![Python Version](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://www.python.org/)
[![CLI Framework](https://img.shields.io/badge/CLI-python--fire-red?logo=pypi)](https://github.com/google/python-fire)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 概要 (About) - AIコードレビューCLI

**`Git Gemini Reviewer Fire`** は、Go言語版の思想を受け継ぎ、**Google Gemini の強力なAI**を活用して、**ローカルGitリポジトリの差分（diff）に基づいたコードレビューを自動化**するコマンドラインツールです。

**Pythonの `click` フレームワーク**を使用し、レビュー結果を**標準出力**に出力することに特化しています。これにより、CI/CDパイプラインやカスタムスクリプトへの組み込みが容易です。

### 💡 主な特徴

* **AI駆動のレビュー**: **`detail`**（詳細レビュー）と **`release`**（リリースレビュー）の2つの**サブコマンド**で、目的に応じたフィードバックを取得。
* **堅牢な引数構造**: **`click`** に移行したことで、引数とオプションの検証が堅牢になり、混乱が解消されました。
* **Gitリポジトリ対応**: SSH認証（`--ssh-key-path`）をサポートし、プライベートリポジトリのクローンとレビューが可能です。
* **プロンプトの外部管理**: レビューロジックとプロンプトテンプレート（`.md` ファイル）を分離し、カスタマイズの容易性を確保。

-----

## ✨ 技術スタック (Technology Stack)

| 要素 | 技術 / ライブラリ | 役割 | (変更点) |
| :--- | :--- | :--- | :--- |
| **言語** | **Python 3.9+** | ツールの開発言語。 | (バージョン調整) |
| **CLI フレームワーク** | **Click** | 関数をサブコマンド形式のCLIに堅牢に変換。 | **(Python Fire から変更)** |
| **AI モデル** | **google-genai SDK (Gemini API)** | コード差分を分析し、レビューコメントを生成。 | (変更なし) |
| **Git 操作** | **GitPython** | リポジトリのクローン、ブランチ切り替え、差分取得を実行。 | (追記) |

-----

## 🛠️ 事前準備と環境設定

### 1\. Python と依存関係のインストール

Python 3.9以上が必要です。仮想環境での作業を強く推奨します。

```bash
# 仮想環境を作成・有効化
python3 -m venv .venv
source .venv/bin/activate

# 依存ライブラリをインストール
# CLIフレームワークが click に変更されました
pip install click google-genai google-api-core gitpython
```

### 2\. 環境変数の設定 (必須)

Gemini API を利用するために、API キーを環境変数に設定します。

#### macOS / Linux (bash/zsh)

```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

-----

## ⚙️ コマンドと引数

本ツールは、Go版と同様に**レビュー対象のGitリポジトリのURL**と**フィーチャーブランチ**を\*\*引数（Argument）\*\*として要求します。

### 🤖 レビューコマンドと目的

| コマンド | プロンプトファイル | 目的とレビュー観点 |
| :--- | :--- | :--- |
| **`detail`** | `prompt_detail.md` | **詳細な技術レビュー**。コード品質、可読性、ベストプラクティスからの逸脱に焦点を当てる。 |
| **`release`** | `prompt_release.md` | **本番リリース可否の判定**。致命的なバグ、セキュリティ脆弱性など、リリースをブロックする問題に限定して指摘する。 |

### 🛠 グローバルオプションとコマンド引数

| タイプ | 引数名 | 説明 | 必須 | デフォルト値 |
| :--- | :--- | :--- | :--- | :--- |
| **引数** | `GIT_CLONE_URL` | **クローン対象のGitリポジトリURL（SSH推奨）** | ✅ | **なし** |
| **引数** | `FEATURE_BRANCH` | **レビュー対象のブランチ、タグ、またはコミット**。 | ✅ | **なし** |
| **オプション** | `--base-branch` | 差分比較の**基準**となるブランチ、タグ、またはコミット。 | ❌ | `main` |
| **グローバル** | `--ssh-key-path` | SSH認証のための秘密鍵パス。 | ❌ | `~/.ssh/id_rsa` |
| **グローバル** | `--model` | 使用する Gemini モデル名。 | ❌ | `gemini-2.5-flash` |

-----

## 🚀 使い方 (Usage) と実行例

`click` への移行により、グローバルオプションはサブコマンドの**前に**、必須引数はサブコマンドの**直後に**記述する必要があります。

### 1\. 詳細レビュー (`detail`)

GitリポジトリURLとレビュー対象ブランチを引数として渡し、詳細レビューを行います。

```bash
# SSHキーパスはグローバルオプションとしてコマンド名の前に記述
python3 -m git_reviewer.reviewer_cli \
    --ssh-key-path "~/.ssh/id_rsa" \
    detail \
    "ssh://git@github.com/your/repo.git" \
    "feature/new-feature" \
    --base-branch "main"
```

### 2\. リリースレビュー (`release`)

`gemini-2.5-pro` モデルを指定し、特定のコミットでリリース判定モードを実行します。

```bash
python3 -m git_reviewer.reviewer_cli \
    --model "gemini-2.5-pro" \
    release \
    "ssh://git@github.com/your/repo.git" \
    "4a5b6c7d8e9f" \
    --base-branch "main"
```

### 3\. ヘルプの表示

`click` の機能により、詳細なヘルプが自動で表示されます。

```bash
python3 -m git_reviewer.reviewer_cli --help
python3 -m git_reviewer.reviewer_cli detail --help
```

-----

### 📜 ライセンス (License)

このプロジェクトは [MIT License](https://opensource.org/licenses/MIT) の下で公開されています。