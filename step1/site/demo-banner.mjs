// Set to false to remove the temporary preview notice for a public release.
export const DEMO_BANNER_ENABLED = true;
const DISMISS_KEY = 'wwii-pacific-war-demo-notice-dismissed';

export function createDemoBanner(document) {
  let dismissed = false;
  try { dismissed = sessionStorage.getItem(DISMISS_KEY) === '1'; } catch { /* Storage is optional. */ }
  const banner = document.createElement('aside');
  banner.className = 'demo-banner';
  banner.hidden = true;
  const inner = document.createElement('div');
  inner.className = 'wrap demo-banner-inner';
  const label = document.createElement('strong');
  label.className = 'demo-banner-label';
  const summary = document.createElement('p');
  summary.className = 'demo-banner-summary';
  const counts = document.createElement('span');
  const meta = document.createElement('span');
  meta.className = 'demo-banner-meta';
  const close = document.createElement('button');
  close.type = 'button';
  close.className = 'demo-banner-close';
  close.textContent = '×';
  close.addEventListener('click', () => {
    dismissed = true;
    banner.hidden = true;
    try { sessionStorage.setItem(DISMISS_KEY, '1'); } catch { /* Dismissal still works on this page. */ }
    document.querySelector('.brand')?.focus();
  });
  summary.append(counts, meta);
  inner.append(label, summary, close);
  banner.append(inner);
  document.body.insertBefore(banner, document.querySelector('.masthead'));
  return (catalog, locale) => {
    banner.hidden = !DEMO_BANNER_ENABLED || dismissed || !catalog;
    if (!catalog) return;
    const en = locale === 'en';
    label.textContent = en ? 'Demo preview' : '演示预览';
    banner.setAttribute('aria-label', en ? 'Temporary demo notice' : '临时演示提示');
    close.setAttribute('aria-label', en ? 'Dismiss demo notice' : '关闭演示提示');
    const count = catalog.records.length;
    const sources = catalog.sources.filter(source => source.count > 0).length;
    counts.textContent = en ? `${count} catalogue samples / ${sources} source institutions` : `${count} 条目录样本 / ${sources} 个来源机构`;
    const latest = catalog.sources.flatMap(source => [source.fetched_at, source.checked_at]).filter(Boolean).sort().at(-1);
    const date = new Date(latest);
    const formatted = Number.isNaN(date.valueOf()) ? '' : date.toLocaleDateString(locale, { year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'UTC' });
    meta.textContent = en ? `Local sample search${formatted ? ` · Updated ${formatted}` : ''}` : `本地样本检索${formatted ? ` · 样本更新 ${formatted}` : ''}`;
  };
}
