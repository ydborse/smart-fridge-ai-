import urllib.request
import json

url = 'https://datasets-server.huggingface.co/parquet?dataset=Densu341/Fresh-rotten-fruit'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        for item in data.get('parquet_files', []):
            mb = item['size'] / (1024 * 1024)
            print(f"Split: {item['split']} | Size: {mb:.2f} MB | Rows: {item.get('num_rows')} | URL: {item['url']}")
except Exception as e:
    print('Error:', e)
