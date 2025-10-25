import logging
import os
import shutil
from typing import Tuple, Optional
from pathlib import Path

# 依存モジュールをインポート
# GitCommandError は GitClient の中で使われているので、ここではインポート不要
from .git_client import GitClient, GitClientError, BranchNotFoundError
from .ai_client import AIClient, AICallError

# ロガー設定
core_logger = logging.getLogger(__name__)
core_logger.addHandler(logging.NullHandler())

# --- ReviewCore Class ---
class ReviewCore:
    """
    Git操作とAIレビューロジックを統合するコアクラス。
    """
    def __init__(self,
                 repo_url: str,
                 repo_path: str, # 👈 修正: local_path を repo_path に変更 (GitClient に合わせる)
                 ssh_key_path: str,
                 model_name: str,
                 skip_host_key_check: bool,
                 max_retries: int,
                 initial_delay_seconds: int):

        self.repo_path = repo_path # 👈 インスタンス変数名も repo_path に変更

        # Gitクライアントを初期化
        # 修正: キーワード引数を local_path から repo_path に変更
        self.git_client = GitClient(
            repo_url=repo_url,
            repo_path=repo_path, # 👈 修正: local_path だった引数を repo_path に変更
            ssh_key_path=ssh_key_path,
            skip_host_key_check=skip_host_key_check
        )

        # AIクライアントを初期化
        self.ai_client = AIClient(
            model_name=model_name,
            max_retries=max_retries,
            initial_delay_seconds=initial_delay_seconds
        )

        core_logger.info("ReviewCore initialized.")

    def _load_prompt_template(self, mode: str) -> str:
        """
        パッケージ内の prompts ディレクトリからプロンプトテンプレートファイルを読み込みます。
        """
        # core.py があるディレクトリ (git_reviewer) から prompts ディレクトリへの相対パスを使用
        current_dir = Path(__file__).parent # git_reviewer ディレクトリを指す
        prompt_dir = current_dir / "prompts"

        prompt_filename = f"prompt_{mode}.md" # 例: prompt_detail.md
        prompt_path = prompt_dir / prompt_filename

        core_logger.info(f"Attempting to load prompt from: {prompt_path.resolve()}")

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found for mode '{mode}': {prompt_path.resolve()}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def run_review(self,
                   base_branch: str,
                   feature_branch: str,
                   mode: str,
                   temperature: float,
                   max_output_tokens: int) -> Tuple[bool, str]:
        """
        メインのレビュー実行フロー。Git操作とAI呼び出しを順に行う。
        """
        try:
            # 1. Gitリポジトリのセットアップ（クローン/フェッチ）
            core_logger.info("フェーズ1: Gitリポジトリのセットアップ開始...")

            # GitClientの run_setup() は clone_or_open() に置き換わったため、メソッド名を修正
            self.git_client.clone_or_open()

            # 2. 差分取得
            # 新しい GitClient は get_diff の中で fetch を含むため、ブランチ切り替えは不要
            core_logger.info("フェーズ2: 差分取得を開始...")

            # 差分を取得（3点比較による pure diff）
            diff_content = self.git_client.get_diff(base_branch, feature_branch)

            if not diff_content.strip():
                return True, "Success: 差分が見つからなかったため、レビューをスキップしました。"

            core_logger.info(f"差分取得完了: {len(diff_content.splitlines())}行の変更を検出。")

            # 3. プロンプトの準備
            try:
                prompt_template = self._load_prompt_template(mode)
                prompt_content = prompt_template.format(diff_content=diff_content)
            except FileNotFoundError as e:
                core_logger.error(f"プロンプトファイルのロードエラー: {e}")
                return False, f"Error: {e}"

            # 4. AIレビューの実行
            core_logger.info(f"フェーズ3: AIレビュー呼び出し開始 (モード: {mode})...")
            review_result = self.ai_client.generate_review(
                prompt_content=prompt_content,
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )

            core_logger.info("AIレビュー完了。")
            return True, review_result

        except (BranchNotFoundError, GitClientError, AICallError, Exception) as e:
            core_logger.error(f"レビュー処理中にエラーが発生しました: {e}")
            return False, str(e)

        finally:
            # CLI側で渡された local_path は一時ディレクトリなので、ここでは特にクリーンアップは行いません
            # （一時ディレクトリの管理は _run_review_command の外で行う方が堅牢なため）
            pass
