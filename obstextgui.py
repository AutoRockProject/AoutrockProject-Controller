import obspython as obs
import time
import os

source_name = "Timestamp"
START_TIME_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "start_time.txt")

START_TIME = None
_last_mtime = None


def get_ts():
    if START_TIME is None:
        return "00:00.000000"
    elapsed = time.time() - START_TIME
    m = int(elapsed // 60)
    s = int(elapsed % 60)
    us = int((elapsed - int(elapsed)) * 1_000_000)
    return f"{m:02}:{s:02}.{us:06}"

def update_text():
    global START_TIME, _last_mtime

    # start_time.txt が更新されたときだけ読み直す
    try:
        mtime = os.path.getmtime(START_TIME_FILE)
        if mtime != _last_mtime:
            with open(START_TIME_FILE, "r") as f:
                START_TIME = float(f.read())
            _last_mtime = mtime
    except:
        return

    if START_TIME is None:
        return

    text = get_ts()

    source = obs.obs_get_source_by_name(source_name)
    if source is not None:
        print("kakikomi")
        settings = obs.obs_data_create()
        obs.obs_data_set_string(settings, "text", text)
        obs.obs_source_update(source, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source)


def script_load(settings):
    print("kidou")
    obs.timer_add(update_text, 16)


def script_unload():
    obs.timer_remove(update_text)


