import fire
import sys
import tempfile
from pathlib import Path
from typing import Optional
import logging

# --- コアロジックをインポート ---
from git_reviewer.core import ReviewCore

# CLIとしてのログ設定（アプリケーションのエントリポイントとして設定）
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class GitGeminiReviewerCLI:
    """
    Python版 Git Gemini Reviewer CLI
    詳細レビュー (detail) と リリースレビュー (release) のためのコマンドを提供します。
    """

    def __init__(self,
                 model: str = "gemini-2.5-flash",
                 ssh_key_path: str = "~/.ssh/id_rsa",
                 skip_host_key_check: bool = False):

        self.model_name = model
        self.ssh_key_path = ssh_key_path
        self.skip_host_key_check = skip_host_key_check

        logger.info(f"--- CLI初期化完了 ---")
        logger.info(f"使用モデル: {self.model_name}")
        logger.info("----------------------")


    def _get_default_local_path(self, command: str) -> str:
        """Go版のデフォルトパス生成をエミュレート (一時ディレクトリ内に作成)"""
        base_dir = Path(tempfile.gettempdir()) / "prototypus-ai-doc-go-repos" # ユーザーのGoツール名に合わせてディレクトリ名を調整
        local_repo_name = f"tmp-{command}"
        return str(base_dir / local_repo_name)


    def _print_info(self, command: str, **kwargs):
        """引数情報を表示するダミー関数 (デバッグ用)"""
        logger.info(f"\n--- {command.upper()} モード引数確認 (DEBUG) ---")
        for key, value in kwargs.items():
            logger.info(f"{key}: {value}")
        logger.info(f"グローバルモデル設定: {self.model_name}")
        logger.info(f"グローバルSSH設定: {self.ssh_key_path} (Skip Host Check: {self.skip_host_key_check})")
        logger.info("------------------------------------------")


    def _run_review_command(self,
                            feature_branch: str,
                            git_clone_url: str,
                            base_branch: str,
                            local_path: Optional[str],
                            mode: str) -> Optional[str]:
        """
        共通ロジックを処理するヘルパーメソッド。
        ReviewCoreを初期化し、レビューを実行します。
        成功時は結果メッセージを返し、失敗時はsys.exit(1)で強制終了します。
        """
        if local_path is None:
            local_path = self._get_default_local_path(mode)

        self._print_info(
            mode,
            feature_branch=feature_branch,
            git_clone_url=git_clone_url,
            base_branch=base_branch,
            local_path=local_path
        )

        # ReviewCore の初期化と実行
        core = ReviewCore(
            repo_url=git_clone_url,
            local_path=local_path,
            ssh_key_path=self.ssh_key_path,
            model_name=self.model_name,
            skip_host_key_check=self.skip_host_key_check
        )
        success, result_message = core.run_review(base_branch, feature_branch, mode)

        if success:
            # 成功時は結果メッセージを出力し、fireの戻り値として渡す
            if result_message:
                return f"\n--- AIレビュー結果 ---\n{result_message}"
            else:
                return "レビュー処理が完了しました。" # 差分なしなど
        else:
            # 失敗時はエラーメッセージをstderrに出力し、非ゼロ終了コードで終了
            print(f"\n--- AIレビュー失敗 ---\n{result_message}", file=sys.stderr)
            sys.exit(1)


    def detail(self,
               feature_branch: str,
               git_clone_url: str,
               base_branch: str = "main",
               local_path: Optional[str] = None):
        """
        [詳細レビュー] コード品質と保守性に焦点を当てたAIレビューを実行します。
        """
        # 共通ヘルパーメソッドを呼び出し
        return self._run_review_command(feature_branch, git_clone_url, base_branch, local_path, "detail")


    def release(self,
                feature_branch: str,
                git_clone_url: str,
                base_branch: str = "main",
                local_path: Optional[str] = None):
        """
        [リリースレビュー] 本番リリース可否の判定に焦点を当てたAIレビューを実行します。
        """
        # 共通ヘルパーメソッドを呼び出し
        return self._run_review_command(feature_branch, git_clone_url, base_branch, local_path, "release")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        logger.info("実行にはコマンドと必須引数が必要です。ヘルプを表示します。")
        # fire.Fire はヘルプ表示後に自動的に終了コード0で終了するため、sys.exit(0)は不要
        fire.Fire(GitGeminiReviewerCLI, command=['--help'])
    else:
        try:
            # fireが例外を発生させた場合、sys.exit(1)で終了させることを保証
            fire.Fire(GitGeminiReviewerCLI)
        except SystemExit as e:
            # _run_review_command 内の sys.exit(1) を捕捉
            sys.exit(e.code)
        except Exception as e:
            # fireが処理しきれなかった予期せぬエラー
            logger.error(f"致命的なCLIエラー: {e}")
            sys.exit(1)