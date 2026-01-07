import csv
import os

FILE = "output.csv"
FIELDNAMES = ["date", "name", "age"]  # 先にカラム（列）を固定
ROWORIZIN = {col: "" for col in FIELDNAMES}  # まず空で作る
row = {}
def append_row(row: dict):
    file_exists = os.path.exists(FILE)
    file_is_empty = (not file_exists) or (os.path.getsize(FILE) == 0)

    with open(FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)

        # ファイルが無い or 空ならヘッダーを書く
        if file_is_empty:
            writer.writeheader()

        # 1行追加
        writer.writerow(row)

row.update(ROWORIZIN)
row["date"] = "2026-01-07"
row["name"] = "Alice"
row["age"] = 20
# 使い方例
append_row(row)

row.clear()
row.update(ROWORIZIN)

print(row)
append_row(row)


