import subprocess
import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Union
import stat
import urllib.parse


# 注意: core.pyやcli.py側で設定する方が望ましいですが、ここでは暫定的に設定
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- Custom Exceptions for better error handling ---
class GitClientError(Exception):
    """GitClient関連のエラーベースクラス。"""
    pass

class GitCommandError(GitClientError):
    """Gitコマンドの実行失敗時に送出されるエラー。"""
    def __init__(self, message: str, stderr: str = ""):
        super().__init__(message)
        self.stderr = stderr
        logging.error(f"{message}\nstderr: {stderr.strip()}")

class BranchNotFoundError(GitClientError):
    """指定されたブランチがリポジトリに見つからない時に送出されるエラー。"""
    pass

# --- GitClient Implementation ---

class GitClient:
    """
    Go版のロジックに基づき、Gitリポジトリを操作するためのクライアントクラス。
    リポジトリの存在チェック、URL不一致時の自動再クローン機能を提供します。
    """

    def __init__(self,
                 repo_url: str,
                 repo_path: str,
                 ssh_key_path: Optional[str] = None,
                 skip_host_key_check: bool = False):

        self.repo_url = repo_url
        self.repo_path = Path(repo_path).resolve()
        self.ssh_key_path = ssh_key_path
        self.skip_host_key_check = skip_host_key_check

        # SSHキーパスの設定を試みる
        if self.ssh_key_path:
            self._setup_ssh_command()

        # 既存の __init__ のチェックロジックを置き換え、URLチェックと再クローンを実行
        self.clone_or_open()


    def _setup_ssh_command(self):
        """Go版の getGitSSHCommand に相当: GIT_SSH_COMMAND 環境変数を設定する。"""
        ssh_key_path = os.path.expanduser(self.ssh_key_path)

        if not Path(ssh_key_path).is_file():
            logging.warning(f"Warning: SSHキーファイルが見つかりません: {ssh_key_path}. SSH認証は機能しない可能性があります。")
            return

        # ssh -i <鍵のパス> -o StrictHostKeyChecking=no の形式で設定
        ssh_command = f'ssh -i {ssh_key_path}'

        if self.skip_host_key_check:
            # Go版の InsecureSkipHostKeyCheck に対応
            ssh_command += " -o StrictHostKeyChecking=no"
            logging.warning("CRITICAL WARNING: Setting StrictHostKeyChecking=no for GIT_SSH_COMMAND.")

        os.environ['GIT_SSH_COMMAND'] = ssh_command
        logging.info(f"Setting GIT_SSH_COMMAND for SSH authentication.")


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
            # git config --get remote.origin.url を実行
            result = self._run_git_command(['config', '--get', f'remote.{remote}.url'], check=False, ignore_errors=True)
            if result.returncode != 0:
                return None
            return result.stdout.strip()
        except Exception:
            return None


    def _remove_and_clone(self, url: str):
        """Go版と同様に、既存のディレクトリを削除し、指定されたURLで新しくクローンします。"""
        if self.repo_path.exists():
            logging.info(f"Removing old repository directory {self.repo_path}...")
            try:
                # 権限問題を避けるために、エラーを無視して削除を試みる
                shutil.rmtree(self.repo_path, ignore_errors=True)
            except Exception as e:
                raise GitClientError(f"Failed to remove old repository directory: {e}")

        logging.info(f"Cloning {url} into {self.repo_path}...")

        # クローン先ディレクトリの親ディレクトリが存在しない場合は作成
        self.repo_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # git clone <url> <local_path> コマンドを self.repo_path の親ディレクトリで実行
            # Go版と異なり、ブランチは指定せずに全ブランチを取得し、Fetchで最新化する方が確実
            self._run_git_command(['clone', url, self.repo_path.name], check=True, cwd=self.repo_path.parent)
        except GitCommandError as e:
            raise GitClientError(f"Failed to clone repository {url}. Check URL and SSH key/access permissions: {e.stderr}")


    def clone_or_open(self):
        """
        リポジトリをクローンするか、既存のものを開きます。
        Go版と同様に、URLが不一致の場合は自動的に再クローンします。
        """
        is_git_repo = self.repo_path.is_dir() and (self.repo_path / '.git').is_dir()

        if not is_git_repo:
            # 1. リポジトリが存在しない、または壊れている場合は単純にクローン
            self._remove_and_clone(self.repo_url)
            print(f"--- ✅ リポジトリをクローンしました: {self.repo_path} ---")
            return

        # 2. 既存リポジトリを開く
        logging.info(f"Opening repository at {self.repo_path}...")
        existing_url = self._get_remote_url()

        if not existing_url:
            # リモート'origin'がない場合は再クローン
            logging.warning("Warning: Remote 'origin' not found. Re-cloning...")
            self._remove_and_clone(self.repo_url)
            print(f"--- ✅ リモート設定不一致のため再クローンしました: {self.repo_path} ---")
            return

        # 3. URLチェック (Go版の正規化をエミュレート: 末尾のスラッシュやURIエンコードの違いを無視)
        def normalize_url(u: str) -> str:
            """比較のためのURLを正規化"""
            u = u.strip().rstrip('/')
            # SSH URL (git@...) の場合、go-gitの動作に近づけるため、特に処理は加えない
            if not u.startswith('git@') and '://' in u:
                try:
                    parsed = urllib.parse.urlparse(u)
                    # ユーザー情報を削除し、パスも正規化
                    return parsed._replace(netloc=parsed.netloc.split('@')[-1], path=parsed.path).geturl().lower()
                except:
                    pass
            return u.lower()

        normalized_existing_url = normalize_url(existing_url)
        normalized_target_url = normalize_url(self.repo_url)

        if normalized_existing_url != normalized_target_url:
            # URLが一致しない場合、削除して再クローン
            logging.warning(
                f"Warning: Existing URL ({existing_url}) does not match requested URL ({self.repo_url}). Re-cloning..."
            )
            self._remove_and_clone(self.repo_url)
            print(f"--- ✅ URL不一致のため再クローンしました: {self.repo_path} ---")
        else:
            # URLが一致する場合は、そのまま利用
            logging.info("Repository URL matches. Using existing local repository.")
            print(f"--- ✅ 既存リポジトリを利用します: {self.repo_path} ---")

        # 既存リポジトリのパーミッションを設定（Go版の権限処理をエミュレート）
        # サブプロセスとして git コマンドを実行するだけなので、通常は不要だが、Go版の堅牢性を意識
        os.chmod(self.repo_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)


    def fetch_updates(self, remote: str = "origin") -> None:
        """Go版の Fetch に相当: リモートリポジトリの最新情報を取得します。"""
        print(f"'{self.repo_path.name}' のリモート情報を更新中 (git fetch)...")
        # --prune を付けて、リモートで削除されたブランチをローカルから削除
        self._run_git_command(['fetch', remote, '--prune'])
        print(f"--- ✅ リモート情報の更新が完了しました ---")


    def _remote_branch_exists(self, ref_name: str) -> bool:
        """Go版の _remote_branch_exists に相当: 指定されたリファレンスが存在するかをチェックします。"""
        # git show-ref --verify <ref> を使用
        result = self._run_git_command(
            ['show-ref', '--verify', ref_name],
            check=False,
            ignore_errors=True
        )
        return result.returncode == 0

    def get_diff(self, base_branch: str, feature_branch: str, remote: str = "origin") -> str:
        """
        Go版の GetCodeDiff に相当: 指定された2つのリモートブランチ間の「純粋な差分」（3点比較）を取得します。

        Args:
            base_branch (str): 比較の基準となるブランチ名（例: 'main'）。
            feature_branch (str): 比較対象のブランチ名（例: 'develop'）。
            remote (str): リモート名（デフォルトは 'origin'）。

        Returns:
            str: git diffの出力結果。

        Raises:
            BranchNotFoundError, GitCommandError
        """
        # 1. リモートの最新情報を取得（Go版と同様に最初に実行）
        self.fetch_updates(remote)

        # リファレンス名を構築
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

        # 3. マージベースの特定 (Go版の MergeBase に相当)
        # git merge-base <base> <feature> を実行して、共通の祖先コミットSHAを取得
        print(f"マージベースを計算中: {base_ref} と {feature_ref}")

        merge_base_result = self._run_git_command(
            ['merge-base', base_ref, feature_ref],
            check=True
        )
        merge_base_sha = merge_base_result.stdout.strip()

        if not merge_base_sha:
            raise GitClientError(f"エラー: {base_ref} と {feature_ref} の間に共通の祖先コミット（マージベース）が見つかりませんでした。")

        # 4. 3点比較による diff を実行 (Go版の patch.String() に相当)
        # git diff <MergeBase> <feature>
        print(f"差分を取得中: {merge_base_sha}...{feature_ref}")
        diff_command = [
            'diff',
            f'{merge_base_sha}',
            feature_ref,
            '--unified=10' # Go版の例に合わせてコンテキストを10行に設定
        ]
        result = self._run_git_command(diff_command)

        # 差分取得が完了したことを示すメッセージを追加
        print(f"--- ✅ 純粋な差分（3点比較）の取得が完了しました ---")

        return result.stdout
