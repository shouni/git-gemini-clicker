# 🤖 Git Gemini Reviewer Fire

[![Python Version](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://www.python.org/)
[![CLI Framework](https://img.shields.io/badge/CLI-python--fire-red?logo=pypi)](https://github.com/google/python-fire)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 概要 (About) - AIコードレビューCLI

**`Git Gemini Reviewer Fire`** は、Go言語版の思想を受け継ぎ、**Google Gemini の強力なAI**を活用して、**ローカルGitリポジトリの差分（diff）に基づいたコードレビューを自動化**するコマンドラインツールです。

Pythonの`fire`フレームワークを使用し、レビュー結果を**標準出力**に出力することに特化しています。これにより、CI/CDパイプラインやカスタムスクリプトへの組み込みが容易です。

### 💡 主な特徴

* **AI駆動のレビュー**: **`detail`**（詳細レビュー）と`release`（リリースレビュー）の2つのコマンドで、目的に応じたフィードバックを取得。
* **Go版の引数構造**: レビュー対象ブランチの**明示的な指定**を要求するGo版の必須引数構造を再現。
* **プロンプトの外部管理**: レビューロジックとプロンプトテンプレート（`.md` ファイル）を分離し、カスタマイズの容易性を確保。

-----

## ✨ 技術スタック (Technology Stack)

| 要素 | 技術 / ライブラリ | 役割 |
| :--- | :--- | :--- |
| **言語** | **Python 3.8+** | ツールの開発言語。 |
| **CLI フレームワーク** | **Python Fire** | 関数やクラスを自動でCLIコマンドに変換。 |
| **AI モデル** | **google-genai SDK (Gemini API)** | コード差分を分析し、レビューコメントを生成。 |
| **パッケージ管理** | **pyproject.toml** | 設定、依存関係、プロンプトデータファイルの同梱設定を一元管理。 |

-----

## 🛠️ 事前準備と環境設定

### 1\. Python と依存関係のインストール

Python 3.8以上が必要です。仮想環境での作業を推奨します。

```bash
# 仮想環境を作成・有効化
python3 -m venv .venv
source .venv/bin/activate

# 依存ライブラリをインストール
pip install python-fire google-genai
```

### 2\. 環境変数の設定 (必須)

Gemini API を利用するために、API キーを環境変数に設定します。

#### macOS / Linux (bash/zsh)

```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

-----

## ⚙️ コマンドと引数

本ツールは、Go版と同様に**レビュー対象のフィーチャーブランチ（`--feature_branch`）の指定を必須**とします。

### 🤖 レビューコマンドと目的

| コマンド | プロンプトファイル | 目的とレビュー観点 |
| :--- | :--- | :--- |
| **`detail`** | `prompt_detail.md` | **詳細な技術レビュー**。コード品質、可読性、ベストプラクティスからの逸脱に焦点を当てる。 |
| **`release`** | `prompt_release.md` | **本番リリース可否の判定**。致命的なバグ、セキュリティ脆弱性など、リリースをブロックする問題に限定して指摘する。 |

### 🛠 必須引数とオプション引数 (Flags)

| 引数 | 説明 | 必須 | デフォルト値 |
| :--- | :--- | :--- | :--- |
| `--feature_branch` | **レビュー対象のフィーチャーブランチ**、タグ、またはコミット。 | ✅ | **なし** |
| `--base_branch` | 差分比較の**基準**となるブランチ、タグ、またはコミット。 | ❌ | `main` |
| `--model` | 使用する Gemini モデル名。 | ❌ | `gemini-2.5-flash` |
| `-m`, `--mode` | レビューモード（Go版の互換性のため残存しますが、コマンド名でレビュータイプは決定されます）。 | ❌ | コマンド依存 |

-----

## 🚀 使い方 (Usage) と実行例

### 1\. 詳細レビュー (`detail`)

`feature/login-fix` ブランチと `main` ブランチの差分について、詳細レビューを行います。

```bash
# --base_branch=main はデフォルトのため省略可能
python reviewer_cli.py detail --feature_branch "feature/login-fix"
```

基準ブランチを `develop` に変更する場合:

```bash
python reviewer_cli.py detail --feature_branch "feature/login-fix" --base_branch "develop"
```

### 2\. リリースレビュー (`release`)

`release/v1.1.0` ブランチを、`main` と比較し、`gemini-2.5-pro` モデルでリリース判定モードで実行します。

```bash
python reviewer_cli.py release \
    --feature_branch "release/v1.1.0" \
    --model "gemini-2.5-pro"
```

### 3\. ヘルプの表示

`python-fire` の機能により、詳細なヘルプが自動で表示されます。

```bash
python reviewer_cli.py -- --help
```

-----

### 📜 ライセンス (License)

このプロジェクトは [MIT License](https://opensource.org/licenses/MIT) の下で公開されています。
