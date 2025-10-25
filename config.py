"""
Git Gemini Clicker のデフォルト設定値を定義するファイル。
CLIオプションや環境変数で上書きされない場合の基本値を提供します。
"""
import os

# --- Git 設定 ---
# 差分比較の基準となるデフォルトブランチ名
DEFAULT_BASE_BRANCH: str = "main"

# SSH認証キーのデフォルトパス (os.path.expanduser を使用してホームディレクトリを展開)
# DEFAULT_SSH_KEY_PATH: str = os.path.expanduser("~/.ssh/id_rsa")


# --- AI/LLM 設定 ---
# 使用する Gemini モデル名
DEFAULT_MODEL_NAME: str = "gemini-2.5-flash"

# LLMの応答のランダム性 (0.0:決定論的 〜 1.0:創造的)
DEFAULT_TEMPERATURE: float = 0.2

# LLMの最大出力トークン数
DEFAULT_MAX_TOKENS: int = 20480


# --- 堅牢性/リトライ設定 (ai_client.py で使用) ---
# API呼び出しの最大リトライ回数
DEFAULT_MAX_RETRIES: int = 3

# 指数バックオフの初期遅延時間（秒）
DEFAULT_INITIAL_DELAY_SECONDS: int = 30
