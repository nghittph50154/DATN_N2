import pandas as pd
import glob
import os

print("=== INSPECTING CSV FILES ===")
files = glob.glob("data/**/*.csv", recursive=True)
for f in files:
    try:
        df = pd.read_csv(f, nrows=5)
        # Get shape
        # Since we only read 5 rows, we need to get length separately or read full file if it's not too huge
        full_df = pd.read_csv(f)
        print(f"File: {f}")
        print(f"  Shape: {full_df.shape}")
        print(f"  Columns: {list(full_df.columns)[:5]} ... ({len(full_df.columns)} total)")
    except Exception as e:
        print(f"Error reading {f}: {e}")
