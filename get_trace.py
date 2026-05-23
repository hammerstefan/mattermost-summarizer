import urllib.request
import json
import sys

trace_id = "tr-3dd9a533d0c815a6e49136739abb6fe7"
url = f"http://127.0.0.1:5000/api/2.0/mlflow/traces/get?request_id={trace_id}"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Failed to fetch {url}: {e}")
