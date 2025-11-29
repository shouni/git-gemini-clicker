import click
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import logging
# --- 追加 ---
from dataclasses import dataclass

from ..settings import Settings
from ..core import ReviewCore

# CLIとしてのログ設定
# INFOレベルでログを出力
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- データクラス定義 ---
@dataclass
class ReviewParams:
    """レビュー実行に必要なパラメータを格納するデータクラス"""
    feature_branch: str
    repo_url: str
    base_branch: str
    local_path: Optional[str]
    mode: str
    temperature: float
    max_tokens: int


# --- グローバルオプション定義 ---
def get_model_default():
    return Settings.get("DEFAULT_GEMINI_MODEL") or "gemini-2.5-flash"

def get_ssh_key_default():
    return Settings.get("DEFAULT_SSH_KEY_PATH") or "~/.ssh/id_rsa"

# --- グローバル設定 ---
@click.group()
@click.option(
    '-m', '--model',
    default=get_model_default(),
    help='使用するGeminiモデル名。'
)
@click.option(
    '-k', '--ssh-key-path',
    default=get_ssh_key_default(),
    help='SSHプライベートキーへのパス。'
)
@click.option('-s', '--skip-host-key-check', is_flag=True, help='SSHホストキーのチェックをスキップします。')
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
    # repo-url
    f = click.option('-u', '--repo-url', required=True, type=str, help='リポジトリのクローンURL。')(f)
    # feature-branch (必須なので変更なし)
    f = click.option('-f', '--feature-branch', required=True, type=str, help='レビュー対象のフィーチャーブランチ名。')(f)

    # base-branch
    base_branch_default = Settings.get("BASE_BRANCH") or "main"
    f = click.option('-b', '--base-branch', default=base_branch_default, help='比較対象のベースブランチ。')(f)

    # local-path (デフォルトはNoneなので変更なし)
    f = click.option('--local-path', default=None, help='リポジトリをクローンするローカルパス。')(f)

    # LLMパラメータ (temperature)
    f = click.option(
        '--temperature',
        type=float,
        default=float(Settings.get("DEFAULT_TEMPERATURE") or 0.2),
        help='LLMの応答のランダム性 (0.0 - 1.0)。'
    )(f)

    # LLMパラメータ (max-tokens)
    f = click.option(
        '--max-tokens',
        type=int,
        default=int(Settings.get("DEFAULT_MAX_OUTPUT_TOKENS") or 4096),
        help='LLMの最大出力トークン数。'
    )(f)

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


def _execute_review(ctx: dict, repo_url: str, local_path: str, base_branch: str, feature_branch: str, mode: str, temperature: float, max_tokens: int) -> Tuple[bool, str]:
    """
    ReviewCoreをインスタンス化し、レビューを実行する。
    成功/失敗と結果メッセージを返す。
    """
    # config.pyからリトライ設定を取得 (core.pyやai_client.pyに渡すために)
    max_retries = int(Settings.get("AI_MAX_RETRIES") or 3)
    initial_delay = int(Settings.get("AI_INITIAL_DELAY_SECONDS") or 30)

    core = ReviewCore(
        repo_url=repo_url,
        repo_path=local_path,
        ssh_key_path=ctx['SSH_KEY_PATH'],
        model_name=ctx['MODEL'],
        skip_host_key_check=ctx['SKIP_HOST_KEY_CHECK'],
        max_retries=max_retries,
        initial_delay_seconds=initial_delay
    )

    return core.run_review(
        base_branch=base_branch,
        feature_branch=feature_branch,
        mode=mode,
        temperature=temperature,
        max_output_tokens=max_tokens
    )


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


# 引数をデータクラスで受け取るように変更 (行番号 146)
def _run_review_command(ctx: dict, params: ReviewParams) -> None:
    """
    Gitレビューのメインフローを調整するメソッド。（責務はフロー管理に集中）
    """
    if params.local_path is None:
        # local_path のデフォルト設定を params.local_path に反映
        params.local_path = _get_default_local_path(params.mode)

    # ctx は辞書なので、直接キーでアクセス
    _print_info(
        params.mode,
        feature_branch=params.feature_branch,
        repo_url=params.repo_url,
        base_branch=params.base_branch,
        local_path=params.local_path,
        model_name=ctx['MODEL'],
        ssh_key_path=ctx['SSH_KEY_PATH'],
        temperature=params.temperature,
        max_tokens=params.max_tokens
    )

    try:
        # レビューを実行
        success, result_message = _execute_review(
            ctx=ctx,
            repo_url=params.repo_url,
            local_path=params.local_path,
            base_branch=params.base_branch,
            feature_branch=params.feature_branch,
            mode=params.mode,
            temperature=params.temperature,
            max_tokens=params.max_tokens
        )

        # 結果の出力と終了処理
        _handle_review_result(success, result_message)

    except Exception as e:
        logger.error(f"致命的なエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)


# --- DETAIL コマンド ---
@cli.command()
@common_options
@click.pass_context
def detail(ctx, repo_url, feature_branch, base_branch, local_path, temperature, max_tokens):
    """
    [詳細レビュー] リポジトリURLとフィーチャーブランチを指定し、コード品質に焦点を当てたAIレビューを実行します。
    """
    # ReviewParams をインスタンス化して引数をカプセル化
    params = ReviewParams(
        feature_branch=feature_branch,
        repo_url=repo_url,
        base_branch=base_branch,
        local_path=local_path,
        mode="detail",
        temperature=temperature,
        max_tokens=max_tokens,
    )
    _run_review_command(ctx.obj, params)


# --- RELEASE コマンド ---
@cli.command()
@common_options
@click.pass_context
def release(ctx, repo_url, feature_branch, base_branch, local_path, temperature, max_tokens):
    """
    [リリースレビュー] リポジトリURLとフィーチャーブランチを指定し、本番リリース可否に焦点を当てたAIレビューを実行します。
    """
    # ReviewParams をインスタンス化して引数をカプセル化
    params = ReviewParams(
        feature_branch=feature_branch,
        repo_url=repo_url,
        base_branch=base_branch,
        local_path=local_path,
        mode="release",
        temperature=temperature,
        max_tokens=max_tokens,
    )
    _run_review_command(ctx.obj, params)


if __name__ == '__main__':
    cli(obj={})
