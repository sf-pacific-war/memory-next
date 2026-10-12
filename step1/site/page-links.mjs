/** Keep language and submitted search filters when moving between local pages. */
export function pageURL(page, search, locale) {
  const params = new URLSearchParams(search);
  params.set('lang', locale);
  params.delete('record');
  if (page !== 'topics.html') params.delete('browse');
  return `${page}?${params}`;
}
export function updatePageLinks(locale) {
  for (const anchor of document.querySelectorAll('[data-page-link]')) {
    anchor.href = pageURL(anchor.dataset.pageLink, location.search, locale);
  }
}
