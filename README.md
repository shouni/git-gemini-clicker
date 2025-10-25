# 🤖 Git Gemini Clicker

[![Python Version](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://www.python.org/)
[![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/shouni/git-gemini-clicker)](https://github.com/shouni/git-gemini-clicker/tags)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 概要 (About) - AIコードレビューCLI

**Git Gemini Clicker** は、Go言語版の思想を受け継ぎ、**Google Gemini の強力なAI**を活用して、**ローカルGitリポジトリの差分（diff）に基づいたコードレビューを自動化**するコマンドラインツールです。インストール後の実行コマンドは **`ggrc`** です。

**堅牢なリトライ・遅延メカニズムを備えたAIクライアント**と、**`click` フレームワーク**で構築されており、APIの安定性に依存するAI処理の信頼性を高めています。レビュー結果を**標準出力**に出力することに特化しており、CI/CDパイプラインやカスタムスクリプトへの組み込みが容易です。

### 💡 主な特徴

* **AI駆動のレビュー**: **`detail`**（詳細レビュー）と **`release`**（リリースレビュー）の2つの**サブコマンド**で、目的に応じたフィードバックを取得。
* **最高の堅牢性**: **指数バックオフ付きのリトライ・遅延メカニズム**を実装し、レートリミットやサーバーエラーに耐性を持たせることで、**Action Perfect Get On Go**の堅牢な設計思想を完全に継承しています。
* **LLMパラメータの完全制御**: **`--temperature`** と **`--max-tokens`** のオプションが追加され、LLMの応答のランダム性や最大出力長をユーザーが詳細に制御できます。
* **堅牢なオプション構造**: すべての必須項目を**オプション**（`--` または `-`）で渡す設計。`click` の採用により、引数検証の堅牢性が向上しました。
* **Gitリポジトリ対応**: SSH認証（`--ssh-key-path`）をサポートし、プライベートリポジトリのクローンとレビューが可能です。
* **プロンプトの外部管理**: レビューロジックとプロンプトテンプレート（`.md` ファイル）を分離し、カスタマイズの容易性を確保。

-----

## ✨ 技術スタック (Technology Stack)

| 要素 | 技術 / ライブラリ | 役割 |
| :--- | :--- | :--- |
| **言語** | **Python 3.9+** | ツールの開発言語。 |
| **CLI フレームワーク** | **Click** | 関数をサブコマンド形式のCLIに堅牢に変換。 |
| **AI モデル** | **google-genai SDK (Gemini API)** | **堅牢なリトライロジックと、`Content`/`Part`による構造化された入力**で、コード差分を分析し、レビューコメントを生成。 |
| **Git 操作** | **Git コマンド (subprocess)** | ローカルGitリポジトリ操作（クローン、ブランチ切り替え、**3点比較による差分取得**）を直接実行。Go版の堅牢性を継承。 |
| **パッケージ管理** | **pyproject.toml (setuptools)** | ビルドシステムと依存関係の標準的な定義。 |

-----

## 🛠️ 事前準備と環境設定

### 1\. Python と依存関係のインストール

Python 3.9以上が必要です。**`pyproject.toml`** を使用して、編集可能モード（開発モード）でインストールすることを推奨します。

```bash
# 仮想環境を作成・有効化
python3 -m venv .venv
source .venv/bin/activate

# 依存ライブラリをインストール（pyproject.tomlを読み込む）
# -e . : 編集可能モードでインストールし、CLIコマンド ggrc を有効化します
pip install -e .
````

### 2\. 環境変数の設定 (必須)

Gemini API を利用するために、API キーを環境変数に設定します。

#### macOS / Linux (bash/zsh)

```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

-----

## ⚙️ コマンドとオプション

本ツールは、すべての必須項目を**オプション（`--`またはショートカット `-`）で受け付けます。インストール後、`ggrc`** コマンドで起動できます。

### 🤖 レビューコマンドと目的

| コマンド | プロンプトファイル | 目的とレビュー観点 |
| :--- | :--- | :--- |
| **`detail`** | `prompt_detail.md` | **詳細な技術レビュー**。コード品質、可読性、ベストプラクティスからの逸脱に焦点を当てる。 |
| **`release`** | `prompt_release.md` | **本番リリース可否の判定**。致命的なバグ、セキュリティ脆弱性など、リリースをブロックする問題に限定して指摘する。 |

### 🛠 グローバルオプションとコマンドオプション

| タイプ | ロングオプション | ショートカット | 説明 | 必須 | デフォルト値 (ソース) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **オプション** | `--git-clone-url**` | **`-u`** | **クローン対象のGitリポジトリURL（SSH推奨）** | ✅ | **なし** |
| **オプション** | `--feature-branch**` | **`-f`** | **レビュー対象のブランチ、タグ、またはコミット**。 | ✅ | **なし** |
| **オプション** | `--base-branch` | **`-b`** | 差分比較の**基準**となるブランチ、タグ、またはコミット。 | ❌ | `main` (config.py) |
| **オプション** | `--temperature` | **なし** | LLMの応答のランダム性 (0.0 - 1.0)。 | ❌ | `0.2` (config.py) |
| **オプション** | `--max-tokens` | **なし** | LLMの最大出力トークン数。 | ❌ | **`20480`** (config.py) |
| **グローバル** | `--ssh-key-path**` | **`-k`** | SSH認証のための秘密鍵パス。**（デフォルトは`~/.ssh/id_rsa`）** | ❌ | `~/.ssh/id_rsa` (config.py) |
| **グローバル** | `--model` | **`-m`** | 使用する Gemini モデル名。 | ❌ | `gemini-2.5-flash` (config.py) |
| **グローバル** | `--skip-host-key-check` | **`-s`** | SSHホストキーのチェックをスキップします。 | ❌ | `False` |

-----

## 🚀 使い方 (Usage) と実行例

インストール後、新しいコマンド名 **`ggrc`** を使用します。

### 1\. 詳細レビュー (`detail`)

必須オプションと新しいLLMパラメータを渡して、詳細レビューを行います。

```bash
# LLMパラメータを指定した実行例
ggrc \
    detail \
    -u "ssh://git@github.com/your/repo.git" \
    -f "feature/new-feature" \
    --temperature 0.5 \
    --max-tokens 8192 # 一時的にデフォルト値(20480)を上書き
```

### 2\. リリースレビュー (`release`)

ロングオプションとショートカットを混ぜて使用し、特定のコミットでリリース判定モードを実行します。

```bash
# ロングオプションとショートカットを組み合わせた実行例
ggrc \
    --model "gemini-2.5-pro" \
    release \
    -u "ssh://git@github.com/your/repo.git" \
    -f "4a5b6c7d8e9f" \
    --base-branch "main"
```

### 3\. ヘルプの表示

```bash
ggrc --help
ggrc detail --help
```

-----

### 📜 ライセンス (License)

このプロジェクトは [MIT License](https://opensource.org/licenses/MIT) の下で公開されています。
