import logging
import importlib.resources as pkg_resources
from typing import Optional, Tuple
from .git_client import GitClient, GitClientError, BranchNotFoundError # 同じパッケージのgit_clientをインポート

# ロギング設定: ライブラリのデフォルトロガーを設定
# アプリケーションがbasicConfigを呼び出さない限り、このロガーからのメッセージは出力されない
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
# logger.propagate = False # NullHandlerを設定する場合、通常は不要

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

        self.logger = logging.getLogger(__name__) # インスタンス内でロガーを使用

        self.repo_url = repo_url
        self.local_path = local_path
        self.model_name = model_name
        self.skip_host_key_check = skip_host_key_check

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
            # FileNotFoundErrorはそのまま再送出
            raise FileNotFoundError(f"プロンプトファイル '{prompt_filename}' がパッケージリソース '{prompt_package}' 内に見つかりません。") from e
        except Exception as e:
            self.logger.error(f"プロンプトファイルの読み込み中に予期せぬエラー: {e}")
            raise


    # ----------------------------------------------
    # 2. Gemini API の呼び出し (TODO: 次のステップで実装)
    # ----------------------------------------------
    def _call_gemini_api(self, prompt_content: str) -> str:
        """
        Gemini APIを呼び出すダミー関数。
        """
        # --- [TODO: google-genai SDKの実装] ---
        # ダミー結果を返す
        return f"[[PLACEHOLDER: AI Review Result for model {self.model_name}]]\n\n--- Prompt Snippet ---\n{prompt_content[:200]}..."


    # ----------------------------------------------
    # 🌟 メインのレビュー実行ロジック
    # ----------------------------------------------
    def run_review(self, base_branch: str, feature_branch: str, mode: str) -> Tuple[bool, str]:
        """
        AIレビューの全工程（差分取得、プロンプト適用、API呼び出し）を実行します。
        """
        self.logger.info(f"\n===== AI Review START: Mode={mode} =====")
        try:
            # 1. 差分の取得 (GitClientに処理を委譲)
            diff_content = self.git_client.get_diff(base_branch, feature_branch)

            if not diff_content.strip():
                self.logger.info("Info: 差分がありません。レビューをスキップしました。")
                return True, ""

            # 2. プロンプトテンプレートのロード
            prompt_template = self._load_prompt_template(mode)

            # 3. テンプレート処理とAPI呼び出し
            final_prompt_content = prompt_template.replace("[CODE_DIFF]", diff_content)

            review_result = self._call_gemini_api(final_prompt_content)

            return True, review_result

        except BranchNotFoundError as e:
            self.logger.error(f"指定されたブランチが存在しません。{e}")
            return False, f"Error: 指定されたブランチが存在しません。{e}"
        except GitClientError as e:
            self.logger.error(f"Git操作エラーが発生しました。詳細ログを確認してください。")
            return False, f"Error: Git操作中に問題が発生しました。"
        except FileNotFoundError as e:
            self.logger.error(f"プロンプトファイルが見つかりません。{e}")
            return False, f"Error: プロンプトファイルが見つかりません。{e}"
        except Exception as e:
            self.logger.error(f"予期せぬエラーが発生しました: {type(e).__name__}: {e}", exc_info=True)
            return False, f"Error: 予期せぬエラーが発生しました。{type(e).__name__}: {e}"
        finally:
            self.logger.info("===== AI Review END =====")