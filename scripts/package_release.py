"""Build clearly separated source, private local and private backend-data archives."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from check_distribution import check

ROOT=Path(__file__).resolve().parents[1]


def tree(mapping,base,prefix):
    if not base.is_dir():raise ValueError(f'Required directory missing: {base}')
    for path in sorted(base.rglob('*')):
        if path.is_symlink():raise ValueError(f'Symlink not allowed in distribution: {path}')
        if not path.is_file():continue
        relative=path.relative_to(base)
        if '__pycache__' in relative.parts or path.suffix=='.pyc':continue
        if path.suffix in ('.db','.sqlite','.sqlite3') or path.name=='.env':raise ValueError(f'Credential/cache file rejected: {path.name}')
        mapping[(Path(prefix)/relative).as_posix()]=path


def contents(value):return value.read_bytes() if isinstance(value,Path) else value


def archive(destination,mapping,kind,commit,prefix):
    if destination.exists():raise ValueError(f'Refusing to overwrite existing archive: {destination}')
    manifest=dict(format_version=3,distribution=kind,source_commit=commit,
                  files={name:hashlib.sha256(contents(value)).hexdigest() for name,value in sorted(mapping.items())})
    mapping=dict(mapping);mapping['BUNDLE_MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,value in sorted(mapping.items()):
            target=prefix+'/'+name if prefix else name
            if isinstance(value,Path):z.write(value,target)
            else:z.writestr(target,value)
    with zipfile.ZipFile(destination) as z:
        if z.testzip() is not None:raise ValueError('Archive CRC failure')
        for name,digest in manifest['files'].items():
            target=prefix+'/'+name if prefix else name
            if hashlib.sha256(z.read(target)).hexdigest()!=digest:raise ValueError('Archive checksum failure')
    print(json.dumps(dict(file=str(destination),kind=kind,files=len(mapping),bytes=destination.stat().st_size)),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',default='releases');p.add_argument('--legacy-public',type=Path);p.add_argument('--legacy-cache',type=Path)
    args=p.parse_args()
    for flag in ([],['--cached']):
        if subprocess.run(['git','diff',*flag,'--quiet'],cwd=ROOT).returncode:raise SystemExit('Commit tracked source changes before producing a versioned distribution.')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    names=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    source={name:ROOT/name for name in names}
    for name in source:
        if name.startswith(('data/','model_registry/','imports/','reports/','web/dist','web/public/history/')) or name=='web/public/results.json':raise SystemExit('Private/generated file unexpectedly tracked: '+name)
    required=['START_HERE.md','requirements-local.lock','scripts/run_local.py','scripts/check_distribution.py','scripts/build_vercel.mjs','Dockerfile.backend','render.yaml','vercel.json']
    for name in required:
        if name not in source:raise SystemExit('Required source helper not tracked: '+name)
    local_check=check(ROOT,local=True)
    if not local_check['ok']:raise SystemExit(json.dumps(local_check,indent=2))
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    source_notice=dict(distribution='source',private_data_included=False,model_binaries_included=False,prebuilt_frontend_included=False,
                       note='Source is not the complete private local distribution. See START_HERE.md.')
    source['PACKAGE_CONTENTS.json']=(json.dumps(source_notice,indent=2)+'\n').encode()
    archive(output/'BullBench-Markov-Deployment-Source.zip',source,'source',commit,'BullBench-Markov-Source')
    local={name:value for name,value in source.items() if name!='PACKAGE_CONTENTS.json'}
    tree(local,ROOT/'web/dist','web/dist')
    backend={}
    for name in ('exploratory_snapshots','calendar_evidence','corporate_action_evidence'):
        tree(local,ROOT/'data'/name,'data/'+name);tree(backend,ROOT/'data'/name,name)
    tree(local,ROOT/'model_registry','model_registry');tree(backend,ROOT/'model_registry','model_registry')
    if (ROOT/'data/legacy_site').is_dir():tree(local,ROOT/'data/legacy_site','data/legacy_site')
    legacy=args.legacy_public or ROOT/'web/public'
    if (legacy/'results.json').is_file():
        for prefix in ('web/public','web/dist'):
            local[prefix+'/results.json']=legacy/'results.json'
            tree(local,legacy/'history',prefix+'/history')
    cache=args.legacy_cache or ROOT/'data/legacy_cache'
    if cache.is_dir():
        for path in cache.iterdir():
            if path.is_file() and path.suffix in ('.csv','.json'):local['data/legacy_cache/'+path.name]=path
    local_notice=dict(distribution='complete private local',checks=local_check,
                      prebuilt_frontend_included=True,all_six_model_bundles_included=True,
                      data_directory='data/exploratory_snapshots',legacy_static_included=(legacy/'results.json').is_file(),
                      note='Private owner package. Do not upload data/models/static price history to public Git or Vercel.')
    local['PACKAGE_CONTENTS.json']=(json.dumps(local_notice,indent=2)+'\n').encode()
    backend['BACKEND_DATA_README.txt']=b'PRIVATE BACKEND DATA. Extract these directories directly to the persistent mount /var/data. Source code/image is deployed separately. Never publish this archive or mount it as a public static directory.\n'
    archive(output/'BullBench-Markov-Deployment-Local.zip',local,'private local',commit,'BullBench-Markov-Local')
    archive(output/'BullBench-Markov-Backend-Data-PRIVATE.zip',backend,'private backend data',commit,'')

if __name__=='__main__':main()
