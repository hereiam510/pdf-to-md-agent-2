"""Check local documentation links, source IDs and preservation coverage structure."""

import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def anchors(text):
    result = set(re.findall(r'<a\s+(?:id|name)=[\"\']([^\"\']+)[\"\']', text))
    counts = Counter()
    for line in text.splitlines():
        match = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line)
        if match:
            heading = re.sub(r'<[^>]*>', '', match.group(1)).lower()
            slug = re.sub(r'[^\w\- ]', '', heading, flags=re.UNICODE).replace(' ', '-')
            duplicate = counts[slug]
            counts[slug] += 1
            result.add(slug + (f'-{duplicate}' if duplicate else ''))
    return result


def main():
    errors = []
    files = [ROOT/'README.md', ROOT/'AGENTS.md', *sorted((ROOT/'docs').rglob('*.md'))]
    documents = {path: path.read_text(encoding='utf-8-sig') for path in files if path.is_file()}
    known_anchors = {path: anchors(text) for path, text in documents.items()}
    links = 0

    def check_target(origin, target):
        nonlocal links
        target = target.strip().strip('<>')
        if urlsplit(target).scheme or target.startswith('//'):
            return
        target_path, _, fragment = target.partition('#')
        resolved = (origin.parent/unquote(target_path)).resolve() if target_path else origin
        links += 1
        if not resolved.is_relative_to(ROOT):
            errors.append(f'{origin.relative_to(ROOT)}: local link leaves repository: {target}')
        elif not resolved.exists():
            errors.append(f'{origin.relative_to(ROOT)}: missing {target}')
        elif fragment and resolved.suffix == '.md' and unquote(fragment) not in known_anchors.get(resolved, set()):
            errors.append(f'{origin.relative_to(ROOT)}: missing anchor {target}')

    for path, text in documents.items():
        # Only actual Markdown links, not raw source paths or code identifiers.
        for match in re.finditer(r'(?<!!)\[[^\]\n]+\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)', text):
            check_target(path, match.group(1))

    inventory_path = ROOT/'docs/reference/source-inventory.json'
    point_path = ROOT/'docs/reference/POINT_COVERAGE.json'
    coverage_path = ROOT/'docs/reference/SOURCE_COVERAGE.json'
    if not all(p.is_file() for p in (inventory_path, point_path, coverage_path)):
        errors.append('Source inventory / point coverage / source coverage not all present')
        inventory, points, coverage = {}, [], []
    else:
        inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
        points = json.loads(point_path.read_text(encoding='utf-8'))
        coverage = json.loads(coverage_path.read_text(encoding='utf-8'))
    source_ids = {r['id'] for key in ('events', 'attachments', 'live_sources', 'supporting_sources') for r in inventory.get(key, [])}
    point_ids = set()
    for p in points:
        identity = p.get('id')
        if not identity or identity in point_ids:
            errors.append(f'Missing/duplicate point ID: {identity}')
        point_ids.add(identity)
        for field in ('topic','summary','status','source_ids','destination'):
            if not p.get(field):
                errors.append(f'{identity}: missing {field}')
        for source in p.get('source_ids', []):
            if source not in source_ids:
                errors.append(f'{identity}: unknown source {source}')
        if p.get('destination'):
            check_target(ROOT/'_root.md', p['destination'])
    covered = set()
    for row in coverage:
        identity = row.get('source_id')
        if identity in covered or identity not in source_ids:
            errors.append(f'Duplicate/unknown source disposition: {identity}')
        covered.add(identity)
        if not row.get('disposition') or not row.get('reason'):
            errors.append(f'{identity}: missing source disposition/reason')
        if row.get('disposition') == 'unresolved-review-required':
            errors.append(f'{identity}: source review unresolved')
        for point in row.get('point_ids', []):
            if point not in point_ids:
                errors.append(f'{identity}: unknown point {point}')
    required = {r['id'] for r in inventory.get('events', []) if r['type'] in ('UserMessage','AgentMessage')}
    required |= {r['id'] for r in inventory.get('attachments', []) + inventory.get('live_sources', []) + inventory.get('supporting_sources', [])}
    required.add('EVT-0001')
    for missing in sorted(required-covered):
        errors.append(f'Missing source disposition: {missing}')
    for path, text in documents.items():
        for source in set(re.findall(r'\b(?:EVT-\d{4}|ATT-\d{2}|LIVE-\d{2}|SUP-\d{2})\b', text)):
            if source not in source_ids:
                errors.append(f'{path.relative_to(ROOT)}: unknown source ID {source}')
    report = {'markdown_files':len(documents),'local_links_and_destinations_checked':links,'preserved_points':len(points),'source_dispositions':len(coverage),'errors':errors,'scope':'Structural documentation check; semantic completeness and runtime correctness require separate evidence.'}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return bool(errors)


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
