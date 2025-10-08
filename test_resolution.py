import pandas as pd
from core.entity_resolution import EntityResolver

# Load data
student_profiles = pd.read_csv('data/student_profiles.csv')
swipe_logs = pd.read_csv('data/swipe_logs.csv')
wifi_logs = pd.read_csv('data/wifi_logs.csv')
library_logs = pd.read_csv('data/library_checkouts.csv')
cctv_data = pd.read_csv('data/cctv_data.csv')

print("=== Data Loaded ===")
print(f"Students: {len(student_profiles)}")
print(f"Swipe logs: {len(swipe_logs)}")
print(f"WiFi logs: {len(wifi_logs)}")
print(f"Library logs: {len(library_logs)}")
print(f"CCTV data: {len(cctv_data)}")

# Initialize resolver
resolver = EntityResolver(student_profiles)

print("\n=== ID Map ===")
print(resolver.id_map)

# Resolve entities
resolved = resolver.resolve_multiple_sources(swipe_logs, wifi_logs, library_logs, cctv_data)

print("\n=== Resolved Swipe Logs ===")
print(resolved['swipe_logs'])

print("\n=== Resolved WiFi Logs ===")
print(resolved['wifi_logs'])

print("\n=== Resolved Library Logs ===")
print(resolved['library_logs'])

print("\n=== Resolved CCTV Data ===")
print(resolved['cctv_data'])

# Test entity search
test_ids = ['CID101', 'DEV102', 'FID103', 'ananya@campus.edu']
print("\n=== Entity Resolution Test ===")
for identifier in test_ids:
    student_id, confidence = resolver.resolve_entity(identifier)
    print(f"{identifier} -> {student_id} (confidence: {confidence})")
