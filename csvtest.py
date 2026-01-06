import csv

rows = [
    ["name", "age"],   # ヘッダー（列名）
    ["Alice", 20],
    ["Bob", 25],
]

with open("output.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print("output.csv を作ったよ！")
