# EDA Report 04: Temporal Dynamics

## 1. Input Density by Match Phase

| Player | 0-25% | 25-50% | 50-75% | 75-100% |
|---|---|---|---|---|
| akira | 402.04 | 306.50 | 412.12 | 385.14 |
| jin | 360.33 | 383.00 | 388.74 | 438.27 |
| keita | 388.02 | 409.05 | 341.08 | 525.76 |
| kotaro | 338.28 | 444.16 | 327.72 | 439.94 |
| nakamura | 510.66 | 560.85 | 469.77 | 371.99 |
| ryo | 417.27 | 383.89 | 329.40 | 447.68 |
| yamaguti | 643.08 | 564.51 | 444.89 | 412.03 |

## 2. Special Flags by char_distance_px

（shoryuken が遠距離で多発 → 誤検知の疑い）

| Distance Range | hadouken_rate% | shoryuken_rate% |
|---|---|---|
| <100 | 0.00 | 0.00 |
| 100-200 | 5.37 | 44.17 |
| 200-300 | 12.73 | 21.30 |
| 300-400 | 3.64 | 11.64 |
| 400-600 | 2.99 | 9.58 |
| 600-1000 | 2.39 | 9.62 |
| >1000 | 0.70 | 3.08 |

## 3. Input Density Timeline (Attack Buttons)

## 4. Shoryuken Detection Validity

- shoryuken=1 の char_distance 中央値: 504.8px
- 300px 以上での発火率: 86.0%
- 0px（キャラ未検出）での発火率: 0.0%

**⚠ 注意: 遠距離（>300px）での shoryuken 発火が 30% 超 → 誤検知の可能性あり**

