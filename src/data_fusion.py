import pandas as pd

def fuse_records(student_profiles, swipe_logs, wifi_logs, library_checkouts, cctv_data):
    """
    Example: Merge all logs on student_id, enrich with confidence (simple 1.0 for direct match)
    """
    merged = pd.merge(swipe_logs, wifi_logs, on="student_id", how="outer", suffixes=('_swipe','_wifi'))
    merged = pd.merge(merged, library_checkouts, on="student_id", how="outer")
    merged = pd.merge(merged, cctv_data, on="student_id", how="outer")
    merged['confidence'] = 1.0
    return merged
