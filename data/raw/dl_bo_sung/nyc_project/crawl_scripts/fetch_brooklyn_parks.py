import urllib.request
import urllib.parse
import json

# Use Kumi Overpass mirror
OVERPASS_URL = 'https://overpass.kumi.systems/api/interpreter'
BOT_HEADERS = {'User-Agent': 'research-bot/1.0'}

# Brooklyn bbox
s, w, n, e = (40.5707, -74.0421, 40.7395, -73.8334)

print("Fetching Brooklyn's parks count using kumi systems Overpass mirror...")

query = f"""[out:json][timeout:35];
(
  node["leisure"="park"]({s},{w},{n},{e});
  way["leisure"="park"]({s},{w},{n},{e});
);
out count;"""

data = urllib.parse.urlencode({'data': query}).encode('utf-8')
req  = urllib.request.Request(OVERPASS_URL, data=data, headers=BOT_HEADERS, method='POST')

try:
    with urllib.request.urlopen(req, timeout=40) as r:
        resp  = json.loads(r.read().decode('utf-8'))
        count = resp['elements'][0]['tags']['total']
        print(f"  [OK] Brooklyn parks count: {count}")
        
        # Read nyc_combined_data.json and update Brooklyn's count
        json_path = "D:/nyc_combined_data.json"
        with open(json_path, "r", encoding="utf-8") as f:
            db = json.load(f)
            
        for item in db:
            if item["Quận"] == "Brooklyn":
                item["Số_công_viên"] = int(count)
                print(f"  Successfully updated D:/nyc_combined_data.json with {count} parks for Brooklyn!")
                
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
            
except Exception as err:
    print(f"  [ERROR]: {err}")
