import pandas as pd
df = pd.read_csv("D:/code/Data/Dulieu_Cleaned_v2.csv", nrows=5)
print("Columns in dataset:")
print(df.columns.tolist())
print("\nSample row:")
print(df.iloc[0].to_dict())
