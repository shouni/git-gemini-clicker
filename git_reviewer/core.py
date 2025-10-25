import logging
import importlib.resources as pkg_resources
from typing import Optional, Tuple
from .git_client import GitClient, GitClientError, BranchNotFoundError # 同じパッケージのgit_clientをインポート

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

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

        self.repo_url = repo_url
        self.local_path = local_path
        self.model_name = model_name
        self.skip_host_key_check = skip_host_key_check

        # GitClientの初期化とリポジトリの準備（クローン/オープン/URLチェック/再クローン）を実行
        # Go版の堅牢な設計に従い、初期化時にリポジトリの状態を確定させます。
        self.git_client = GitClient(
            repo_url=repo_url,
            repo_path=local_path,
            ssh_key_path=ssh_key_path,
            skip_host_key_check=skip_host_key_check
        )

        logging.info("ReviewCore initialized and Git repository state confirmed.")


    # ----------------------------------------------
    # 🌟 1. プロンプトファイルの読み込み (実装済み)
    # ----------------------------------------------
    def _load_prompt_template(self, mode: str) -> str:
        """
        指定されたモード (detail/release) に基づき、
        パッケージリソースからMarkdownプロンプトテンプレートを読み込みます。

        Args:
            mode (str): 'detail' または 'release'.

        Returns:
            str: 読み込まれたプロンプトテンプレートの内容。

        Raises:
            FileNotFoundError: 対応するプロンプトファイルが見つからない場合。
        """
        prompt_filename = f"prompt_{mode}.md"
        prompt_package = "git_reviewer.prompts"

        try:
            content = pkg_resources.files(prompt_package).joinpath(prompt_filename).read_text(encoding='utf-8')
            logging.info(f"Loaded prompt template: {prompt_filename}")
            return content
        except FileNotFoundError as e:
            raise FileNotFoundError(f"プロンプトファイル '{prompt_filename}' がパッケージリソース '{prompt_package}' 内に見つかりません。") from e
        except Exception as e:
            logging.error(f"プロンプトファイルの読み込み中に予期せぬエラー: {e}")
            raise


    # ----------------------------------------------
    # 💡 2. Gemini API の呼び出し (TODO: 次のステップで実装)
    # ----------------------------------------------
    def _call_gemini_api(self, prompt_content: str) -> str:
        """
        Gemini APIを呼び出すダミー関数。
        Go版と同様に、google-genai SDKを使用してAPIを呼び出し、堅牢なリトライ処理を含めます。
        """
        # --- [TODO: google-genai SDKの実装] ---
        # 実際には、ここで API Client を初期化し、
        # diff_contentを含んだプロンプトを渡し、レスポンスを返す処理が入ります。

        # ダミー結果を返す
        return f"[[PLACEHOLDER: AI Review Result for model {self.model_name}]]\n\n--- Prompt Snippet ---\n{prompt_content[:200]}..."


    # ----------------------------------------------
    # 🌟 メインのレビュー実行ロジック
    # ----------------------------------------------
    def run_review(self, base_branch: str, feature_branch: str, mode: str) -> Tuple[bool, str]:
        """
        AIレビューの全工程（差分取得、プロンプト適用、API呼び出し）を実行します。

        Returns:
            Tuple[bool, str]: (成功/失敗, 結果メッセージ/エラーメッセージ)
        """
        print(f"\n===== AI Review START: Mode={mode} =====")
        try:
            # 1. 差分の取得 (GitClientに処理を委譲)
            # Go版と同様に、3点比較による「純粋な差分」を取得します。
            diff_content = self.git_client.get_diff(base_branch, feature_branch)

            if not diff_content.strip():
                print("Info: 差分がありません。レビューをスキップしました。")
                return True, ""

            # 2. プロンプトテンプレートのロード
            prompt_template = self._load_prompt_template(mode)

            # 3. テンプレート処理とAPI呼び出し
            # Go版と同様に、{{ .CodeDiff }} のようなプレースホルダーを置換
            # シンプルな置換 (Go版のテンプレート処理は次のステップで詳細化可能)
            final_prompt_content = prompt_template.replace("[CODE_DIFF]", diff_content)

            review_result = self._call_gemini_api(final_prompt_content)

            return True, review_result

        except BranchNotFoundError as e:
            return False, f"Error: 指定されたブランチが存在しません。{e}"
        except GitClientError as e:
            logging.error(f"Git操作エラーが発生しました: {e}")
            return False, f"Error: Git操作中に問題が発生しました。詳細ログを確認してください。"
        except FileNotFoundError as e:
            return False, f"Error: プロンプトファイルが見つかりません。{e}"
        except Exception as e:
            logging.error(f"予期せぬエラー: {e}", exc_info=True)
            return False, f"Error: 予期せぬエラーが発生しました。{type(e).__name__}: {e}"
        finally:
            print("===== AI Review END =====")
