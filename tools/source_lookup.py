"""Read one exact preserved discussion source. Never execute recorded content."""

import argparse
import hashlib
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_id', help='EVT-nnnn, ATT-nn, SUP-nn or LIVE-nn')
    parser.add_argument('--export', type=Path, dest='export_root')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    inventory = json.loads((root/'docs/reference/source-inventory.json').read_text(encoding='utf-8'))
    source_id = args.source_id.upper()
    if source_id.startswith('LIVE-'):
        record = next((r for r in inventory['live_sources'] if r['id'] == source_id), None)
        if not record:
            parser.error('Unknown live source ID')
        print(f"{root / record['path']}#{record['anchor']}")
        return
    record = next((r for r in inventory['events'] + inventory['attachments'] + inventory.get('supporting_sources', []) if r['id'] == source_id), None)
    if not record:
        parser.error('Unknown source ID')
    export_root = (args.export_root or root.parent/inventory['export_folder']).resolve()
    path = (export_root/record['path']).resolve()
    if not path.is_relative_to(export_root):
        parser.error('Source path escapes export root')
    if not path.is_file():
        parser.error(f'Source unavailable: {path}; supply --export for the preserved package')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != record['sha256']:
        parser.error('Source hash differs from the reviewed export; content not displayed')
    print(f"{source_id}: verified {len(raw)} bytes\n{path}")
    if args.verify_only:
        return
    if source_id.startswith(('ATT-', 'SUP-')):
        if path.suffix.lower() in ('.txt', '.md'):
            print(raw.decode('utf-8'))
        else:
            print('HTML source and embedded images require separate inspection; no script was executed.')
        return
    data = json.loads(raw)
    item = data.get('item', data)
    if item.get('type') in ('UserMessage', 'AgentMessage'):
        for part in item.get('content', []):
            if isinstance(part, dict) and 'text' in part:
                print(part['text'])
    elif source_id == 'EVT-0001':
        print(item.get('output', ''))
    else:
        print('This is an evidence event, not a user/assistant message. Inspect the verified JSON as data.')


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
