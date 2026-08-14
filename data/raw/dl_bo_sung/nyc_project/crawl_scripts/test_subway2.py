import urllib.request, urllib.parse, json, io, zipfile, csv

headers_browser = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
headers_bot     = {'User-Agent': 'research-bot/1.0'}

tests = [
    # Overpass bbox toàn NYC, không theo admin area (đơn giản hơn)
    ('Overpass bbox (no CT)', 'POST', 'https://overpass-api.de/api/interpreter',
     '[out:json][timeout:25];node["railway"="station"]["station"="subway"](40.4774,-74.2591,40.9176,-73.7004);out count;'),
    # Overpass kumi instance
    ('Overpass kumi bbox',    'POST', 'https://overpass.kumi.systems/api/interpreter',
     '[out:json][timeout:25];node["railway"="station"]["station"="subway"](40.4774,-74.2591,40.9176,-73.7004);out count;'),
    # Transitland v1
    ('Transitland v1', 'GET',
     'https://transit.land/api/v1/stops?served_by=r-dr5r-nyctsubway&per_page=1&total=true', None),
    # NYC GIS REST API (alternative to NYC Open Data)
    ('NYC GIS subway', 'GET',
     'https://data.cityofnewyork.us/resource/arq3-7z49.json?$limit=1', None),
    # GitHub - MTA GTFS stops.txt (cached/partial)
    ('GitHub MTA stops', 'GET',
     'https://raw.githubusercontent.com/nicholasmartino/city-scraper/master/data/nyc/subway_stations.geojson', None),
]

for name, method, url, query in tests:
    try:
        if method == 'POST' and query:
            data = urllib.parse.urlencode({'data': query}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers_bot, method='POST')
        else:
            req = urllib.request.Request(url, headers=headers_browser)
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read()
            print(f'OK   [{name}]: {r.status} | {len(body):,}b | {str(body[:80])}')
    except Exception as e:
        print(f'FAIL [{name}]: {str(e)[:90]}')
