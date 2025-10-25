import logging
import os
import shutil
from typing import Tuple, Optional
from pathlib import Path
from importlib.resources import files

# 依存モジュールをインポート
from .clients.git_client import GitClient, GitClientError, BranchNotFoundError
from .clients.ai_client import AIClient, AICallError

# ロガー設定
core_logger = logging.getLogger(__name__)
core_logger.addHandler(logging.NullHandler())

# --- ReviewCore Class ---
class ReviewCore:
    """
    Git操作とAIレビューロジックを統合するコアクラス。
    """
    # 許可されたプロンプトモードのホワイトリスト
    _ALLOWED_PROMPT_MODES = {"detail", "release"}

    def __init__(self,
                 repo_url: str,
                 repo_path: str, # ローカルリポジトリパス
                 ssh_key_path: str,
                 model_name: str,
                 skip_host_key_check: bool,
                 max_retries: int,
                 initial_delay_seconds: int):

        self.repo_path = repo_path

        # Gitクライアントを初期化
        self.git_client = GitClient(
            repo_url=repo_url,
            repo_path=repo_path,
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

        Args:
            mode (str): 使用するプロンプトモード。必ず _ALLOWED_PROMPT_MODES のいずれかであること。
        """
        # 以前の修正: modeのバリデーションを追加
        if mode not in self._ALLOWED_PROMPT_MODES:
            raise ValueError(f"Invalid prompt mode: '{mode}'. Allowed modes are: {', '.join(self._ALLOWED_PROMPT_MODES)}")

        prompt_filename = f"prompt_{mode}.md"

        try:
            # 'git_reviewer.prompts' はパッケージ名.サブディレクトリ名
            prompt_path = files('git_reviewer.prompts') / prompt_filename
        except Exception as e:
            # パッケージが正しくインポートできないなどの予期せぬエラー
            core_logger.error(f"Failed to locate prompt resource: {e}")
            raise FileNotFoundError(f"Failed to locate prompt resource for mode '{mode}'.") from e

        core_logger.info(f"Attempting to load prompt from: {prompt_path}")

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found for mode '{mode}': {prompt_path}")

        # files().read_text() を使用して直接ファイルの内容を読み込む
        # 以前のロジック: with open(prompt_path, 'r', encoding='utf-8') as f: return f.read()
        return prompt_path.read_text(encoding='utf-8')

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
            self.git_client.clone_or_open()

            # 2. 差分取得
            core_logger.info("フェーズ2: 差分取得を開始...")
            diff_content = self.git_client.get_diff(base_branch, feature_branch)

            if not diff_content.strip():
                return True, "Success: 差分が見つからなかったため、レビューをスキップしました。"

            core_logger.info(f"差分取得完了: {len(diff_content.splitlines())}行の変更を検出。")

            # 3. プロンプトの準備
            try:
                prompt_template = self._load_prompt_template(mode)

                # 以前の修正: テンプレートの契約（プレースホルダー名）をコメントで明示
                # NOTE: プロンプトテンプレートファイルは '{diff_content}' というプレースホルダーを持つことを想定しています。
                prompt_content = prompt_template.format(diff_content=diff_content)

            except FileNotFoundError as e:
                core_logger.error(f"プロンプトファイルのロードエラー: {e}")
                return False, f"Error: {e}"
            except ValueError as e:
                # 不正なプロンプトモードエラーをキャッチ
                core_logger.error(f"不正なプロンプトモードエラー: {e}")
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
            # クリーンアップは外側で行う
            pass
