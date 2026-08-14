import json

filepath = "D:/nyc_combined_data.json"

with open(filepath, "r", encoding="utf-8") as f:
    data = json.load(f)

new_data = {
    "Manhattan": {
        "Chất_lượng_trường_học_(thang_10)": 7.8,
        "Điểm_thân_thiện_đi_bộ_(Walk_Score)": 89.0,
        "Thuế_bất_động_sản_TB_%": "0.90%"
    },
    "Brooklyn": {
        "Chất_lượng_trường_học_(thang_10)": 6.9,
        "Điểm_thân_thiện_đi_bộ_(Walk_Score)": 74.0,
        "Thuế_bất_động_sản_TB_%": "0.85%"
    },
    "Queens": {
        "Chất_lượng_trường_học_(thang_10)": 7.2,
        "Điểm_thân_thiện_đi_bộ_(Walk_Score)": 65.0,
        "Thuế_bất_động_sản_TB_%": "0.88%"
    },
    "The Bronx": {
        "Chất_lượng_trường_học_(thang_10)": 5.1,
        "Điểm_thân_thiện_đi_bộ_(Walk_Score)": 69.0,
        "Thuế_bất_động_sản_TB_%": "1.05%"
    },
    "Staten Island": {
        "Chất_lượng_trường_học_(thang_10)": 7.4,
        "Điểm_thân_thiện_đi_bộ_(Walk_Score)": 38.0,
        "Thuế_bất_động_sản_TB_%": "0.95%"
    }
}

for b in data:
    name = b["Quận"]
    if name in new_data:
        b.update(new_data[name])

with open(filepath, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("nyc_combined_data.json updated successfully!")
