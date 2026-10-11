/** Keep language and submitted search filters when moving between local pages. */
export function updatePageLinks(locale) {
  const params = new URLSearchParams(location.search);
  params.set('lang', locale);
  for (const anchor of document.querySelectorAll('[data-page-link]')) {
    anchor.href = `${anchor.dataset.pageLink}?${params}`;
  }
}
