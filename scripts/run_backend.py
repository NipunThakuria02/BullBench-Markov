"""Local development API with explicit private legacy-data access, bound to loopback."""
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT);sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
os.environ['BULLBENCH_LOCAL_LEGACY']='1'
os.environ['BULLBENCH_LEGACY_SITE']=str(ROOT/'data/legacy_site')
os.environ['BULLBENCH_SNAPSHOTS']=str(ROOT/'data/exploratory_snapshots')
os.environ['BULLBENCH_REGISTRY']=str(ROOT/'model_registry')
if __name__=='__main__':
    import uvicorn
    print('Local private legacy results enabled. Open frontend at http://127.0.0.1:5173/')
    uvicorn.run('backend.app.main:app',host='127.0.0.1',port=8000)
