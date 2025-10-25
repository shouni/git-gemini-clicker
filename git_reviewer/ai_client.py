import logging
import time
import os
from google import genai
from google.genai.errors import APIError
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError
from typing import Optional

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

class AIClient:
    """
    Gemini APIとの通信を管理し、リトライロジックを実装するクライアント。
    Go版の堅牢な設計（リトライ・遅延メカニズム）を再現します。
    """
    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        self.MAX_RETRIES = 3
        self.INITIAL_DELAY = 30

        if api_key is None:
            # 環境変数から取得を試みる
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                ai_client_logger.error("GEMINI_API_KEYが設定されていません。")
                raise AICallError("Gemini API Clientの初期化に失敗しました。環境変数 GEMINI_API_KEY を設定してください。")

        # APIクライアントを初期化
        self.client = genai.Client(api_key=api_key)
        ai_client_logger.info("Gemini API Client initialized successfully.")


    def generate_review(self, prompt_content: str) -> str:
        """
        プロンプトに基づいてGemini APIを呼び出し、堅牢なリトライ処理を実行します。
        """
        ai_client_logger.info(f"Calling Gemini API with model: {self.model_name}")

        for attempt in range(self.MAX_RETRIES):
            # 修正: ループの各イテレーションでis_retryableを初期化する
            is_retryable = False

            try:
                # API呼び出しの実行
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt_content]
                )

                # 改善: 応答が空でないかチェックする
                if not response.text.strip():
                    ai_client_logger.warning("Gemini API returned empty content. It might be filtered or failed silently.")
                    # 空のレビューとして返すことで、CLIが空の結果を処理できるようにする
                    return ""

                    # 成功
                return response.text

            except ResourceExhausted as e:
                ai_client_logger.warning(f"Rate limit exceeded (Attempt {attempt + 1}/{self.MAX_RETRIES}).")
                is_retryable = True
            except (ServiceUnavailable, InternalServerError) as e:
                ai_client_logger.warning(f"Server error (Attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                is_retryable = True
            except APIError as e:
                if e.code is not None and e.code >= 500:
                    ai_client_logger.warning(f"Server error {e.code} (Attempt {attempt + 1}/{self.MAX_RETRIES}).")
                    is_retryable = True
                else:
                    ai_client_logger.error(f"Non-retryable API Error: {e}")
                    raise AICallError(f"Gemini APIクライアントエラー: {e}") from e

            except Exception as e:
                ai_client_logger.error(f"Unexpected error during API call: {e}")
                raise AICallError(f"AI呼び出し中に予期せぬエラーが発生しました: {e}") from e

            # リトライロジック
            if is_retryable and attempt < self.MAX_RETRIES - 1:
                delay = self.INITIAL_DELAY * (2 ** attempt)
                ai_client_logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)

            elif is_retryable and attempt == self.MAX_RETRIES - 1:
                # 最終リトライ失敗
                raise RateLimitExceeded(f"API呼び出しが最大リトライ回数 ({self.MAX_RETRIES}回) を超えて失敗しました。") from e
