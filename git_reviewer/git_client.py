import logging
import time
import os
from google import genai
from google.genai.errors import APIError
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError
from typing import Optional
# ContentとPartオブジェクトを使用するためにインポート
from google.genai.types import Content, Part

# ロガー設定
ai_client_logger = logging.getLogger(__name__)
ai_client_logger.addHandler(logging.NullHandler())

# --- Custom Exception ---
class AICallError(Exception):
    """AI API呼び出しに関連するエラーのベースクラス。"""
    pass

class RateLimitExceeded(AICallError):
    """レートリミットを超過した際のエラー。"""
    pass

class MaxRetriesExceededError(AICallError):
    """最大リトライ回数を超過した際のエラー。"""
    pass

class AIClient:
    """
    Gemini APIとの通信を管理し、リトライロジックを実装するクライアント。
    Go版の堅牢な設計（リトライ・遅延メカニズム）を再現します。
    """
    def __init__(self,
                 model_name: str,
                 api_key: Optional[str] = None,
                 # 修正: リトライ設定を引数として受け取る
                 max_retries: int = 3,
                 initial_delay_seconds: int = 30):

        self.model_name = model_name

        # 修正: 引数で渡された値で設定を上書き
        self.MAX_RETRIES = max_retries
        self.INITIAL_DELAY = initial_delay_seconds

        if api_key is None:
            # 環境変数から取得を試みる
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                ai_client_logger.error("GEMINI_API_KEYが設定されていません。")
                raise AICallError("Gemini API Clientの初期化に失敗しました。環境変数 GEMINI_API_KEY を設定してください。")

        # APIクライアントを初期化
        self.client = genai.Client(api_key=api_key)
        ai_client_logger.info("Gemini API Client initialized successfully.")


    def generate_review(self,
                        prompt_content: str,
                        # 修正: LLMパラメータを引数として受け取る
                        temperature: float,
                        max_output_tokens: int) -> str:
        """
        プロンプトに基づいてGemini APIを呼び出し、堅牢なリトライ処理を実行します。
        """
        ai_client_logger.info(f"Calling Gemini API with model: {self.model_name}")

        # Contentオブジェクトを作成し、role="user"を明示
        contents_object = [
            Content(
                role="user",
                parts=[Part(text=prompt_content)]
            )
        ]

        for attempt in range(self.MAX_RETRIES):
            # ループの各イテレーションでリトライ可能フラグを初期化
            is_retryable = False

            try:
                # API呼び出しの実行
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents_object,
                    # 修正: LLMパラメータをAPIに渡す
                    temperature=temperature,
                    max_output_tokens=max_output_tokens
                )

                # 応答が空でないかチェック (コンテンツフィルタリングやサイレント失敗の可能性に対応)
                if not response.text.strip():
                    ai_client_logger.warning("Gemini API returned empty content. It might be filtered or failed silently.")
                    # 空のレビューとして返す
                    return ""

                # 成功
                return response.text

            except ResourceExhausted as e:
                # レートリミットエラー
                ai_client_logger.warning(f"Rate limit exceeded (Attempt {attempt + 1}/{self.MAX_RETRIES}).")
                is_retryable = True
            except (ServiceUnavailable, InternalServerError) as e:
                # サーバーエラー (503, 500)
                ai_client_logger.warning(f"Server error (Attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                is_retryable = True
            except APIError as e:
                # その他のAPIエラー (特に5xx系)
                if e.code is not None and e.code >= 500:
                    ai_client_logger.warning(f"Server error {e.code} (Attempt {attempt + 1}/{self.MAX_RETRIES}).")
                    is_retryable = True
                else:
                    # リトライ不可能なエラー (例: 4xx クライアントエラー)
                    ai_client_logger.error(f"Non-retryable API Error: {e}")
                    raise AICallError(f"Gemini APIクライアントエラー: {e}") from e

            except Exception as e:
                # 予期せぬエラー (トレースバック付きでログを出力)
                ai_client_logger.exception("Unexpected error during AI API call.")
                raise AICallError(f"AI呼び出し中に予期せぬエラーが発生しました: {e}") from e

            # リトライロジック
            if is_retryable and attempt < self.MAX_RETRIES - 1:
                # 指数バックオフ
                delay = self.INITIAL_DELAY * (2 ** attempt)
                ai_client_logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)

            elif is_retryable and attempt == self.MAX_RETRIES - 1:
                # 最終リトライ失敗
                raise MaxRetriesExceededError(f"API呼び出しが最大リトライ回数 ({self.MAX_RETRIES}回) を超えて失敗しました。") from e
