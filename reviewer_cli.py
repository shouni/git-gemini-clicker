import fire
import sys

class GitGeminiReviewerCLI:
    """
    Python版 Git Gemini Reviewer CLI
    詳細レビュー (detail) と リリースレビュー (release) のためのコマンドを提供します。
    """

    def __init__(self, model: str = "gemini-2.5-flash"):
        # Go版の --model (グローバルフラグ) に相当
        self.model_name = model
        print(f"--- CLI初期化完了 ---")
        print(f"使用モデル: {self.model_name}")
        print("----------------------")


    def _print_diff_info(self, command: str, base_branch: str, feature_branch: str):
        """
        AIレビューの代わりに、引数情報を表示するダミー関数
        """
        print(f"\n--- {command.upper()} モード引数確認 (実装前) ---")
        print(f"レビュー対象フィーチャーブランチ (--feature_branch): {feature_branch}")
        print(f"比較基準ブランチ (--base_branch): {base_branch}")
        print(f"実行コマンド: {command}")
        print(f"グローバルモデル設定: {self.model_name}")
        print("------------------------------------------")


    def detail(self,
               feature_branch: str,                   # 必須引数 (デフォルト値なし)
               base_branch: str = "main",             # オプション引数 (デフォルト値あり)
               mode: str = "detail"):
        """
        [詳細レビュー] コード品質と保守性に焦点を当てたAIレビューを実行します。

        Args:
            feature_branch: レビュー対象のフィーチャーブランチ (例: 'feature/new-feature').
            base_branch: 差分比較の基準ブランチ (例: 'main').
            mode: レビューモード (互換性のため残存しますが、値は 'detail' です).
        """
        # 実際の実装では、ここで diff を取得し、AI APIを呼び出します。
        self._print_diff_info("detail", base_branch, feature_branch)
        return "詳細レビュー処理の骨組み実行が完了しました。"


    def release(self,
                feature_branch: str,                   # 必須引数 (デフォルト値なし)
                base_branch: str = "main",             # オプション引数 (デフォルト値あり)
                mode: str = "release"):
        """
        [リリースレビュー] 本番リリース可否の判定に焦点を当てたAIレビューを実行します。

        Args:
            feature_branch: レビュー対象のフィーチャーブランチ (例: 'release/v1.0').
            base_branch: 差分比較の基準ブランチ (例: 'main').
            mode: レビューモード (互換性のため残存しますが、値は 'release' です).
        """
        # 実際の実装では、ここで diff を取得し、AI APIを呼び出します。
        self._print_diff_info("release", base_branch, feature_branch)
        return "リリースレビュー処理の骨組み実行が完了しました。"


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("実行にはコマンドと必須引数が必要です。ヘルプを表示します。")
        fire.Fire(GitGeminiReviewerCLI, command=['--help'])
    else:
        fire.Fire(GitGeminiReviewerCLI)
