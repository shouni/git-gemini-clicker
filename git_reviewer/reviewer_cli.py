import click
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import logging

# --- コアロジックをインポート ---
from .core import ReviewCore

# CLIとしてのログ設定
# INFOレベルでログを出力
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- グローバル設定 ---
@click.group()
@click.option('-m', '--model', default="gemini-2.5-flash", help='使用するGeminiモデル名。') # ショートカット -m
@click.option('-k', '--ssh-key-path', default="~/.ssh/id_rsa", help='SSHプライベートキーへのパス。') # ショートカット -k
@click.option('-s', '--skip-host-key-check', is_flag=True, help='SSHホストキーのチェックをスキップします。') # ショートカット -s
@click.pass_context
def cli(ctx, model, ssh_key_path, skip_host_key_check):
    """
    Python版 Git Gemini Clicker CLI
    詳細レビュー (detail) と リリースレビュー (release) のためのコマンドを提供します。
    """
    # 実行コンテキストに共通設定を格納
    ctx.ensure_object(dict)
    ctx.obj['MODEL'] = model
    ctx.obj['SSH_KEY_PATH'] = ssh_key_path
    ctx.obj['SKIP_HOST_KEY_CHECK'] = skip_host_key_check

    logger.info(f"--- CLI初期化完了 ---")
    logger.info(f"使用モデル: {model}")
    logger.info("----------------------")


# --- 共通オプションデコレータ ---
def common_options(f):
    """detailとreleaseコマンドで共通のオプションを定義するデコレータ"""
    # git-clone-url
    f = click.option('-u', '--git-clone-url', required=True, type=str, help='リポジトリのクローンURL。')(f)
    # feature-branch
    f = click.option('-f', '--feature-branch', required=True, type=str, help='レビュー対象のフィーチャーブランチ名。')(f)
    # base-branch
    f = click.option('-b', '--base-branch', default="main", help='比較対象のベースブランチ。')(f)
    # local-path
    f = click.option('--local-path', default=None, help='リポジトリをクローンするローカルパス。')(f)
    return f


def _get_default_local_path(command: str) -> str:
    """一時ディレクトリ内のデフォルトパスを生成"""
    base_dir = Path(tempfile.gettempdir()) / "git-gemini-clicker-repos"
    local_repo_name = f"tmp-{command}"
    return str(base_dir / local_repo_name)


def _print_info(command: str, **kwargs):
    """引数情報を表示するダミー関数 (デバッグ用)"""
    logger.info(f"\n--- {command.upper()} モード引数確認 (DEBUG) ---")
    for key, value in kwargs.items():
        logger.info(f"{key}: {value}")
    logger.info("------------------------------------------")


def _execute_review(ctx: dict, repo_url: str, local_path: str, base_branch: str, feature_branch: str, mode: str) -> Tuple[bool, str]:
    """
    ReviewCoreをインスタンス化し、レビューを実行する。
    成功/失敗と結果メッセージを返す。
    """
    core = ReviewCore(
        repo_url=repo_url,
        local_path=local_path,
        ssh_key_path=ctx['SSH_KEY_PATH'],
        model_name=ctx['MODEL'],
        skip_host_key_check=ctx['SKIP_HOST_KEY_CHECK']
    )
    return core.run_review(base_branch, feature_branch, mode)


def _handle_review_result(success: bool, result_message: str):
    """
    レビュー結果に基づいて標準出力への表示と終了コードの処理を行う。（責務分離）
    """
    if success:
        if result_message:
            print(f"\n--- AIレビュー結果 ---\n{result_message}")
        else:
            print("レビュー処理が完了しました。（差分なしなど）")
    else:
        print(f"\n--- AIレビュー失敗 ---\n{result_message}", file=sys.stderr)
        sys.exit(1)


def _run_review_command(ctx: dict, feature_branch: str, git_clone_url: str,
                        base_branch: str, local_path: Optional[str], mode: str) -> None:
    """
    Gitレビューのメインフローを調整するメソッド。（責務はフロー管理に集中）
    """
    if local_path is None:
        local_path = _get_default_local_path(mode)

    # ctx は辞書なので、直接キーでアクセス
    _print_info(
        mode,
        feature_branch=feature_branch,
        git_clone_url=git_clone_url,
        base_branch=base_branch,
        local_path=local_path,
        model_name=ctx['MODEL'],
        ssh_key_path=ctx['SSH_KEY_PATH']
    )

    try:
        # レビューを実行
        success, result_message = _execute_review(
            ctx=ctx,
            repo_url=git_clone_url,
            local_path=local_path,
            base_branch=base_branch,
            feature_branch=feature_branch,
            mode=mode
        )

        # 結果の出力と終了処理
        _handle_review_result(success, result_message)

    except Exception as e:
        logger.error(f"致命的なエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)


# --- DETAIL コマンド ---
@cli.command()
@common_options # 👈 共通オプションを適用
@click.pass_context
def detail(ctx, git_clone_url, feature_branch, base_branch, local_path):
    """
    [詳細レビュー] リポジトリURLとフィーチャーブランチを指定し、コード品質に焦点を当てたAIレビューを実行します。
    """
    _run_review_command(ctx.obj, feature_branch, git_clone_url, base_branch, local_path, "detail")


# --- RELEASE コマンド ---
@cli.command()
@common_options # 👈 共通オプションを適用
@click.pass_context
def release(ctx, git_clone_url, feature_branch, base_branch, local_path):
    """
    [リリースレビュー] リポジトリURLとフィーチャーブランチを指定し、本番リリース可否に焦点を当てたAIレビューを実行します。
    """
    _run_review_command(ctx.obj, feature_branch, git_clone_url, base_branch, local_path, "release")


if __name__ == '__main__':
    cli(obj={})
