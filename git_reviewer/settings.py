import os
import sys
from typing import Optional, Any
from pathlib import Path
import importlib.util

class Settings:
    """
    環境変数またはconfig.pyファイルから設定値を管理するクラス。
    """
    _config: Optional[Any] = None

    @classmethod
    def _initialize_config(cls):
        """
        config.pyモジュールを一度だけロードします。
        CLI実行ディレクトリ直下のconfig.pyを検索します。
        """
        if cls._config is not None:
            return

        # 修正: カレントディレクトリ直下の config.py を検索
        config_path = Path(os.getcwd()) / 'config.py'

        if not config_path.exists():
            print("情報: config.pyがカレントディレクトリに見つかりません。設定は環境変数を優先して読み込まれます。", file=sys.stderr)
            cls._config = None
            return

        try:
            # config.pyを動的にインポート
            spec = importlib.util.spec_from_file_location("config", str(config_path))
            config_module = importlib.util.module_from_spec(spec)
            sys.modules["config"] = config_module
            spec.loader.exec_module(config_module)
            cls._config = config_module
        except Exception as e:
            print(f"警告: config.pyのロード中にエラーが発生しました: {e}", file=sys.stderr)
            cls._config = None

    def __init__(self):
        """
        Settingsクラスは直接インスタンス化されるべきではありません。
        """
        raise TypeError("Settingsクラスはインスタンス化できません。Settings.get()を使用してください。")

    @staticmethod
    def get(name: str) -> Optional[str]:
        """
        設定値を取得します。環境変数がconfig.pyより優先されます。
        """
        # 初回呼び出し時に設定を初期化
        Settings._initialize_config()

        # 1. 環境変数を優先して検索
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()

        # 2. 環境変数になければ、ロード済みのconfigモジュールから検索
        if Settings._config:
            value = getattr(Settings._config, name, None)

            # 整数/浮動小数点数も文字列に変換して返す
            if value is not None:
                return str(value).strip()

        return None
