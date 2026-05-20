import time

# start = time.perf_counter()

def get_ts():
    elapsed = time.perf_counter()
    m = int(elapsed // 60)
    s = int(elapsed % 60)
    us = int((elapsed - int(elapsed)) * 1_000_000)

    return f"{m:02}:{s:02}.{us:06}"

# # 使用例
# time.sleep(0.5)
# print(get_ts())

# time.sleep(1)
print(get_ts())