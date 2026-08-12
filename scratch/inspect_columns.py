import pandas as pd
df = pd.read_csv("data/Data crawl/Crawl_data_NYC.csv", nrows=1)
print("Columns in Crawl_data_NYC.csv:")
for c in df.columns:
    print(f"  '{c}'")
