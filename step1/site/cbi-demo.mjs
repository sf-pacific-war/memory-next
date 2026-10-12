/** CBI references are pointers only; previews must be archive-origin URLs. */
export function archivalThumbnail(value) {
  try {
    const url = new URL(value);
    const hosts = ['loc.gov', 'archives.gov', 'si.edu', 'archive.org', 'iwm.org.uk'];
    return url.protocol === 'https:' && !url.username && !url.password && !url.port && hosts.some(h => url.hostname === h || url.hostname.endsWith(`.${h}`)) ? url.href : null;
  } catch { return null; }
}
export function referenceMatches(item, query, kind, status) {
  const text = `${item.title || ''} ${item.url || ''} ${item.category || ''}`.normalize('NFKC').toLowerCase();
  return (!kind || item.kind === kind) && (!status || item.review_status === status) && query.normalize('NFKC').toLowerCase().trim().split(/\s+/u).every(word => text.includes(word));
}
