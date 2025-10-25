import fire
import sys
import tempfile
from pathlib import Path

# --- 💡 (次のステップで) ここにコアロジックをインポートします ---
# from git_reviewer.core import ReviewCore

class GitGeminiReviewerCLI:
    """
    Python版 Git Gemini Reviewer CLI
    詳細レビュー (detail) と リリースレビュー (release) のためのコマンドを提供します。
    """

    def __init__(self,
                 model: str = "gemini-2.5-flash",
                 ssh_key_path: str = "~/.ssh/id_rsa", # 👈 SSHキーパスを追加 (Go版のデフォルト値)
                 skip_host_key_check: bool = False): # 👈 ホストキーチェックを追加

        self.model_name = model
        self.ssh_key_path = ssh_key_path
        self.skip_host_key_check = skip_host_key_check # 未使用だが互換性のため保持

        # ... (他の初期化)


    def _get_default_local_path(self, command: str) -> str:
        """Go版のデフォルトパス生成をエミュレート (一時ディレクトリ内に作成)"""
        # Go版のデフォルト: "/var/folders/.../git-reviewer-repos/tmp-generic"

        # 実行ごとにユニークな一時ディレクトリを作成
        base_dir = Path(tempfile.gettempdir()) / "git-reviewer-repos"
        # コマンド名に応じたサブディレクトリを生成 (Go版の 'tmp-generic' に相当)
        local_repo_name = f"tmp-{command}"
        return str(base_dir / local_repo_name)


    def _print_info(self, command: str, **kwargs):
        """引数情報を表示するダミー関数"""
        print(f"\n--- {command.upper()} モード引数確認 (実装前) ---")
        for key, value in kwargs.items():
            print(f"{key}: {value}")
        print(f"グローバルモデル設定: {self.model_name}")
        print(f"グローバルSSH設定: {self.ssh_key_path} (Skip Host Check: {self.skip_host_key_check})")
        print("------------------------------------------")

    # --- detail コマンド ---

    def detail(self,
               feature_branch: str,                               # 必須引数
               git_clone_url: str,                                # 👈 必須引数: リモートURLを追加
               base_branch: str = "main",                         # オプション引数 (デフォルト値あり)
               local_path: str = None,                            # 👈 オプション引数: クローン先パスを追加
               mode: str = "detail"):

        # local_path が指定されていない場合、デフォルトパスを生成
        if local_path is None:
            local_path = self._get_default_local_path("detail")

        self._print_info(
            "detail",
            feature_branch=feature_branch,
            git_clone_url=git_clone_url,
            base_branch=base_branch,
            local_path=local_path
        )

        # 💡 ここで GitClient を初期化し、get_diff を呼び出すロジックが入ります。
        # core = ReviewCore(...)
        # core.run_review(...)

        return "詳細レビュー処理の骨組み実行が完了しました。"


    # --- release コマンド ---

    def release(self,
                feature_branch: str,
                git_clone_url: str,                               # 👈 必須引数: リモートURLを追加
                base_branch: str = "main",
                local_path: str = None,
                mode: str = "release"):

        if local_path is None:
            local_path = self._get_default_local_path("release")

        self._print_info(
            "release",
            feature_branch=feature_branch,
            git_clone_url=git_clone_url,
            base_branch=base_branch,
            local_path=local_path
        )

        return "リリースレビュー処理の骨組み実行が完了しました。"


if __name__ == '__main__':
    # ... (fire.Fire の実行ロジックは変更なし)
    if len(sys.argv) == 1:
        print("実行にはコマンドと必須引数が必要です。ヘルプを表示します。")
        fire.Fire(GitGeminiReviewerCLI, command=['--help'])
    else:
        fire.Fire(GitGeminiReviewerCLI)
