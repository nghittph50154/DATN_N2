import urllib.request, urllib.parse, json, io, zipfile

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

tests = [
    # Overpass - thu lai voi header khac nhau
    ('Overpass (no custom CT)', 'POST', 'https://overpass-api.de/api/interpreter',
     '[out:json][timeout:25];node["railway"="station"]["station"="subway"]["name"~"."](40.4774,-74.2591,40.9176,-73.7004);out count;'),
    # Overpass kumi instance
    ('Overpass kumi POST', 'POST', 'https://overpass.kumi.systems/api/interpreter',
     '[out:json][timeout:25];node["railway"="station"]["station"="subway"](40.4774,-74.2591,40.9176,-73.7004);out count;'),
    # Transitland API v1
    ('Transitland stops', 'GET', 'https://transit.land/api/v1/stops?served_by=r-dr5r-nyctsubway&per_page=1&total=true', None),
    # Transitland v2
    ('Transitland v2', 'GET', 'https://transit.land/api/v2/rest/stops?served_by_onestop_ids=r-dr5r-nyctsubway&per_page=1', None),
    # MTA GTFS static feed (alternative URLs)
    ('MTA GTFS direct', 'GET', 'https://rrgtfsfeeds.s3.amazonaws.com/gtfs_supplemented.zip', None),
    # Wikipedia API - MTA subway stations count
    ('Wikipedia API', 'GET', 'https://en.wikipedia.org/api/rest_v1/page/summary/New_York_City_Subway', None),
]

for name, method, url, query in tests:
    try:
        if method == 'POST' and query:
            data = urllib.parse.urlencode({'data': query}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'User-Agent': 'research-bot/1.0'}, method='POST')
        else:
            req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as r:
            body = r.read()
            print(f'OK   [{name}]: {r.status} | {len(body):,}b | {str(body[:80])}')
    except Exception as e:
        print(f'FAIL [{name}]: {str(e)[:90]}')
