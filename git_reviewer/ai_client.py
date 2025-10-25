import logging
import time
import os
from google import genai
from google.genai.errors import APIError
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
        self.MAX_RETRIES = 3  # Go版と同様の堅牢な設定
        self.INITIAL_DELAY = 30 # 初期遅延時間（秒）

        if api_key is None:
            # 環境変数から取得を試みる
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                ai_client_logger.error("GEMINI_API_KEYが設定されていません。")
                raise AICallError("Gemini API Clientの初期化に失敗しました。環境変数 GEMINI_API_KEY を設定してください。")

        try:
            # APIクライアントを初期化
            self.client = genai.Client(api_key=api_key)
            ai_client_logger.info("Gemini API Client initialized successfully.")
        except Exception as e:
            ai_client_logger.error(f"Gemini API Clientの初期化に失敗しました: {e}")
            raise AICallError("Gemini API Clientの初期化に失敗しました。")


    def generate_review(self, prompt_content: str) -> str:
        """
        プロンプトに基づいてGemini APIを呼び出し、堅牢なリトライ処理を実行します。

        Args:
            prompt_content (str): Diffとテンプレートを結合した最終的なプロンプト。

        Returns:
            str: AIによって生成されたレビュー結果のテキスト。

        Raises:
            AICallError: リトライ後もAPI呼び出しが失敗した場合。
        """
        ai_client_logger.info(f"Calling Gemini API with model: {self.model_name}")

        for attempt in range(self.MAX_RETRIES):
            try:
                # 💡 API呼び出しの実行
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt_content]
                )

                # 成功
                return response.text

            except APIError as e:
                # APIErrorの処理
                str_e = str(e).lower()
                is_retryable = False

                if "rate limit" in str_e or "quota" in str_e:
                    # レートリミットエラーはリトライ対象
                    ai_client_logger.warning(f"Rate limit exceeded (Attempt {attempt + 1}/{self.MAX_RETRIES}).")
                    is_retryable = True
                elif e.code is not None and e.code >= 500:
                    # サーバーエラー (5xx) もリトライ対象
                    ai_client_logger.warning(f"Server error {e.code} (Attempt {attempt + 1}/{self.MAX_RETRIES}).")
                    is_retryable = True
                else:
                    # その他のクライアントエラー (4xx) はリトライしない
                    ai_client_logger.error(f"Non-retryable API Error: {e}")
                    raise AICallError(f"Gemini APIクライアントエラー: {e}") from e

                if is_retryable and attempt < self.MAX_RETRIES - 1:
                    # 💡 指数関数的バックオフの実装: 2, 4, 8, 16...秒と遅延を増加
                    delay = self.INITIAL_DELAY * (2 ** attempt)
                    ai_client_logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)

                elif is_retryable and attempt == self.MAX_RETRIES - 1:
                    # 最終リトライ失敗
                    raise RateLimitExceeded(f"API呼び出しが最大リトライ回数 ({self.MAX_RETRIES}回) を超えて失敗しました。") from e

            except Exception as e:
                # 予期せぬエラー
                ai_client_logger.error(f"Unexpected error during API call: {e}")
                raise AICallError(f"AI呼び出し中に予期せぬエラーが発生しました: {e}") from e

        # MAX_RETRIESを超えてループを抜けた場合（論理的には到達しない）
        raise AICallError(f"API呼び出しが最大リトライ回数 ({self.MAX_RETRIES}回) を超えて失敗しました。")