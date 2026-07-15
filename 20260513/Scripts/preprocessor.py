"""
Phase 2: CSV前処理・動画特徴量マージ
- StateX/StateY を除外
- Timestamp を float秒に変換
- video_cache の特徴量CSVと merge_asof でマージ
- ファイル末尾 _1 → train, _2 → test に振り分け
"""

import re
import warnings
from pathlib import Path

import pandas as pd

# ---- パス定義 ----------------------------------------------------------------
BASE_DIR  = Path(__file__).parent.parent    # 20260513/
CSV_DIR   = BASE_DIR / "csv_data"
CACHE_DIR = Path(__file__).parent / "video_cache"

# ---- 出力列定義 --------------------------------------------------------------
BUTTON_COLUMNS = [
    "X", "Y", "B", "A", "RB", "LB", "RT", "LT", "RStick", "LStick",
    "SELECT", "START",
    "CenterArrow", "UpArrow", "DownArrow", "LeftArrow", "RightArrow",
    "UpRightArrow", "UpLeftArrow", "DownRightArrow", "DownLeftArrow",
    "Center", "Up", "Down", "Right", "Left",
    "UpRight", "UpLeft", "DownRight", "DownLeft",
]
VIDEO_FEATURE_COLUMNS = ["char_distance_px", "hadouken_flag", "shoryuken_flag"]

MERGE_TOLERANCE_SEC = 0.10  # merge_asof タイムスタンプ許容誤差（秒）

# MM:SS.ffffff 形式のパターン
_TS_PATTERN = re.compile(r"^(\d+):(\d+\.\d+)$")


def _parse_timestamp(ts_str: str) -> float | None:
    """'MM:SS.ffffff' を float秒に変換。パース失敗時は None。"""
    if not isinstance(ts_str, str):
        return None
    m = _TS_PATTERN.match(ts_str.strip())
    if not m:
        return None
    return int(m.group(1)) * 60.0 + float(m.group(2))


