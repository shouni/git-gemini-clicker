import logging
import time
import os
from google import genai
from google.genai.errors import APIError
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError
from typing import Optional
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

# 安全性評価用のユーティリティ関数
def _check_safety_filtering(response) -> Optional[str]:
    """レスポンスがフィルタリングされたか確認し、理由を返す"""
    if response and response.candidates:
        candidate = response.candidates[0]
        if candidate.finish_reason.name != 'STOP':
            reason = candidate.finish_reason.name
            if reason == 'SAFETY':
                # 安全性フィルタリングの詳細を取得
                safety_ratings = [
                    f"{r.category.name}: {r.probability.name}"
                    for r in candidate.safety_ratings
                ]
                return f"Safety Filtered. Reason: {', '.join(safety_ratings)}"

            return f"Generation failed. Finish reason: {reason}"

    return None

class AIClient:
    """
    Gemini APIとの通信を管理し、リトライロジックを実装するクライアント。
    Go版の堅牢な設計（リトライ・遅延メカニズム）を再現します。
    """
    def __init__(self,
                 model_name: str,
                 api_key: Optional[str] = None,
                 max_retries: int = 3,
                 initial_delay_seconds: int = 30):

        self.model_name = model_name
        self.MAX_RETRIES = max_retries
        self.INITIAL_DELAY = initial_delay_seconds

        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                ai_client_logger.error("GEMINI_API_KEYが設定されていません。")
                raise AICallError("Gemini API Clientの初期化に失敗しました。環境変数 GEMINI_API_KEY を設定してください。")

        self.client = genai.Client(api_key=api_key)
        ai_client_logger.info("Gemini API Client initialized successfully.")


    def generate_review(self,
                        prompt_content: str,
                        temperature: float,
                        max_output_tokens: int) -> str:
        """
        プロンプトに基づいてGemini APIを呼び出し、堅牢なリトライ処理を実行します。
        """
        ai_client_logger.info(f"Calling Gemini API with model: {self.model_name}")
        config_dict = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }

        # Contentオブジェクトを作成
        contents_object = [
            Content(
                role="user",
                parts=[Part(text=prompt_content)]
            )
        ]

        for attempt in range(self.MAX_RETRIES):
            is_retryable = False

            try:
                # API呼び出し
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents_object,
                    config=config_dict
                )

                # 修正: response.text にアクセスする前に None チェックを行う
                if response.text is None or not response.text.strip():
                    filter_message = _check_safety_filtering(response)

                    if filter_message:
                        ai_client_logger.error(f"AI generation failed: {filter_message}")
                        # フィルタリングはリトライしても無駄なので、AICallErrorとして再送出
                        raise AICallError(f"AI出力がブロックされました: {filter_message}")

                    # フィルタリング以外でテキストがNoneの場合 (リトライ対象)
                    ai_client_logger.warning("Gemini API returned empty or None content. Retrying if possible.")
                    is_retryable = True
                    # 強制的に次のループへ
                    if attempt < self.MAX_RETRIES - 1:
                        raise Exception("Empty content received, triggering retry logic.")
                    else:
                        raise AICallError("AIが空の応答を返し続けました。")

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

            except AICallError as e:
                # フィルタリングエラーや最終リトライでの空応答はここでキャッチし、再送出
                raise e

            except Exception as e:
                # 予期せぬエラー (空応答トリガーのエラーも含む)
                if not is_retryable:
                    ai_client_logger.exception("Unexpected error during AI API call.")

                # 空応答でリトライを試みる場合は、このブロックで is_retryable が True になっている
                if not is_retryable:
                    raise AICallError(f"AI呼び出し中に予期せぬエラーが発生しました: {e}") from e


            # リトライロジック
            if is_retryable and attempt < self.MAX_RETRIES - 1:
                delay = self.INITIAL_DELAY * (2 ** attempt)
                ai_client_logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)

            elif is_retryable and attempt == self.MAX_RETRIES - 1:
                raise MaxRetriesExceededError(f"API呼び出しが最大リトライ回数 ({self.MAX_RETRIES}回) を超えて失敗しました。")