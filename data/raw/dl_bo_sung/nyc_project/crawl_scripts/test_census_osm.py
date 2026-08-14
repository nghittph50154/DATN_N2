import urllib.request, urllib.parse, json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

tests = [
    # Census Reporter - no API key needed, wraps Census data
    ('Census Reporter Manhattan', 'https://api.censusreporter.org/1.0/data/show/latest?table_ids=B19083,B17001,B25003,B05002,B15003,B08303&geo_ids=05000US36061,05000US36047,05000US36081,05000US36005,05000US36085'),
    # OSM Overpass via GET (not POST)
    ('OSM Overpass GET', 'https://overpass-api.de/api/interpreter?data=[out:json];area[name="New+York+County"][admin_level=6]->.a;node[station=subway](area.a);out+count;'),
    # Overpass via different instance
    ('Overpass kumi', 'https://overpass.kumi.systems/api/interpreter?data=[out:json];rel["name"="New York City Subway"]; out tags;'),
]

for name, url in tests:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read()
            print(f'OK [{name}]: {r.status} | {len(body):,}b | {str(body[:120])}')
    except Exception as e:
        print(f'FAIL [{name}]: {str(e)[:100]}')
