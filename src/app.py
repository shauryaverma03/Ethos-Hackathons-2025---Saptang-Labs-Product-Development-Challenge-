import streamlit as st
import pandas as pd
from entity_resolution import resolve_entities
from data_fusion import fuse_records
from timeline_generator import generate_timeline

st.title("Ethos: Campus Entity Resolution & Security Monitoring")

# Load data
student_profiles = pd.read_csv("../data/student_profiles.csv")
swipe_logs = pd.read_csv("../data/swipe_logs.csv")
wifi_logs = pd.read_csv("../data/wifi_logs.csv")
library_checkouts = pd.read_csv("../data/library_checkouts.csv")
cctv_data = pd.read_csv("../data/cctv_data.csv")

# Entity resolution
swipe_logs, wifi_logs = resolve_entities(student_profiles, swipe_logs, wifi_logs)

# Fusion
merged = fuse_records(student_profiles, swipe_logs, wifi_logs, library_checkouts, cctv_data)

# UI
student_id = st.selectbox("Select Student ID", student_profiles['student_id'])
timeline = generate_timeline(merged, student_id)
st.write("Timeline of activities:", timeline)
