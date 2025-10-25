import logging
import time
import os
from google import genai
from google.genai.errors import APIError
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError
from typing import Optional, Iterator
# Content, Partオブジェクトを使用するためにインポート
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
    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        # Go版の設計に合わせて、最大リトライ回数と初期遅延を設定
        self.MAX_RETRIES = 3
        # 初期遅延を30秒に設定
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


    def generate_review(self, prompt_content: str, temperature: float = 0.2, max_output_tokens: int = 4096) -> Iterator[str]:
        """
        プロンプトに基づいてGemini APIを呼び出し、堅牢なリトライ処理を実行しつつ、結果をストリーミングで返します。

        Args:
            prompt_content: モデルに渡すプロンプト文字列。
            temperature: 応答のランダム性を制御する温度。デフォルトは0.2 (コードレビュー向け)。
            max_output_tokens: 生成される応答の最大トークン数。

        Returns:
            strを生成するイテレータ（ジェネレータ）。
        """
        ai_client_logger.info(f"Calling Gemini API with model: {self.model_name} (Streaming)")

        # Contentオブジェクトを作成し、role="user"を明示
        contents_object = [
            Content(
                role="user",
                parts=[Part(text=prompt_content)]
            )
        ]

        # ストリーミング処理のため、try-exceptブロック全体をリトライループで囲む
        for attempt in range(self.MAX_RETRIES):
            is_retryable = False

            try:
                # API呼び出しの実行: generate_content_streamを使用し、設定を直接キーワード引数で渡す
                stream_response = self.client.models.generate_content_stream(
                    model=self.model_name,
                    contents=contents_object,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens
                )

                # ストリームを処理するジェネレータ
                for chunk in stream_response:
                    # チャンクが空でない場合にのみ yield
                    if chunk.text:
                        yield chunk.text

                # ストリームが最後まで到達した場合、正常終了とみなし、リトライを中断
                return

            except ResourceExhausted as e:
                ai_client_logger.warning(f"Rate limit exceeded (Attempt {attempt + 1}/{self.MAX_RETRIES}).")
