import { createDemoBanner } from './demo-banner.mjs';
import { sourceLabel } from './search.mjs';
import { bindPageTranslations, resolveLocale, normalizeLocale, translate } from './i18n.mjs';
import { updatePageLinks } from './page-links.mjs';

const $ = id => document.getElementById(id);
const LANGUAGE_KEY = 'pacific-war-language-choice';
function savedLocale() {
  try { return localStorage.getItem(LANGUAGE_KEY); } catch { return null; }
}
function currentLocale() {
  return resolveLocale(new URLSearchParams(location.search).get('lang'), savedLocale());
}
let locale = currentLocale();
let catalog = null;
const t = (message, values) => translate(message, locale, values);
const applyPageLanguage = bindPageTranslations(document);
const renderDemoBanner = createDemoBanner(document);

function el(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}
function renderSources() {
  const cards = $('source-cards');
  cards.replaceChildren();
  for (const source of catalog.sources) {
    const card = el('article', 'source-card');
    const heading = el('div', 'source-card-heading');
    const count = source.count ? (locale === 'en' && source.count === 1 ? '1 sample' : t('{count} 条样本', { count: source.count })) : t('暂未接入');
    heading.append(el('span', 'source-abbr', source.id.toUpperCase()), el('span', `source-state${source.count ? '' : ' unavailable'}`, count));
    const curatedOnly = source.access_modes?.length === 1 && source.access_modes[0] === 'curated';
    const description = curatedOnly ? t('人工整理的原馆记录与研究入口，尚未接通该机构的搜索 API。') : source.access_modes?.includes('curated') ? t('目录数据与人工整理的原馆记录；原件访问和使用条件以来源说明为准。') : t(source.description || '公开目录元数据样本。');
    card.append(heading, el('h2', '', sourceLabel(source.id, locale)), el('p', '', description));
    if (source.access_modes?.length) card.append(el('p', 'source-modes', source.access_modes.map(mode => t({ api: 'API 元数据', dataset: '公开数据集', curated: '人工整理' }[mode] || mode)).join(' · ')));
    try {
      const url = new URL(source.url);
      if (['http:', 'https:'].includes(url.protocol) && !url.username && !url.password) {
        const anchor = el('a', '', t('访问来源网站 ↗'));
        anchor.href = url.href;
        anchor.target = '_blank';
        anchor.rel = 'noopener noreferrer';
        card.append(anchor);
      }
    } catch { /* A missing or invalid URL is never made into a link. */ }
    cards.append(card);
  }
  $('scope-note').textContent = t('样本范围说明：当前索引包含 {count} 条真实目录记录，经过初步排除同名误命中；仍需逐条核对史料相关性。更多结果需在原馆继续检索。', { count: catalog.records.length });
  renderDemoBanner(catalog, locale);
}

async function loadCatalog() {
  catalog = null;
  $('error-state').hidden = true;
  $('scope-note').hidden = true;
  $('sources-loading').hidden = false;
  $('source-cards').replaceChildren();
  $('source-cards').setAttribute('aria-busy', 'true');
  renderDemoBanner(null, locale);
  try {
    const response = await fetch('./data/catalog.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error('Catalogue unavailable');
    const data = await response.json();
    if (!Array.isArray(data.records) || !Array.isArray(data.sources)
        || !data.sources.every(s => s && typeof s.id === 'string' && Number.isInteger(s.count) && s.count >= 0)) throw new Error('Invalid catalogue');
    catalog = data;
    renderSources();
    $('scope-note').hidden = false;
  } catch {
    catalog = null;
    $('source-cards').replaceChildren();
    $('error-state').hidden = false;
    renderDemoBanner(null, locale);
  } finally {
    $('sources-loading').hidden = true;
    $('source-cards').setAttribute('aria-busy', 'false');
  }
}

function changeLanguage(value, { save = true } = {}) {
  locale = normalizeLocale(value) || locale;
  applyPageLanguage(locale);
  $('language').value = locale;
  try { if (save) localStorage.setItem(LANGUAGE_KEY, locale); } catch { /* Storage may be disabled. */ }
  if (catalog) renderSources();
  else renderDemoBanner(null, locale);
  if (save) {
    const url = new URL(location.href);
    url.searchParams.set('lang', locale);
    history.pushState(null, '', `${url.pathname}${url.search}${url.hash}`);
  }
  updatePageLinks(locale);
}
$('language').addEventListener('change', () => changeLanguage($('language').value));
$('retry-button').addEventListener('click', loadCatalog);
$('help-button').addEventListener('click', () => $('help-dialog').showModal());
$('close-help').addEventListener('click', () => $('help-dialog').close());
$('help-dialog').addEventListener('click', e => {
  const rect = $('help-dialog').getBoundingClientRect();
  if (e.target === $('help-dialog') && (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom)) $('help-dialog').close();
});
window.addEventListener('popstate', () => changeLanguage(currentLocale(), { save: false }));
const initialURL = new URL(location.href);
initialURL.searchParams.set('lang', locale);
history.replaceState(null, '', `${initialURL.pathname}${initialURL.search}${initialURL.hash}`);
changeLanguage(locale, { save: false });
loadCatalog();
