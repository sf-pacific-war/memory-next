/** Browse editorial groupings independently of the visitor's active search. */
export function browseRecords(catalog, topicId = '') {
  const topic = (catalog.topics || []).find(topic => topic.id === topicId);
  const ids = topic ? new Set(topic.record_ids) : null;
  return catalog.records.filter(record => !ids || ids.has(record.id)).sort((a, b) =>
    Number(Boolean(b.thumbnail_url)) - Number(Boolean(a.thumbnail_url)) ||
    Number(b.record_origin === 'curated') - Number(a.record_origin === 'curated'));
}
export function discoveryLink(locale, values = {}) {
  const params = new URLSearchParams({ lang: locale === 'en' ? 'en' : 'zh-CN' });
  for (const key of ['topic', 'q', 'record']) if (values[key]) params.set(key, values[key]);
  return `./?${params}`;
}
