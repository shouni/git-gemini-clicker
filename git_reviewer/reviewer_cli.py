import click
import sys
import tempfile
from pathlib import Path
from typing import Optional
import logging

# --- コアロジックをインポート ---
from git_reviewer.core import ReviewCore

# CLIとしてのログ設定
# INFOレベルでログを出力
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- グローバル設定 ---
@click.group()
@click.option('--model', default="gemini-2.5-flash", help='使用するGeminiモデル名。')
@click.option('--ssh-key-path', default="~/.ssh/id_rsa", help='SSHプライベートキーへのパス。')
@click.option('--skip-host-key-check', is_flag=True, help='SSHホストキーのチェックをスキップします。')
@click.pass_context
def cli(ctx, model, ssh_key_path, skip_host_key_check):
    """
    Python版 Git Gemini Reviewer CLI
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


def _get_default_local_path(command: str) -> str:
    """一時ディレクトリ内のデフォルトパスを生成"""
    # ユーザーのGoツール名に合わせてディレクトリ名を調整
    base_dir = Path(tempfile.gettempdir()) / "prototypus-ai-doc-go-repos"
    local_repo_name = f"tmp-{command}"
    return str(base_dir / local_repo_name)


def _print_info(command: str, **kwargs):
    """引数情報を表示するダミー関数 (デバッグ用)"""
    logger.info(f"\n--- {command.upper()} モード引数確認 (DEBUG) ---")
    for key, value in kwargs.items():
        logger.info(f"{key}: {value}")
    logger.info("------------------------------------------")


def _run_review_command(ctx: dict, feature_branch: str, git_clone_url: str,
                        base_branch: str, local_path: Optional[str], mode: str) -> None:
    """
    Gitレビューのコアロジックを実行するヘルパーメソッド。
    ctx は click.group() で設定されたグローバルオプションの辞書 (ctx.obj) です。
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
        core = ReviewCore(
            repo_url=git_clone_url,
            local_path=local_path,
            # ctx は辞書なので、直接キーでアクセス（AIの指摘が誤解している部分）
            ssh_key_path=ctx['SSH_KEY_PATH'],
            model_name=ctx['MODEL'],
            skip_host_key_check=ctx['SKIP_HOST_KEY_CHECK']
        )
        success, result_message = core.run_review(base_branch, feature_branch, mode)

        if success:
            if result_message:
                print(f"\n--- AIレビュー結果 ---\n{result_message}")
            else:
                print("レビュー処理が完了しました。（差分なしなど）")
        else:
            print(f"\n--- AIレビュー失敗 ---\n{result_message}", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        logger.error(f"致命的なエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)


# --- DETAIL コマンド ---
@cli.command()
@click.argument('git_clone_url', type=str)
@click.argument('feature_branch', type=str)
@click.option('--base-branch', default="main", help='比較対象のベースブランチ。')
@click.option('--local-path', default=None, help='リポジトリをクローンするローカルパス。')
@click.pass_context
def detail(ctx, git_clone_url, feature_branch, base_branch, local_path):
    """
    [詳細レビュー] GIT_CLONE_URLとFEATURE_BRANCHを指定し、コード品質に焦点を当てたAIレビューを実行します。
    """
    # 修正済み: click.Context ではなく、辞書である ctx.obj を渡す
    _run_review_command(ctx.obj, feature_branch, git_clone_url, base_branch, local_path, "detail")


# --- RELEASE コマンド ---
@cli.command()
@click.argument('git_clone_url', type=str)
@click.argument('feature_branch', type=str)
@click.option('--base-branch', default="main", help='比較対象のベースブランチ。')
@click.option('--local-path', default=None, help='リポジトリをクローンするローカルパス。')
@click.pass_context
def release(ctx, git_clone_url, feature_branch, base_branch, local_path):
    """
    [リリースレビュー] GIT_CLONE_URLとFEATURE_BRANCHを指定し、本番リリース可否に焦点を当てたAIレビューを実行します。
    """
    # 修正済み: click.Context ではなく、辞書である ctx.obj を渡す
    _run_review_command(ctx.obj, feature_branch, git_clone_url, base_branch, local_path, "release")


if __name__ == '__main__':
    # cli() を呼び出し、空の辞書をobjとして渡します (click の標準的なパターン)
    cli(obj={})