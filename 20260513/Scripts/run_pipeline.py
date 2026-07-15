"""
メインパイプライン (Phase 1 → 2 → 3)

使用方法:
    python run_pipeline.py                   # 全フェーズ実行
    python run_pipeline.py --skip-phase1     # Phase1スキップ（キャッシュ使用）
    python run_pipeline.py --force-reprocess # 動画キャッシュを再生成
    python run_pipeline.py --verify          # 出力後に品質確認レポートを表示
"""

import argparse
import time
from pathlib import Path

import pandas as pd

from video_analyzer import VideoFeatureExtractor
from preprocessor import MatchPreprocessor, BUTTON_COLUMNS, VIDEO_FEATURE_COLUMNS

# ---- パス定義 ----------------------------------------------------------------
BASE_DIR   = Path(__file__).parent.parent    # 20260513/
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_COLUMNS = (
    ["username", "Timestamp", "timestamp_sec"]
    + BUTTON_COLUMNS
    + VIDEO_FEATURE_COLUMNS
    + ["match_num", "source_file"]
)


# ---- Phase 1 ----------------------------------------------------------------

def run_phase1(force_reprocess: bool = False) -> dict[str, Path]:
    """動画特徴量を抽出してキャッシュCSVを生成する。"""
    print("=" * 60)
    print("Phase 1: 動画特徴量抽出")
    print("=" * 60)
    t0 = time.time()
    extractor = VideoFeatureExtractor(force_reprocess=force_reprocess)
    results   = extractor.process_all()
    elapsed   = time.time() - t0
    print(f"\nPhase 1 完了: {len(results)} ファイル処理 ({elapsed:.1f}秒)")
    return results


# ---- Phase 2 ----------------------------------------------------------------

def run_phase2() -> tuple[pd.DataFrame, pd.DataFrame]:
    """CSVを前処理し動画特徴量とマージしてtrain/testに分割する。"""
    print("\n" + "=" * 60)
    print("Phase 2: 前処理・特徴量マージ")
    print("=" * 60)
    preprocessor = MatchPreprocessor()
    return preprocessor.process_all()


# ---- Phase 3 ----------------------------------------------------------------

def run_phase3(train_df: pd.DataFrame, test_df: pd.DataFrame) -> None:
    """train/testをoutput/に保存する。"""
    print("\n" + "=" * 60)
    print("Phase 3: データ分割・出力")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 存在する列のみ選択（キャッシュ不在時にvideo列が0埋めの場合でも対応）
    def _select_columns(df: pd.DataFrame) -> pd.DataFrame:
        cols = [c for c in OUTPUT_COLUMNS if c in df.columns]
        return df[cols]

    train_path = OUTPUT_DIR / "train.csv"
    test_path  = OUTPUT_DIR / "test.csv"

    train_out = _select_columns(train_df)
    train_out.to_csv(train_path, index=False)
    print(f"[OK] train.csv: {len(train_out):,} 行 → {train_path}")

    if not test_df.empty:
        test_out = _select_columns(test_df)
        test_out.to_csv(test_path, index=False)
        print(f"[OK] test.csv:  {len(test_out):,} 行 → {test_path}")
    else:
        print("[WARN] testデータが空です。test.csv は生成されません。")


# ---- 品質確認 ----------------------------------------------------------------

def verify_output(
    train_path: Path = OUTPUT_DIR / "train.csv",
    test_path:  Path = OUTPUT_DIR / "test.csv",
) -> None:
    """保存済みCSVを再読込して品質確認レポートを表示する。"""
    print("\n" + "=" * 60)
    print("品質確認レポート")
    print("=" * 60)

    for label, path in [("train", train_path), ("test", test_path)]:
        if not path.exists():
            print(f"[SKIP] {label}.csv が見つかりません")
            continue

        df = pd.read_csv(path)
        size_mb = path.stat().st_size / 1024 / 1024
        print(f"\n--- {label}.csv ({size_mb:.1f} MB) ---")
        print(f"  行数      : {len(df):,}")
        print(f"  列数      : {len(df.columns)}")
        print(f"  ユーザー  : {sorted(df['username'].unique().tolist())}")
        print(f"  StateX含む: {'StateX' in df.columns}")
        print(f"  StateY含む: {'StateY' in df.columns}")

        if "char_distance_px" in df.columns:
            dist = df["char_distance_px"]
            print(f"  char_distance_px: mean={dist.mean():.1f}, min={dist.min():.1f}, max={dist.max():.1f}")
            zero_pct = (dist == 0).mean() * 100
            print(f"    (0の割合: {zero_pct:.1f}% ※高いと検出精度要確認)")

        for flag_col in ["hadouken_flag", "shoryuken_flag"]:
            if flag_col in df.columns:
                rate = df[flag_col].mean() * 100
                print(f"  {flag_col}: 発火率 {rate:.2f}%")

        print(f"  列一覧: {list(df.columns)}")


# ---- メインエントリポイント --------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="対戦データ統合パイプライン")
    parser.add_argument("--force-reprocess", action="store_true",
                        help="動画キャッシュを無視して再処理")
    parser.add_argument("--skip-phase1", action="store_true",
                        help="Phase1をスキップ（既存キャッシュを使用）")
    parser.add_argument("--verify", action="store_true",
                        help="出力後に品質確認レポートを表示")
    args = parser.parse_args()

    t_start = time.time()

    if not args.skip_phase1:
        run_phase1(force_reprocess=args.force_reprocess)

    train_df, test_df = run_phase2()
    run_phase3(train_df, test_df)

    if args.verify:
        verify_output()

    total = time.time() - t_start
    print(f"\n{'=' * 60}")
    print(f"全パイプライン完了 ({total:.1f}秒)")
    print(f"出力先: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
