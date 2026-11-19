"""Read-only validation by default; --commit explicitly writes a local snapshot."""
import argparse
import json

from .official import ASSETS, FORMATS
from .snapshot import prepare_snapshot, save_snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description='Validate a manually obtained official export; never download or train.')
    parser.add_argument('--file', required=True)
    parser.add_argument('--format', required=True, choices=FORMATS)
    parser.add_argument('--asset', required=True, choices=ASSETS)
    parser.add_argument('--source-url', required=True)
    parser.add_argument('--retrieved-at', required=True, help='Actual retrieval timestamp with timezone')
    parser.add_argument('--published-at', required=True, help='Verified source publication timestamp with timezone')
    parser.add_argument('--commit', action='store_true', help='Save a local snapshot; does not approve G0 or publish')
    parser.add_argument('--output', default='data/snapshots')
    args = parser.parse_args(argv)
    try:
        prepared = prepare_snapshot(args.file, args.format, args.asset, args.source_url,
                                    args.retrieved_at, args.published_at)
        result = {'manifest': prepared[2], 'audit': prepared[3]}
        if args.commit:
            result['saved_to'] = str(save_snapshot(prepared, args.output))
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, UnicodeError) as error:
        parser.exit(1, f'Import rejected: {error}\n')


if __name__ == '__main__':
    main()
