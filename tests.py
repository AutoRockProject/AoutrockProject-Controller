import obspython as obs

source_name = "Timestamp"

def update_text(text):
    source = obs.obs_get_source_by_name(source_name)
    if source is not None:
        settings = obs.obs_data_create()
        obs.obs_data_set_string(settings, "text", text)
        obs.obs_source_update(source, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source)

def on_event(event):
    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED:
        update_text("録画開始！")
    elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        update_text("録画停止")

def script_load(settings):
    obs.obs_frontend_add_event_callback(on_event)

def script_unload():
    obs.obs_frontend_remove_event_callback(on_event)