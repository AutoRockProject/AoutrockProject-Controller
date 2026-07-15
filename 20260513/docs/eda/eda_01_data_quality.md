# EDA Report 01: Data Quality & Overview

## 1. Basic Stats

**Train**
- Shape: 703,672 rows × 38 cols
- Missing values: 0
- Unique players: 7
- Unique source files: 9

**Test**
- Shape: 589,176 rows × 38 cols
- Missing values: 0
- Unique players: 7
- Unique source files: 9

## 2. Special Flag Rates per Player

| Player | hadouken_rate% (tr) | shoryuken_rate% (tr) | hadouken_rate% (te) | shoryuken_rate% (te) |
|---|---|---|---|---|
| akira | 4.70 | 10.86 | 4.00 | 6.93 |
| jin | 3.32 | 10.53 | 2.94 | 7.67 |
| keita | 0.93 | 8.34 | 1.78 | 10.30 |
| kotaro | 3.82 | 9.66 | 2.68 | 9.79 |
| nakamura | 2.94 | 10.15 | 5.22 | 9.86 |
| ryo | 2.22 | 12.61 | 2.89 | 9.15 |
| yamaguti | 2.91 | 10.12 | 5.19 | 9.85 |

## 3. Shoryuken Flag: Consecutive Frame Analysis

（発火フレームが長く続くなら誤検知の可能性が高い）

**Train**
- 発火区間数: 497
- 平均連続フレーム数: 145.84
- 中央値: 135.0
- 最大連続フレーム数: 892
- 1フレームのみ区間の割合: 4.2%

**Test**
- 発火区間数: 389
- 平均連続フレーム数: 136.57
- 中央値: 116.0
- 最大連続フレーム数: 525
- 1フレームのみ区間の割合: 2.8%

## 4. Timestamp Interval Distribution

- 平均間隔: 0.0025s
- 中央値間隔: 0.0006s
- 最大間隔（ギャップ）: 8.8554s
- 1秒以上のギャップ数: 159

## 5. char_distance_px Distribution

- Train ゼロ値率（未検出フレーム）: 8.95%
- Test  ゼロ値率（未検出フレーム）: 7.65%

