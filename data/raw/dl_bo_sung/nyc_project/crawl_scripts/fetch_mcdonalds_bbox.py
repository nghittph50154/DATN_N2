import urllib.request
import urllib.parse
import json
import time
import sys

# Prevent Unicode issues in standard output
if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError: pass

OVERPASS_URL = 'https://overpass-api.de/api/interpreter'
BOT_HEADERS = {'User-Agent': 'research-bot/1.0'}

# Bounding boxes for NYC boroughs
BOROUGH_BBOX = {
    "Manhattan":     (40.6960, -74.0203, 40.8820, -73.9067),
    "Brooklyn":      (40.5707, -74.0421, 40.7395, -73.8334),
    "Queens":        (40.5431, -73.9625, 40.8007, -73.7004),
    "The Bronx":     (40.7850, -73.9332, 40.9176, -73.7654),
    "Staten Island": (40.4774, -74.2591, 40.6501, -74.0340),
}

results = {}

for boro, (s, w, n, e) in BOROUGH_BBOX.items():
    print(f"Fetching McDonald's count for {boro}...")
    
    # Query nodes and ways with name matching McDonald's
    query = f"""[out:json][timeout:35];
    (
      node["amenity"="fast_food"]["name"~"McDonald's",i]({s},{w},{n},{e});
      way["amenity"="fast_food"]["name"~"McDonald's",i]({s},{w},{n},{e});
    );
    out count;"""
    
    data = urllib.parse.urlencode({'data': query}).encode('utf-8')
    req  = urllib.request.Request(OVERPASS_URL, data=data, headers=BOT_HEADERS, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            resp  = json.loads(r.read().decode('utf-8'))
            count = resp['elements'][0]['tags']['total']
            print(f"  [OK] {boro}: {count} McDonalds")
            results[boro] = int(count)
    except Exception as err:
        print(f"  [ERROR] {boro}: {err}")
        results[boro] = 0
    time.sleep(2)

print("\nFinal BBOX Results:")
print(json.dumps(results, indent=4, ensure_ascii=False))

# Now write back to nyc_combined_data.json
json_path = "D:/nyc_combined_data.json"
try:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for item in data:
        name = item["Quận"]
        key_name = name
        if name == "Bronx":
            key_name = "The Bronx"
        elif name == "The Bronx":
            key_name = "The Bronx"
            
        mcd_count = results.get(key_name, 0)
        item["Số_cửa_hàng_McDonalds"] = mcd_count
        
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print("\nSuccessfully updated nyc_combined_data.json with McDonalds count!")
except Exception as file_err:
    print(f"Error updating JSON: {file_err}")
