import subprocess
import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional
import urllib.parse


# ロギング設定: ライブラリのデフォルトロガーを設定
git_client_logger = logging.getLogger(__name__)
git_client_logger.addHandler(logging.NullHandler())

# --- Custom Exceptions for better error handling ---
class GitClientError(Exception):
    """GitClient関連のエラーベースクラス。"""
    pass

class GitCommandError(GitClientError):
    """Gitコマンドの実行失敗時に送出されるエラー。"""
    def __init__(self, message: str, stderr: str = ""):
        super().__init__(message)
        self.stderr = stderr
        git_client_logger.error(f"{message}\nstderr: {stderr.strip()}") # logger を使用

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

        self.logger = logging.getLogger(__name__) # インスタンス内でロガーを使用

        self.repo_url = repo_url
        self.repo_path = Path(repo_path).resolve()
        self.ssh_key_path = ssh_key_path
        self.skip_host_key_check = skip_host_key_check

        # SSHキーパスの設定を試みる
        if self.ssh_key_path:
            self._setup_ssh_command()

        # URLチェックと再クローンを実行
        self.clone_or_open()


    def _setup_ssh_command(self):
        """Go版の getGitSSHCommand に相当: GIT_SSH_COMMAND 環境変数を設定する。"""
        ssh_key_path = os.path.expanduser(self.ssh_key_path)

        if not Path(ssh_key_path).is_file():
            self.logger.warning(f"Warning: SSHキーファイルが見つかりません: {ssh_key_path}. SSH認証は機能しない可能性があります。")
            return

        ssh_command = f'ssh -i {ssh_key_path}'

        if self.skip_host_key_check:
            ssh_command += " -o StrictHostKeyChecking=no"
            self.logger.warning("CRITICAL WARNING: Setting StrictHostKeyChecking=no for GIT_SSH_COMMAND.")

        os.environ['GIT_SSH_COMMAND'] = ssh_command
        self.logger.info(f"Setting GIT_SSH_COMMAND for SSH authentication.")


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
            result = subprocess.run(
                ['git'] + command,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False, # エラーハンドリングを自前で行うためFalse
                encoding='utf-8'
            )

            if result.returncode != 0 and check and not ignore_errors:
                raise GitCommandError(
                    f"Gitコマンド '{' '.join(command)}' の実行に失敗しました (Exit Code: {result.returncode})",
                    stderr=result.stderr
                )
            return result

        except FileNotFoundError:
            raise GitCommandError("'git' コマンドが見つかりません。Gitがインストールされ、PATHが通っているか確認してください。")
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

        # クローン先ディレクトリの親ディレクトリが存在しない場合は作成
        self.repo_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._run_git_command(['clone', url, self.repo_path.name], check=True, cwd=self.repo_path.parent)
        except GitCommandError as e:
            raise GitClientError(f"Failed to clone repository {url}. Check URL and SSH key/access permissions: {e.stderr}")


    def clone_or_open(self):
        """
        リポジトリをクローンするか、既存のものを開きます。URLが不一致の場合は自動的に再クローンします。
        """
        is_git_repo = self.repo_path.is_dir() and (self.repo_path / '.git').is_dir()

        if not is_git_repo:
            # 1. リポジトリが存在しない、または壊れている場合は単純にクローン
            self._remove_and_clone(self.repo_url)
            self.logger.info(f"--- ✅ リポジトリをクローンしました: {self.repo_path} ---")
            return

        # 2. 既存リポジトリを開く
        self.logger.info(f"Opening repository at {self.repo_path}...")
        existing_url = self._get_remote_url()

        if not existing_url:
            # リモート'origin'がない場合は再クローン
            self.logger.warning("Warning: Remote 'origin' not found. Re-cloning...")
            self._remove_and_clone(self.repo_url)
            self.logger.info(f"--- ✅ リモート設定不一致のため再クローンしました: {self.repo_path} ---")
            return

        # 3. URLチェック
        def normalize_url(u: str) -> str:
            """比較のためのURLを正規化"""
            u = u.strip().rstrip('/')
            if not u.startswith('git@') and '://' in u:
                try:
                    parsed = urllib.parse.urlparse(u)
                    return parsed._replace(netloc=parsed.netloc.split('@')[-1], path=parsed.path).geturl().lower()
                except:
                    pass
            return u.lower()

        normalized_existing_url = normalize_url(existing_url)
        normalized_target_url = normalize_url(self.repo_url)

        if normalized_existing_url != normalized_target_url:
            # URLが一致しない場合、削除して再クローン
            self.logger.warning(
                f"Warning: Existing URL ({existing_url}) does not match requested URL ({self.repo_url}). Re-cloning..."
            )
            self._remove_and_clone(self.repo_url)
            self.logger.info(f"--- ✅ URL不一致のため再クローンしました: {self.repo_path} ---")
        else:
            # URLが一致する場合は、そのまま利用
            self.logger.info("Repository URL matches. Using existing local repository.")
            self.logger.info(f"--- ✅ 既存リポジトリを利用します: {self.repo_path} ---")


    def fetch_updates(self, remote: str = "origin") -> None:
        """リモートリポジトリの最新情報を取得します。"""
        self.logger.info(f"'{self.repo_path.name}' のリモート情報を更新中 (git fetch)...")
        self._run_git_command(['fetch', remote, '--prune'])
        self.logger.info(f"--- ✅ リモート情報の更新が完了しました ---")


    def _remote_branch_exists(self, ref_name: str) -> bool:
        """指定されたリファレンスが存在するかをチェックします。"""
        result = self._run_git_command(
            ['show-ref', '--verify', ref_name],
            check=False,
            ignore_errors=True
        )
        return result.returncode == 0

    def get_diff(self, base_branch: str, feature_branch: str, remote: str = "origin") -> str:
        """
        指定された2つのリモートブランチ間の「純粋な差分」（3点比較）を取得します。
        """
        # 1. リモートの最新情報を取得
        self.fetch_updates(remote)

        base_ref = f'refs/remotes/{remote}/{base_branch}'
        feature_ref = f'refs/remotes/{remote}/{feature_branch}'

        # 2. 両方のブランチの存在をチェック
        missing_branches = []
        if not self._remote_branch_exists(base_ref):
            missing_branches.append(f"{remote}/{base_branch} ({base_ref})")
        if not self._remote_branch_exists(feature_ref):
            missing_branches.append(f"{remote}/{feature_branch} ({feature_ref})")

        if missing_branches:
            raise BranchNotFoundError(f"ブランチが存在しません: {', '.join(missing_branches)}")

        # 3. マージベースの特定
        self.logger.info(f"マージベースを計算中: {base_ref} と {feature_ref}")

        merge_base_result = self._run_git_command(
            ['merge-base', base_ref, feature_ref],
            check=True
        )
        merge_base_sha = merge_base_result.stdout.strip()

        if not merge_base_sha:
            raise GitClientError(f"エラー: {base_ref} と {feature_ref} の間に共通の祖先コミット（マージベース）が見つかりませんでした。")

        # 4. 3点比較による diff を実行 (git diff <MergeBase> <feature>)
        self.logger.info(f"差分を取得中: {merge_base_sha}...{feature_ref}")
        diff_command = [
            'diff',
            f'{merge_base_sha}',
            feature_ref,
            '--unified=10'
        ]
        result = self._run_git_command(diff_command)

        self.logger.info(f"--- ✅ 純粋な差分（3点比較）の取得が完了しました ---")

        return result.stdout
