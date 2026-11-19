"""Prepare exact-origin CSP for a separate API; does not deploy anything."""
import argparse,json
from pathlib import Path
from urllib.parse import urlsplit
p=argparse.ArgumentParser();p.add_argument('origin');args=p.parse_args()
u=urlsplit(args.origin)
if u.scheme!='https' or not u.hostname or u.username or u.password or u.path not in ('','/') or u.query or u.fragment:p.error('Supply a bare public HTTPS API origin')
origin=f'https://{u.netloc}'
path=Path(__file__).resolve().parents[1]/'vercel.json';config=json.loads(path.read_text())
for rule in config['headers']:
 for header in rule['headers']:
  if header['key']=='Content-Security-Policy':
   header['value']='; '.join("connect-src 'self' "+origin if item.strip().startswith('connect-src ') else item.strip() for item in header['value'].split(';'))
path.write_text(json.dumps(config,indent=2)+'\n')
print('Exact API origin configured for CSP. Set VITE_API_BASE_URL to the same origin when building; set BULLBENCH_CORS_ORIGINS to the frontend origin on the backend.')
