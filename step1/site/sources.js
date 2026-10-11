import { sourceLabel } from './search.mjs';
import { bindPageTranslations, resolveLocale, normalizeLocale, translate } from './i18n.mjs';
import { updatePageLinks } from './page-links.mjs';

const $ = id => document.getElementById(id);
const LANGUAGE_KEY = 'pacific-war-discovery-language';
function savedLocale() {
  try { return localStorage.getItem(LANGUAGE_KEY); } catch { return null; }
}
function currentLocale() {
  return resolveLocale(new URLSearchParams(location.search).get('lang'), savedLocale(), navigator.languages || [navigator.language]);
}
let locale = currentLocale();
let catalog = null;
let loadFailed = false;
const t = (message, values) => translate(message, locale, values);
const applyPageLanguage = bindPageTranslations(document);

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
    card.append(heading, el('h2', '', sourceLabel(source.id, locale)), el('p', '', t(source.description || '公开目录元数据样本。')));
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
  $('scope-note').textContent = t('样本范围说明：当前索引包含 {count} 条真实目录记录，经过初步排除同名误命中；仍需逐条核对史料相关性。NDL 样本包括战后出版的回忆录与研究书目。更多结果需在原馆继续检索。', { count: catalog.records.length });
  $('sample-count').textContent = catalog.records.length;
  $('source-count').textContent = catalog.sources.filter(s => s.count > 0).length;
  const lastDate = catalog.sources.map(s => s.fetched_at).filter(Boolean).sort().at(-1);
  const date = new Date(lastDate);
  const formatted = lastDate && !Number.isNaN(date.valueOf()) ? date.toLocaleDateString(locale, { year: 'numeric', month: '2-digit', day: '2-digit' }) : t('日期未提供');
  $('updated-date').textContent = t('样本更新 {date}', { date: formatted });
}

async function loadCatalog() {
  loadFailed = false;
  catalog = null;
  $('error-state').hidden = true;
  $('scope-note').hidden = true;
  $('sources-loading').hidden = false;
  $('source-cards').replaceChildren();
  $('source-cards').setAttribute('aria-busy', 'true');
  $('sample-count').textContent = '—';
  $('source-count').textContent = '—';
  $('updated-date').textContent = t('正在载入资料');
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
    loadFailed = true;
    $('source-cards').replaceChildren();
    $('error-state').hidden = false;
    $('updated-date').textContent = t('样本载入失败');
  } finally {
    $('sources-loading').hidden = true;
    $('source-cards').setAttribute('aria-busy', 'false');
  }
}

function changeLanguage(value, { save = true } = {}) {
  locale = normalizeLocale(value) || locale;
  applyPageLanguage(locale);
  $('language').value = locale;
  try { localStorage.setItem(LANGUAGE_KEY, locale); } catch { /* Storage may be disabled. */ }
  if (catalog) renderSources();
  else $('updated-date').textContent = t(loadFailed ? '样本载入失败' : '正在载入资料');
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
