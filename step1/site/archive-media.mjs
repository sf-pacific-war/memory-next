/** Preview images are loaded only from known archival hosts. */
export function archivalThumbnail(value) {
  try {
    const url = new URL(value);
    const hosts = ['loc.gov', 'archives.gov', 'si.edu', 'archive.org', 'iwm.org.uk', 'www.saac.gov.cn'];
    return url.protocol === 'https:' && !url.username && !url.password && !url.port && hosts.some(h => url.hostname === h || url.hostname.endsWith(`.${h}`)) ? url.href : null;
  } catch { return null; }
}
