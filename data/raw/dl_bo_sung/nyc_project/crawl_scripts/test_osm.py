import urllib.request, urllib.parse, json

headers = {'User-Agent': 'Mozilla/5.0 research-bot/1.0'}

# OSM Overpass API - dem so ga subway theo borough
overpass_url = 'https://overpass-api.de/api/interpreter'
nominatim_url = 'https://nominatim.openstreetmap.org/search?q=Manhattan+New+York&format=json&limit=1'

# Test Overpass
query = '[out:json][timeout:25];area[name="Manhattan"][admin_level~"5|6"]->.a;node[station=subway](area.a);out count;'
try:
    data = urllib.parse.urlencode({'data': query}).encode()
    req = urllib.request.Request(overpass_url, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=15) as r:
        body = r.read()
        print(f'OK [OSM Overpass]: {r.status} | {len(body)}b | {body[:200]}')
except Exception as e:
    print(f'FAIL [OSM Overpass]: {e}')

# Test Nominatim
try:
    req = urllib.request.Request(nominatim_url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        body = r.read()
        print(f'OK [Nominatim]: {r.status} | {body[:100]}')
except Exception as e:
    print(f'FAIL [Nominatim]: {e}')
