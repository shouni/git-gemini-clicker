import logging
import importlib.resources as pkg_resources
import os
from typing import Optional, Tuple
from .git_client import GitClient, GitClientError, BranchNotFoundError
from .ai_client import AIClient, AICallError

# ロギング設定: ライブラリのデフォルトロガーを設定
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class ReviewCore:
    """
    Git操作、プロンプト処理、Gemini API呼び出しを統括するコアロジッククラス。
    """

    def __init__(self,
                 repo_url: str,
                 local_path: str,
                 ssh_key_path: Optional[str],
                 model_name: str,
                 skip_host_key_check: bool = False):

        self.logger = logging.getLogger(__name__)

        self.repo_url = repo_url
        self.local_path = local_path
        self.model_name = model_name
        self.skip_host_key_check = skip_host_key_check

        # AIClientの初期化
        self.ai_client = AIClient(model_name=self.model_name)

        # GitClientの初期化とリポジトリの準備を実行
        self.git_client = GitClient(
            repo_url=repo_url,
            repo_path=local_path,
            ssh_key_path=ssh_key_path,
            skip_host_key_check=skip_host_key_check
        )

        self.logger.info("ReviewCore initialized and Git repository state confirmed.")


    # ----------------------------------------------
    # 1. プロンプトファイルの読み込み
    # ----------------------------------------------
    def _load_prompt_template(self, mode: str) -> str:
        """
        指定されたモードに基づき、パッケージリソースからMarkdownプロンプトテンプレートを読み込みます。
        """
        prompt_filename = f"prompt_{mode}.md"
        prompt_package = "git_reviewer.prompts"

        try:
            content = pkg_resources.files(prompt_package).joinpath(prompt_filename).read_text(encoding='utf-8')
            self.logger.info(f"Loaded prompt template: {prompt_filename}")
            return content
        except FileNotFoundError as e:
            raise FileNotFoundError(f"プロンプトファイル '{prompt_filename}' がパッケージリソース '{prompt_package}' 内に見つかりません。") from e
        except Exception as e:
            self.logger.error(f"プロンプトファイルの読み込み中に予期せぬエラー: {e}")
            raise


    # ----------------------------------------------
    # 🌟 メインのレビュー実行ロジック
    # ----------------------------------------------
    def run_review(self, base_branch: str, feature_branch: str, mode: str) -> Tuple[bool, str]:
        """
        AIレビューの全工程（差分取得、プロンプト適用、API呼び出し）を実行します。

        Note: _call_gemini_api メソッドは削除され、AIClientの呼び出しはここに統合されました。
        """
        self.logger.info(f"\n===== AI Review START: Mode={mode} =====")
        try:
            # 1. 差分の取得
            diff_content = self.git_client.get_diff(base_branch, feature_branch)

            if not diff_content.strip():
                self.logger.info("Info: 差分がありません。レビューをスキップしました。")
                return True, ""

            # 2. プロンプトテンプレートのロード
            prompt_template = self._load_prompt_template(mode)

            # 3. テンプレート処理とAPI呼び出し (統合されたロジック)
            # 修正箇所: .replace("[CODE_DIFF]", diff_content) から .format(diff_text=diff_content) へ変更
            final_prompt_content = prompt_template.format(diff_text=diff_content)
            self.logger.info(f"Final prompt created (length: {len(final_prompt_content)} characters).") # ロギングを追加

            # 💡 直接 AIClient のメソッドを呼び出す
            review_result = self.ai_client.generate_review(final_prompt_content)
            self.logger.info("AI review generated successfully.")

            return True, review_result

        except BranchNotFoundError as e:
            self.logger.error(f"指定されたブランチが存在しません。{e}")
            return False, f"Error: 指定されたブランチが存在しません。{e}"
        except GitClientError as e:
            self.logger.error(f"Git操作エラーが発生しました。詳細ログを確認してください。")
            return False, f"Error: Git操作中に問題が発生しました。詳細ログを確認してください。"
        except FileNotFoundError as e:
            self.logger.error(f"プロンプトファイルが見つかりません。{e}")
            return False, f"Error: プロンプトファイルが見つかりません。{e}"
        except AICallError as e:
            self.logger.error(f"Gemini API呼び出しエラー: {e}")
            return False, f"Error: Gemini APIの呼び出し中に致命的なエラーが発生しました。{e}"
        except Exception as e:
            self.logger.error(f"予期せぬエラーが発生しました: {type(e).__name__}: {e}", exc_info=True)
            return False, f"Error: 予期せぬエラーが発生しました。{type(e).__name__}: {e}"
        finally:
            self.logger.info("===== AI Review END =====")