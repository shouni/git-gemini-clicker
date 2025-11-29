import subprocess
import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict
import urllib.parse

# ロギング設定
git_client_logger = logging.getLogger(__name__)
git_client_logger.addHandler(logging.NullHandler())

# --- Custom Exceptions ---
class GitClientError(Exception):
    """GitClient関連のエラーベースクラス。"""
    pass

class GitCommandError(GitClientError):
    """Gitコマンドの実行失敗時に送出されるエラー。"""
    def __init__(self, message: str, stderr: str = ""):
        super().__init__(message)
        self.stderr = stderr
        # エラー発生時に詳細をログに出力
        git_client_logger.error(f"{message}\nstderr: {stderr.strip()}")

class BranchNotFoundError(GitClientError):
    """指定されたブランチがリポジトリに見つからない時に送出されるエラー。"""
    pass

# --- GitClient Implementation ---

class GitClient:
    """
    Go版のロジックに基づき、Gitリポジトリを操作するためのクライアントクラス。
    """

    def __init__(self,
                 repo_url: str,
                 repo_path: str,
                 ssh_key_path: Optional[str] = None,
                 skip_host_key_check: bool = False):

        self.logger = logging.getLogger(__name__)

        self.repo_url = repo_url
        self.repo_path = Path(repo_path).resolve()
        self.ssh_key_path = ssh_key_path
        self.skip_host_key_check = skip_host_key_check

        # コマンド実行時に使用する環境変数を準備
        self._git_env = os.environ.copy()
        if self.ssh_key_path:
            self._setup_ssh_env()

        # 初期化処理
        self.clone_or_open()


    def _setup_ssh_env(self):
        """
        SSH認証用の環境変数を self._git_env に設定する。
        プロセス全体の環境変数は汚染しない。
        """
        ssh_key_path = os.path.expanduser(self.ssh_key_path)
        clean_path = Path(os.path.abspath(ssh_key_path)).as_posix()

        if not Path(clean_path).is_file():
            self.logger.error(f"FATAL: SSHキーファイルが見つかりません: {clean_path}")
            return

        # コマンドを作成
        ssh_command = f'ssh -i "{clean_path}" -F /dev/null' # -F /dev/null でユーザー設定の影響を排除

        if self.skip_host_key_check:
            ssh_command += " -o StrictHostKeyChecking=no"
            self.logger.warning("SECURITY WARNING: StrictHostKeyChecking=no is set.")

        # インスタンス固有の環境変数辞書にセット
        self._git_env['GIT_SSH_COMMAND'] = ssh_command
        self.logger.debug(f"GIT_SSH_COMMAND configured: {ssh_command}")


    def _run_git_command(self,
                         command: List[str],
                         check: bool = True,
                         cwd: Optional[Path] = None,
                         ignore_errors: bool = False) -> subprocess.CompletedProcess:
        """
        指定されたGitコマンドを実行する内部ヘルパーメソッド。
        """
        if cwd is None:
            cwd = self.repo_path

        try:
            # subprocess.run に env 引数を渡す
            result = subprocess.run(
                ['git'] + command,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
                encoding='utf-8',
                env=self._git_env  # ★ 改善点: 固有の環境変数を使用
            )

            if result.returncode != 0 and check and not ignore_errors:
                raise GitCommandError(
                    f"Gitコマンド '{' '.join(command)}' の実行に失敗しました (Exit Code: {result.returncode})",
                    stderr=result.stderr
                )
            return result

        except FileNotFoundError:
            raise GitCommandError("'git' コマンドが見つかりません。")
        except Exception as e:
            raise GitCommandError(f"予期せぬ Git コマンド実行エラー: {e}")


    def _get_remote_url(self, remote: str = "origin") -> Optional[str]:
        """既存リポジトリの 'origin' リモートのURLを取得します。"""
        try:
            result = self._run_git_command(['config', '--get', f'remote.{remote}.url'], check=False, ignore_errors=True)
            if result.returncode != 0:
                return None
            return result.stdout.strip()
        except Exception:
            return None


    def _remove_and_clone(self, url: str):
        """既存のディレクトリを削除し、指定されたURLで新しくクローンします。"""
        if self.repo_path.exists():
            self.logger.info(f"Removing old repository directory {self.repo_path}...")
            try:
                shutil.rmtree(self.repo_path, ignore_errors=True)
            except Exception as e:
                raise GitClientError(f"Failed to remove old repository directory: {e}")

        self.logger.info(f"Cloning {url} into {self.repo_path}...")
        self.repo_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # クローン時も _run_git_command を使うことで SSH設定が適用される
            self._run_git_command(['clone', url, self.repo_path.name], check=True, cwd=self.repo_path.parent)
        except GitCommandError as e:
            raise GitClientError(f"Failed to clone repository {url}: {e.stderr}")


    def clone_or_open(self):
        """リポジトリの準備（クローンまたはオープン、URL検証）を行います。"""
        is_git_repo = self.repo_path.is_dir() and (self.repo_path / '.git').is_dir()

        if not is_git_repo:
            self._remove_and_clone(self.repo_url)
            self.logger.info(f"--- ✅ リポジトリをクローンしました: {self.repo_path} ---")
            return

        self.logger.info(f"Checking existing repository at {self.repo_path}...")
        existing_url = self._get_remote_url()

        if not existing_url:
            self.logger.warning("Remote 'origin' not found. Re-cloning...")
            self._remove_and_clone(self.repo_url)
            return

        # URLの正規化と比較 (簡易実装)
        def normalize(u):
            return u.strip().lower().rstrip('/').replace('git@github.com:', 'https://github.com/')

        if normalize(existing_url) != normalize(self.repo_url):
            self.logger.warning(f"URL mismatch ({existing_url} != {self.repo_url}). Re-cloning...")
            self._remove_and_clone(self.repo_url)
        else:
            self.logger.info(f"--- ✅ 既存リポジトリを利用します: {self.repo_path} ---")


    def fetch_updates(self, remote: str = "origin") -> None:
        """リモート情報を更新します。"""
        self.logger.info(f"Fetching updates from {remote}...")
        # --prune で削除されたブランチも同期
        self._run_git_command(['fetch', remote, '--prune'])


    def get_diff(self, base_branch: str, feature_branch: str, remote: str = "origin") -> str:
        """
        指定された2つのリモートブランチ間の「純粋な差分」（3点比較）を取得します。
        """
        # 1. Fetch (最新情報の取得)
        self.fetch_updates(remote)

        base_ref = f'{remote}/{base_branch}'
        feature_ref = f'{remote}/{feature_branch}'

        # 2. 存在チェック (rev-parse --verify)
        for ref in [base_ref, feature_ref]:
            res = self._run_git_command(['rev-parse', '--verify', ref], check=False)
            if res.returncode != 0:
                raise BranchNotFoundError(f"リモートブランチが見つかりません: {ref}")

        # 3. 3点比較 Diff の実行 (git diff base...feature)
        # これだけで「共通の祖先からfeatureまでの差分」が取れます。手動merge-base計算は不要です。
        self.logger.info(f"3点比較Diffを取得中: {base_ref}...{feature_ref}")

        diff_command = [
            'diff',
            f'{base_ref}...{feature_ref}', # 3点リーダー構文を使用
            '--unified=10'
        ]

        # 外部コマンド実行
        result = self._run_git_command(diff_command)

        self.logger.info(f"--- ✅ 差分取得完了 ({len(result.stdout)} bytes) ---")
        return result.stdout


    def cleanup(self, base_branch: str = "main", remote: str = "origin"):
        """
        レビュー処理後にローカルリポジトリをベースブランチの最新状態にクリーンアップします。
        （checkout -> hard reset -> clean -f -d -> pull）
        Go版の Cleanup の責務（次の操作に影響を与えない状態に戻す）を実装します。
        """
        self.logger.info(f"Cleanup: Checking out '{base_branch}' and pulling latest changes...")

        try:
            # 1. ベースブランチにチェックアウト
            #    ローカルにブランチが存在しない場合は作成・追跡設定を行う
            self._run_git_command(['checkout', base_branch])

            # 2. 強制リセット: ローカルの作業ディレクトリをリモートの最新状態に完全に合わせる
            #    これにより、前のレビューで残った可能性のあるローカルの変更（例：マージによる中間状態）を破棄
            base_ref = f'{remote}/{base_branch}'
            self._run_git_command(['reset', '--hard', base_ref])

            # 3. 追跡されていないファイルも完全に削除
            #    ビルド生成物や一時ファイルなども消去し、真にクリーンな状態に
            self._run_git_command(['clean', '-f', '-d'])

            # 4. ベースブランチを pull (最新情報の確実な取得)
            #    fetch のみで比較は可能だが、ローカルブランチを最新にしておくことで次の操作の安全性を確保
            self._run_git_command(['pull', remote, base_branch])

            self.logger.info(f"Cleanup successful: Base branch '{base_branch}' is now clean and up-to-date.")

        except Exception as e:
            # クリーンアップの失敗は、レビューの成功を妨げないが、ログに警告として残す
            self.logger.error(f"Failed to perform Git cleanup (checkout/pull sequence): {e}")
            # エラー発生時の状態を残すため、ここで終了コード1を返さない
