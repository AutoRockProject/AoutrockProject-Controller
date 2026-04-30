import time


# スクリプト読み込み時に記録（＝実質スタート時刻）
START_TIME = time.perf_counter()

def get_ts():
    elapsed = time.perf_counter() - START_TIME
    m = int(elapsed // 60)
    s = int(elapsed % 60)
    us = int((elapsed - int(elapsed)) * 1_000_000)
    return f"{m:02}:{s:02}.{us:06}"


def writets(stop_event):

    with open("timestamp.txt", "w") as f:
        while not stop_event.is_set():
            now = get_ts()

            f.seek(0)
            f.write(now)
            f.truncate()
            f.flush()

            time.sleep(0.016)