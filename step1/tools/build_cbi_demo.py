#!/usr/bin/env python3
"""Build a metadata-only CBI comparison demo; never fetch or publish CBI media.

Human-reviewed comparisons and automatic title leads have separate statuses.
A publication match never transfers to its individual image references.
"""
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unicodedata
from urllib.parse import quote, urlsplit, urlunsplit
from build_site_data import PROJECT_ROOT, SOURCES, public_record, public_url

THUMBNAIL_HOSTS = ('loc.gov', 'archives.gov', 'si.edu', 'archive.org', 'iwm.org.uk')
STOP = set('the and for with from into over along through this that china burma india cbi world war ii wwii theater theatre collection photos photographs photo images image picture of in to a an on at by us army untitled index html jpg jpeg gif png'.split())


def thumbnail_url(value):
    url = public_url(value)
    if not url or urlsplit(url).scheme != 'https':
        return None
    host = urlsplit(url).hostname
    return url if any(host == h or host.endswith('.' + h) for h in THUMBNAIL_HOSTS) else None


def reference_url(value):
    """Keep legacy filenames with spaces as encoded pointers, never previews."""
    if not isinstance(value, str) or '\\' in value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        return None
    try:
        parts = urlsplit(value)
        encoded = urlunsplit((parts.scheme, parts.netloc,
                              quote(parts.path, safe="/:@!$&'()*+,;=-._~%"),
                              quote(parts.query, safe="=&?/:@!$'()*+,;~-._%"), ''))
        return public_url(encoded)
    except ValueError:
        return None


def canonical_url(value):
    url = reference_url(value)
    if not url:
        return None
    parts = urlsplit(url)
    return parts.hostname.removeprefix('www.') + parts.path.rstrip('/')


def tokens(value):
    return {v for v in re.findall(r'[\w]+', unicodedata.normalize('NFKC', value).lower()) if len(v) > 2 and v not in STOP and not v.isdigit()}


def title_leads(title, records):
    reference = tokens(title)
    if len(reference) < 2:
        return []
    ranked = []
    for record in records:
        overlap = reference & tokens(record.get('title') or '')
        if len(overlap) >= 2 and len(overlap) / len(reference) >= .6:
            ranked.append((len(overlap) / len(reference), record['id']))
    return [identity for _, identity in sorted(ranked, reverse=True)[:3]]


