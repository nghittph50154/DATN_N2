import urllib.request
import urllib.parse
import json
import time

headers = {'User-Agent': 'Mozilla/5.0 NYC-RealEstate-Research/1.0'}
overpass_url = 'https://overpass-api.de/api/interpreter'

boroughs = {
    "Manhattan": "Manhattan",
    "Brooklyn": "Brooklyn",
    "Queens": "Queens",
    "The Bronx": "Bronx",
    "Staten Island": "Staten Island"
}

results = {}

for display_name, search_name in boroughs.items():
    print(f"Fetching McDonald's count for {display_name}...")
    query = f"""
    [out:json][timeout:30];
    area[name="{search_name}"][admin_level~"5|6|7|8"]->.a;
    (
      node["amenity"="fast_food"]["name"~"McDonald's",i](area.a);
      way["amenity"="fast_food"]["name"~"McDonald's",i](area.a);
    );
    out count;
    """
    try:
        data = urllib.parse.urlencode({'data': query}).encode()
        req = urllib.request.Request(overpass_url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read().decode('utf-8')
            resp = json.loads(body)
            # Overpass count query returns a "count" block
            count = resp.get("elements", [{}])[0].get("tags", {}).get("total", 0)
            print(f"  Found {count} McDonald's in {display_name}")
            results[display_name] = int(count)
    except Exception as e:
        print(f"  Error fetching {display_name}: {e}")
        results[display_name] = "Error"
    time.sleep(2) # rate limit politeness

print("\nFinal Results:")
print(json.dumps(results, indent=4, ensure_ascii=False))
