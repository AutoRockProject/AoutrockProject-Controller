"""
特定の動作を行うスクリプト(仮バージョン)

本来はここに「顔認証」「パスワード入力」などの実際の判定処理が入る想定。
今回は「確実に成功する(確実に開錠する)処理」として、常に成功を返すようにしてある。

やっていること:
1. 特定の動作を実行する(今は仮の処理。常に成功する)
2. 成功した場合のみ、送信専用スクリプト(sender.py)を呼び出して unlock を送信させる
"""

import subprocess
import sys

# --- 1. ここに本来は実際の動作処理が入る(今回は常に成功) ---
print("[動作] 処理を実行しています...")
print("[動作] 処理が完了しました")

is_correct = True  # 常に成功(仮)。実際の判定条件が決まったらここを差し替える

# --- 2. 成功した場合のみ、sender.py を呼び出して送信させる ---
if is_correct:
    print("[結果] 正しく完了したので、sender.py を実行します")
    # "python" ではなく sys.executable を使うことで、
    # 今このスクリプトを動かしているのと同じPython(同じ.venv)で
    # sender.py を実行することを保証する
    subprocess.run([sys.executable, "SendWin\sender.py"])
else:
    print("[結果] 処理に失敗したので、sender.py は実行しません")
    sys.exit(1)
