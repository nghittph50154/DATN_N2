import urllib.request, urllib.parse, json, time

# Bounding boxes từng quận NYC (lat_min, lon_min, lat_max, lon_max)
BOROUGH_BBOX = {
    "Manhattan":     (40.6960, -74.0203, 40.8820, -73.9067),
    "Brooklyn":      (40.5707, -74.0421, 40.7395, -73.8334),
    "Queens":        (40.5431, -73.9625, 40.8007, -73.7004),
    "The Bronx":     (40.7850, -73.9332, 40.9176, -73.7654),
    "Staten Island": (40.4774, -74.2591, 40.6501, -74.0340),
}

OVERPASS_URL = 'https://overpass-api.de/api/interpreter'
# Lưu ý: KHÔNG set Content-Type thủ công!
BOT_HEADERS = {'User-Agent': 'research-bot/1.0'}

for boro, (s, w, n, e) in BOROUGH_BBOX.items():
    query = f'[out:json][timeout:30];node["railway"="station"]["station"="subway"]({s},{w},{n},{e});out count;'
    data = urllib.parse.urlencode({'data': query}).encode('utf-8')
    req  = urllib.request.Request(OVERPASS_URL, data=data, headers=BOT_HEADERS, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            resp  = json.loads(r.read())
            count = resp['elements'][0]['tags']['total']
            print(f'✅ {boro}: {count} ga tàu điện ngầm')
    except Exception as e:
        print(f'❌ {boro}: {e}')
    time.sleep(2)