def read(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def entry_id(kind, url):
    return kind + ':' + hashlib.sha256(url.encode()).hexdigest()[:16]


def build_demo(root=PROJECT_ROOT):
    root = Path(root)
    folder = root / 'data' / 'cbi'
    inventory = read(folder / 'inventory.json', {})
    if not inventory.get('pages'):
        raise ValueError('Run inventory_cbi.py before building the demo.')
    raw = read(folder / 'archive-records.json', {'records': [], 'queries': []})
    sources = {s['id']: s for s in SOURCES}
    records = []
    for record in raw.get('records', []):
        if record.get('source') not in sources:
            continue
        clean = public_record(record, sources[record['source']])
        if clean:
            clean['thumbnail_url'] = thumbnail_url(clean.get('thumbnail_url'))
            records.append(clean)
    review = read(folder / 'verified-matches.json', {'records': []})
    matches = []
    for record in review.get('records', []):
        # This file is a manually reviewed crosswalk, not an arbitrary API response.
        clean = {k: record.get(k) for k in ('id', 'cbi_page_title', 'archival_title', 'archival_id', 'source', 'source_name_en', 'source_name_zh', 'material_type', 'match_status', 'evidence', 'evidence_zh', 'rights_note', 'checked_at', 'next_step', 'next_step_zh', 'access_note')}
        for k in ('cbi_page_url', 'archival_url', 'thumbnail_source_url'):
            clean[k] = public_url(record.get(k))
        clean['thumbnail_url'] = thumbnail_url(record.get('thumbnail_url'))
        clean['evidence_urls'] = [u for u in (public_url(v) for v in record.get('evidence_urls', [])) if u]
        if clean.get('id') and clean.get('archival_url') and clean.get('cbi_page_url') and clean['match_status'] in ('exact_item', 'same_work', 'related', 'unverified'):
            matches.append(clean)
    indexed = {}
    for record in matches:
        indexed.setdefault(canonical_url(record['cbi_page_url']), []).append(record)
    pages = {p['url']: p for p in inventory.get('pages', [])}
    menu = {p['url']: p for p in inventory.get('menu_items', [])}
    discovered = {p['url']: p for p in inventory.get('frontier', [])}
    reviewed = {r['cbi_page_url']: r for r in matches}
    items = []
    for url in sorted(set(pages) | set(menu) | set(discovered) | set(reviewed)):
        page, menu_item = pages.get(url, {}), menu.get(url, {})
        comparisons = indexed.get(canonical_url(url), [])
        title = page.get('title') or menu_item.get('title') or reviewed.get(url, {}).get('cbi_page_title') or urlsplit(url).path
        leads = title_leads(title, records)
        status = next((s for s in ('exact_item', 'same_work', 'related', 'unverified') if any(m['match_status'] == s for m in comparisons)), 'keyword_lead' if leads else 'not_reviewed')
        items.append({'id': entry_id('page', url), 'kind': 'page', 'title': title, 'url': reference_url(url), 'reference_url': reference_url(url), 'category': menu_item.get('category'), 'fetch_status': page.get('status', 'not_fetched'), 'review_status': status, 'comparison_ids': [m['id'] for m in comparisons], 'candidate_ids': leads, 'image_count': len(page.get('images', [])), 'archive_citations': [u for u in (public_url(v.get('url') if isinstance(v, dict) else v) for v in page.get('external_archival_links', [])) if u]})
    for asset in inventory.get('assets', []):
        url = reference_url(asset.get('url'))
        if not url:
            continue
        parents = asset.get('referenced_by', [])
        refs = [p.get('page_url') or p.get('url') if isinstance(p, dict) else p for p in parents]
        title = asset.get('alt') or asset.get('title') or urlsplit(url).path.rsplit('/', 1)[-1]
        if isinstance(title, list):
            title = ' / '.join(title)
        leads = title_leads(title, records)
        items.append({'id': entry_id('asset', url), 'kind': asset.get('kind', 'image'), 'title': title, 'url': url, 'reference_url': reference_url(refs[0]) if refs else None, 'reference_count': len(refs), 'fetch_status': 'not_requested', 'review_status': 'keyword_lead' if leads else 'not_reviewed', 'comparison_ids': [], 'candidate_ids': leads, 'archive_citations': []})
    access = read(folder / 'access-report.json', {'results': []})
    nara = read(folder / 'nara-access-report.json', {})
    web_checks = read(folder / 'platform-web-checks.json', {})
    return {'schema_version': 1, 'reference_url': inventory.get('source_url'), 'updated_at': inventory.get('updated_at'), 'coverage': inventory.get('summary', {}), 'run_status': inventory.get('run_status'), 'limitations': inventory.get('limitations', []), 'records': records, 'queries': raw.get('queries', []), 'comparisons': matches, 'items': items, 'access': access.get('results', []), 'nara_dataset_access': nara, 'web_checks': web_checks}


def write_demo(root=PROJECT_ROOT):
    root = Path(root)
    data = build_demo(root)
    path = root / 'site' / 'data' / 'cbi-demo.json'
    if any(p.is_symlink() for p in (root / 'site', path.parent, path)):
        raise ValueError('Public demo destination must not be a symbolic link.')
    path.parent.mkdir(exist_ok=True, parents=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, separators=(',', ':'))
            stream.write('\n')
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    return data


def main():
    data = write_demo()
    print(f"CBI demo: {len(data['items'])} references, {len(data['records'])} archive records, {len(data['comparisons'])} reviewed comparisons. No CBI media fetched.")


if __name__ == '__main__':
    main()
