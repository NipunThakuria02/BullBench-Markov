"""Enable a local exploratory bundle offline; does not certify a research release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def main():
    parser=argparse.ArgumentParser(description='Enable an exploratory bundle locally; official release promotion is not implemented')
    parser.add_argument('--registry',default='model_registry');parser.add_argument('--bundle',required=True)
    parser.add_argument('--exploratory',action='store_true',required=True)
    args=parser.parse_args()
    root=Path(args.registry).resolve();bundle=(root/args.bundle).resolve()
    if not bundle.is_relative_to(root) or bundle==root:parser.error('Bundle must be inside registry')
    raw=(bundle/'manifest.json').read_bytes();m=json.loads(raw)
    if m.get('research_track')!='exploratory' or m.get('final_test_evaluated') is not False:parser.error('Only development exploratory bundles supported')
    from ..ingest.official import ASSETS
    if m.get('asset') not in ASSETS:parser.error('Unsupported asset')
    for name,sha in m['files_sha256'].items():
        p=(bundle/name).resolve()
        if p.parent!=bundle or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:parser.error('Bundle checksum failure')
    pointer=dict(bundle=str(bundle.relative_to(root)),manifest_sha256=hashlib.sha256(raw).hexdigest(),approved=True,approval_scope='local_exploratory_only')
    with NamedTemporaryFile(mode='w',dir=root,delete=False) as f:
        json.dump(pointer,f);temporary=f.name
    os.replace(temporary,root/(m['asset'].replace(' ','_')+'.json'))
    print('Local exploratory bundle enabled. No official release, protocol freeze or final-test approval.')

if __name__=='__main__':main()
