"""EDA Run-All: 4本のEDAスクリプトを並列実行し、最終レポートを統合する"""
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "output"
OUT_DIR  = BASE_DIR / "docs" / "eda"
SCRIPTS  = [
    "eda_01_data_quality.py",
    "eda_02_button_patterns.py",
    "eda_03_behavioral_features.py",
    "eda_04_temporal.py",
]
SCRIPTS_DIR = Path(__file__).resolve().parent


def run_script(script_name: str) -> tuple[str, int, str, str]:
    script_path = SCRIPTS_DIR / script_name
    result = subprocess.run(
        [sys.executable, str(script_path),
         "--data-dir", str(DATA_DIR),
         "--out-dir",  str(OUT_DIR)],
        capture_output=True, text=True, encoding="utf-8"
    )
    return script_name, result.returncode, result.stdout, result.stderr


def build_summary_report(out_dir: Path):
    """全 EDA markdown を統合した eda_report.md を生成する"""
    sub_reports = [
        "eda_01_data_quality.md",
        "eda_02_button_patterns.md",
        "eda_03_behavioral_features.md",
        "eda_04_temporal.md",
    ]

    sections = [
        "# EDA 総合レポート\n\n",
        "## 概要\n\n",
        "本レポートは `eda_run_all.py` により自動生成された EDA 分析の統合版です。\n\n",
        "- Script 01: データ品質・概要（欠損値・クラスバランス・特殊フラグ）\n",
        "- Script 02: ボタン使用パターン（ヒートマップ・相関）\n",
        "- Script 03: 行動特徴量分布（ANOVA η²・バイオリンプロット）\n",
        "- Script 04: 時系列ダイナミクス（フェーズ分析・距離 vs 特殊技）\n\n",
        "---\n\n",
    ]

    for filename in sub_reports:
        path = out_dir / filename
        if path.exists():
            content = path.read_text(encoding="utf-8")
            sections.append(content)
            sections.append("\n---\n\n")
        else:
            sections.append(f"## ⚠ {filename} not found\n\n---\n\n")

    # Count generated images
    pngs = list(out_dir.glob("*.png"))
    sections.append(f"## 生成画像一覧 ({len(pngs)} 枚)\n\n")
    for png in sorted(pngs):
        sections.append(f"- `{png.name}`\n")
    sections.append("\n")

    report_path = BASE_DIR / "docs" / "eda_report.md"
    report_path.write_text("".join(sections), encoding="utf-8")
    print(f"\n[run_all] Summary report saved: {report_path}")
    return report_path


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[run_all] Data dir : {DATA_DIR}")
    print(f"[run_all] Output   : {OUT_DIR}")
    print(f"[run_all] Scripts  : {len(SCRIPTS)} (running in parallel)\n")

    results = {}
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_script, s): s for s in SCRIPTS}
        for future in as_completed(futures):
            script_name, rc, stdout, stderr = future.result()
            results[script_name] = rc
            if stdout:
                print(stdout.rstrip())
            if rc != 0:
                print(f"[ERROR] {script_name} failed (exit={rc})")
                if stderr:
                    print(stderr[:2000])

    print("\n" + "=" * 50)
    print("[run_all] Script Results:")
    for s, rc in sorted(results.items()):
        status = "OK" if rc == 0 else f"FAILED (rc={rc})"
        print(f"  {s}: {status}")

    report_path = build_summary_report(OUT_DIR)
    pngs = list(OUT_DIR.glob("*.png"))
    print(f"[run_all] Generated {len(pngs)} PNG files in {OUT_DIR}")
    print(f"[run_all] Done. Final report: {report_path}")


if __name__ == "__main__":
    main()
