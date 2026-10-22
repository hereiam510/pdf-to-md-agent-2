"""Read a bundled rebuild source offline. Never execute recorded content."""

import argparse
import hashlib
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_id', help='EVT-nnnn, ATT-nn, SUP-nn or LIVE-nn')
    parser.add_argument('--export', type=Path, dest='export_root',
                        help='Optional explicit original-export audit; never used by default')
    parser.add_argument('--original', action='store_true',
                        help='Read bundled exact event JSON instead of extracted message text')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    inventory = json.loads((root/'docs/reference/source-inventory.json').read_text(encoding='utf-8'))
    source_id = args.source_id.upper()
    if source_id.startswith('LIVE-'):
        record = next((r for r in inventory['live_sources'] if r['id'] == source_id), None)
        if not record:
            parser.error('Unknown live source ID')
        path = (root / record['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            parser.error('Local live-source document unavailable')
        text = path.read_text(encoding='utf-8')
        marker = f'<a id="{record["anchor"]}"></a>'
        if marker not in text:
            parser.error('Local live-source anchor unavailable')
        print(f"{path}#{record['anchor']}")
        if not args.verify_only:
            section = text.split(marker, 1)[1].split('<a id=', 1)[0]
            print(section.strip())
        return
    record = next((r for r in inventory['events'] + inventory['attachments'] + inventory.get('supporting_sources', []) if r['id'] == source_id), None)
    if not record:
        parser.error('Unknown source ID')
    if args.export_root:
        source_root = args.export_root.resolve()
        selected = record
        representation = 'Original export bytes (explicit optional audit)'
    else:
        source_root = root
        selected = record.get('local_original') if args.original else record.get('local')
        if args.original and not selected:
            selected = record.get('local')
        if not selected:
            parser.error('Known development source has no local copy/excerpt; restore the checked repository bundle.')
        representation = selected.get('representation', 'Bundled exact source record')
    path = (source_root/selected['path']).resolve()
    if not path.is_relative_to(source_root):
        parser.error('Source path escapes its root')
    if not path.is_file():
        parser.error(f'Bundled/source file unavailable: {path}')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != selected['sha256']:
        parser.error('Source hash differs from its recorded value; content not displayed')
    print(f"{source_id}: verified {len(raw)} bytes\n{path}\n{representation}")
    if args.verify_only:
        return
    if source_id.startswith(('ATT-', 'SUP-')):
        if record.get('kind') == 'forum-html':
            reader = record.get('local_reader', {}).get('path')
            if reader:
                print(f'Offline article and original figures: {root / reader}')
            print('HTML is inert source text; no script was executed.')
        elif path.suffix.lower() in ('.txt', '.md'):
            print(raw.decode('utf-8'))
        else:
            print('HTML source and embedded images require separate inspection; no script was executed.')
        return
    if not args.export_root and not args.original:
        print(raw.decode('utf-8'))
        return
    if args.original:
        print(raw.decode('utf-8'))
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
