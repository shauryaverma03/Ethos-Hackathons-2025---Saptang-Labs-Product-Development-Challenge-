import pandas as pd

def generate_timeline(merged_records, student_id):
    """
    Example: Create a sorted timeline for a student.
    """
    events = []
    if 'timestamp_swipe' in merged_records.columns:
        events += list(merged_records.loc[merged_records['student_id'] == student_id, ['timestamp_swipe']].dropna().values.flatten())
    if 'timestamp_wifi' in merged_records.columns:
        events += list(merged_records.loc[merged_records['student_id'] == student_id, ['timestamp_wifi']].dropna().values.flatten())
    events = sorted(events)
    return events
