"""
対戦ログCSVを読み込み、ボタン入力の折れ線グラフPNGを生成するスクリプト

出力先: 結果/ ディレクトリ（各対戦ごとにPNGを1枚生成）
"""
import csv
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm
import numpy as np

# 日本語フォント設定
for _jp_font in ('Yu Gothic', 'Meiryo', 'MS Gothic', 'BIZ UDGothic'):
    if any(f.name == _jp_font for f in fm.fontManager.ttflist):
        matplotlib.rcParams['font.family'] = _jp_font
        break


BUTTON_COLS = [
    'X', 'Y', 'B', 'A',
    'RB', 'LB', 'RT', 'LT',
    'UpArrow', 'DownArrow', 'LeftArrow', 'RightArrow',
]

BUTTON_COLORS = {
    'X':          '#1565c0',
    'Y':          '#c77700',
    'B':          '#c62828',
    'A':          '#2e7d32',
    'RB':         '#6a1b9a',
    'LB':         '#e65100',
    'RT':         '#00695c',
    'LT':         '#880e4f',
    'UpArrow':    '#37474f',
    'DownArrow':  '#4e342e',
    'LeftArrow':  '#00838f',
    'RightArrow': '#bf360c',
}

BIN_SEC = 2.0


def parse_timestamp(ts: str) -> float:
    """MM:SS.ffffff → 秒数"""
    try:
        mins, secs = ts.split(':')
        return int(mins) * 60 + float(secs)
    except Exception:
        return 0.0


def process_csv(filepath: Path) -> dict[str, dict[str, list[float]]]:
    """ボタン押下タイミング（立ち上がりエッジ）をプレイヤーごとに収集"""
    presses: dict[str, dict[str, list[float]]] = {}
    prev:    dict[str, dict[str, int]]         = {}

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            player = row['username']
            # Timestamp が None、またはユーザー名が英字でない不正行はスキップ
            if not row.get('Timestamp') or not player.isalpha():
                continue
            t = parse_timestamp(row['Timestamp'])

            if player not in presses:
                presses[player] = {b: [] for b in BUTTON_COLS}
                prev[player]    = {b: 0   for b in BUTTON_COLS}

            for btn in BUTTON_COLS:
                val = int(row.get(btn, 0) or 0)
                if val == 1 and prev[player][btn] == 0:
                    presses[player][btn].append(t)
                prev[player][btn] = val

    return presses


def build_bins(presses: dict[str, dict[str, list[float]]]) -> tuple[np.ndarray, int]:
    """全押下時刻の最大値からbinラベルを生成"""
    max_t = 0.0
    for btns in presses.values():
        for times in btns.values():
            if times:
                max_t = max(max_t, max(times))
    num_bins = int(max_t / BIN_SEC) + 1
    bins = np.arange(num_bins) * BIN_SEC
    return bins, num_bins


def counts_for(times: list[float], num_bins: int) -> np.ndarray:
    arr = np.zeros(num_bins, dtype=int)
    for t in times:
        idx = int(t / BIN_SEC)
        if idx < num_bins:
            arr[idx] += 1
    return arr


def save_chart(presses: dict[str, dict[str, list[float]]],
               battle_name: str, out_dir: Path) -> None:
    players = sorted(presses.keys())
    n_players = len(players)
    bins, num_bins = build_bins(presses)

    # 全プレイヤー・全ボタンの最大押下回数を求めてY軸を固定
    global_max = 0
    for btns in presses.values():
        for times in btns.values():
            if times:
                arr = counts_for(times, num_bins)
                global_max = max(global_max, int(arr.max()))
    y_max = max(global_max + 1, 2)

    fig, axes = plt.subplots(
        n_players, 1,
        figsize=(16, 5 * n_players),
        facecolor='white',
        sharex=True,
        squeeze=False,
    )
    # 20260513_jin_akira_1 → "jin vs akira（1戦目）"
    parts = battle_name.replace('20260513_', '').rsplit('_', 1)
    match_num = f'（{parts[1]}戦目）' if len(parts) == 2 and parts[1].isdigit() else ''
    players_str = parts[0].replace('_', ' vs ')
    title = f'ボタン入力 折れ線グラフ\n{players_str}{match_num}'
    fig.suptitle(title, color='black', fontsize=14, y=1.01)

    for row_idx, player in enumerate(players):
        ax = axes[row_idx][0]
        ax.set_facecolor('white')
        ax.set_title(player, color='#222222', fontsize=11, pad=4)
        ax.spines[:].set_color('#bbbbbb')
        ax.tick_params(colors='#333333', labelsize=8)
        ax.yaxis.label.set_color('#333333')
        ax.xaxis.label.set_color('#333333')
        ax.set_ylabel('押下回数', fontsize=9)
        ax.grid(color='#dddddd', linewidth=0.6)

        plotted = False
        for btn in BUTTON_COLS:
            times = presses[player].get(btn, [])
            if not times:
                continue
            arr = counts_for(times, num_bins)
            ax.plot(
                bins, arr,
                label=btn,
                color=BUTTON_COLORS[btn],
                linewidth=1.4,
                alpha=0.85,
            )
            plotted = True

        if plotted:
            ax.legend(
                loc='upper right',
                fontsize=7,
                ncol=2,
                framealpha=0.8,
                labelcolor='#111111',
                facecolor='#f5f5f5',
                edgecolor='#cccccc',
            )
        ax.set_ylim(0, y_max)
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True, nbins=y_max))

    axes[-1][0].set_xlabel('経過時間（秒）', fontsize=9)

    plt.tight_layout()
    out_path = out_dir / f'{battle_name}.png'
    fig.savefig(out_path, dpi=120, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'  保存: {out_path.name}')


def main():
    script_dir = Path(__file__).parent
    csv_dir    = script_dir.parent / '20260513'
    out_dir    = script_dir

    if not csv_dir.exists():
        print(f'CSVディレクトリが見つかりません: {csv_dir}')
        return

    csv_files = sorted(csv_dir.glob('*.csv'))
    print(f'{len(csv_files)} 件のCSVを処理します...\n')

    for csv_file in csv_files:
        print(f'処理中: {csv_file.name}')
        presses = process_csv(csv_file)
        save_chart(presses, csv_file.stem, out_dir)

    print('\n完了。')


if __name__ == '__main__':
    main()