class MatchPreprocessor:
    def __init__(
        self,
        csv_dir: Path = CSV_DIR,
        cache_dir: Path = CACHE_DIR,
        merge_tolerance_sec: float = MERGE_TOLERANCE_SEC,
    ):
        self.csv_dir             = csv_dir
        self.cache_dir           = cache_dir
        self.merge_tolerance_sec = merge_tolerance_sec

    # ------------------------------------------------------------------
    # 公開メソッド
    # ------------------------------------------------------------------

    def process_all(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        全CSVファイルを処理し (train_df, test_df) を返す。
        ファイル名末尾 _1 -> train, _2 -> test。
        """
        if not self.csv_dir.exists():
            raise FileNotFoundError(f"CSVディレクトリが見つかりません: {self.csv_dir}")

        csv_files = sorted(self.csv_dir.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"CSVファイルが見つかりません: {self.csv_dir}")

        train_dfs: list[pd.DataFrame] = []
        test_dfs:  list[pd.DataFrame] = []

        for csv_path in csv_files:
            df = self.process_single(csv_path)
            if df is None or df.empty:
                continue

            stem = csv_path.stem
            if stem.endswith("_1"):
                train_dfs.append(df)
            elif stem.endswith("_2"):
                test_dfs.append(df)
            else:
                print(f"[WARN] ファイル名末尾が _1/_2 でないためスキップ: {stem}")

        if not train_dfs:
            raise ValueError("trainデータが1件もありません")

        train_df = pd.concat(train_dfs, ignore_index=True)
        test_df  = pd.concat(test_dfs,  ignore_index=True) if test_dfs else pd.DataFrame()

        print(f"\n前処理完了: train={len(train_df):,} 行, test={len(test_df):,} 行")
        return train_df, test_df

    def process_single(self, csv_path: Path) -> pd.DataFrame | None:
        """単一CSVを処理して DataFrame を返す。キャッシュが存在しない場合は video特徴量を 0 埋め。"""
        print(f"[INFO] 処理中: {csv_path.name}")
        try:
            df = self._load_csv(csv_path)
        except Exception as e:
            print(f"[ERROR] CSV読み込み失敗 ({csv_path.name}): {e}")
            return None

        df = self._parse_timestamps(df)
        if df.empty:
            print(f"[WARN] 有効な行がありません: {csv_path.name}")
            return None

        # video特徴量マージ
        video_df = self._load_video_cache(csv_path.stem)
        if video_df is not None:
            df = self._merge_with_video(df, video_df)
        else:
            for col in VIDEO_FEATURE_COLUMNS:
                df[col] = 0
            print(f"[WARN] 動画キャッシュなし → video特徴量を 0 で埋めます: {csv_path.name}")

        # 試合番号列・ソースファイル列
        df["match_num"]   = int(csv_path.stem[-1]) if csv_path.stem[-1].isdigit() else 0
        df["source_file"] = csv_path.stem

        return df

    # ------------------------------------------------------------------
    # 内部メソッド
    # ------------------------------------------------------------------

    def _load_csv(self, csv_path: Path) -> pd.DataFrame:
        """CSVを読み込み StateX/StateY を除外し、ノイズ行を除去する。"""
        df = pd.read_csv(csv_path, low_memory=False)

        required = {"username", "Timestamp"}
        missing  = required - set(df.columns)
        if missing:
            raise ValueError(f"必須列が不足しています: {missing}")

        # StateX/StateY を除外
        drop_cols = [c for c in ["StateX", "StateY"] if c in df.columns]
        df = df.drop(columns=drop_cols)

        # ノイズ行を除去: username が '0' または数値の行（全ゼロ・全NaNのアーティファクト行）
        before = len(df)
        df = df[~df["username"].astype(str).str.match(r"^\d+$")]
        noise_count = before - len(df)
        if noise_count > 0:
            print(f"[INFO] ノイズ行を除去: {noise_count} 行 (username が数値)")

        return df

    def _parse_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """Timestamp列を timestamp_sec（float秒）に変換。変換失敗行は除外。"""
        df = df.copy()
        df["timestamp_sec"] = df["Timestamp"].apply(_parse_timestamp)

        failed = df["timestamp_sec"].isna().sum()
        if failed > 0:
            print(f"[WARN] Timestamp解析失敗: {failed} 行を除外")
            df = df.dropna(subset=["timestamp_sec"])

        df = df.sort_values("timestamp_sec").reset_index(drop=True)
        return df

    def _load_video_cache(self, csv_stem: str) -> pd.DataFrame | None:
        """対応するキャッシュCSVを読み込む。存在しない場合は None。"""
        cache_path = self.cache_dir / f"{csv_stem}_features.csv"
        if not cache_path.exists():
            return None
        try:
            video_df = pd.read_csv(cache_path)
            video_df = video_df.sort_values("timestamp_sec").reset_index(drop=True)
            return video_df
        except Exception as e:
            print(f"[WARN] キャッシュ読み込み失敗 ({cache_path.name}): {e}")
            return None

    def _merge_with_video(
        self, csv_df: pd.DataFrame, video_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        csv_df と video_df を timestamp_sec で merge_asof（nearest, tolerance付き）。
        マッチしなかった video特徴量列は 0 埋め。
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            merged = pd.merge_asof(
                csv_df,
                video_df[["timestamp_sec"] + VIDEO_FEATURE_COLUMNS],
                on="timestamp_sec",
                direction="nearest",
                tolerance=self.merge_tolerance_sec,
            )

        for col in VIDEO_FEATURE_COLUMNS:
            merged[col] = merged[col].fillna(0).astype(int if col.endswith("flag") else float)

        return merged


# ---- CLI エントリポイント（単体デバッグ用）-----------------------------------

if __name__ == "__main__":
    import sys
    preprocessor = MatchPreprocessor()

    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
        df = preprocessor.process_single(csv_path)
        if df is not None:
            print(df.head())
            print(f"Shape: {df.shape}")
    else:
        train_df, test_df = preprocessor.process_all()
        print("\ntrain.head():")
        print(train_df.head())
        print("\ntest.head():")
        print(test_df.head())
