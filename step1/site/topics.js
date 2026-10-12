import { createDemoBanner } from './demo-banner.mjs';
import { sourceLabel, formatLabel } from './search.mjs';
import { archivalThumbnail } from './archive-media.mjs';
import { bindPageTranslations, resolveLocale, normalizeLocale, translate } from './i18n.mjs';
import { updatePageLinks } from './page-links.mjs';
import { browseRecords, discoveryLink } from './topics.mjs';

const $ = id => document.getElementById(id);
const LANGUAGE_KEY = 'pacific-war-language-choice';
const savedLocale = () => { try { return localStorage.getItem(LANGUAGE_KEY); } catch { return null; } };
const getLocale = () => resolveLocale(new URLSearchParams(location.search).get('lang'), savedLocale());
let locale = getLocale();
let catalog = null;
let active = '';
let visible = 12;
const t = (key, values) => translate(key, locale, values);
const applyLanguage = bindPageTranslations(document);
const renderDemoBanner = createDemoBanner(document);
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function readState() {
  const requested = new URLSearchParams(location.search).get('browse');
  active = catalog?.topics.some(topic => topic.id === requested) ? requested : '';
}
function saveState() {
  const url = new URL(location.href);
  url.searchParams.set('lang', locale);
  if (active) url.searchParams.set('browse', active); else url.searchParams.delete('browse');
  if (url.href !== location.href) history.pushState(null, '', url);
  updatePageLinks(locale);
}
function link(label, href, className = '') {
  const a = el('a', className, label);
  a.href = href;
  return a;
}
function originalLink(record, label, className = '') {
  try {
    const url = new URL(record.source_url);
    if (['http:', 'https:'].includes(url.protocol) && !url.username && !url.password) {
      const a = link(label, url.href, className);
      a.target = '_blank'; a.rel = 'noopener noreferrer';
      a.title = `${record.title} — ${t(record.source_url_kind === 'catalogue_search' ? '在新标签页打开原馆检索入口' : '在新标签页打开原始出处')}`;
      return a;
    }
  } catch { /* Keep notes available when no valid original source link exists. */ }
  return el('span', className, label);
}
function preview(record) {
  const a = originalLink(record, '', 'record-preview');
  a.setAttribute('aria-label', t('打开原始出处：{title}（{type}）', { title: record.title, type: formatLabel(record.format, locale) }));
  const fallback = el('span', 'topic-preview-fallback', t('无预览图'));
  a.append(fallback, el('span', 'preview-type', formatLabel(record.format, locale)));
  const url = archivalThumbnail(record.thumbnail_url);
  if (url) {
    const img = el('img', 'record-thumbnail');
    img.alt = ''; img.loading = 'lazy'; img.decoding = 'async'; img.referrerPolicy = 'no-referrer';
    img.addEventListener('load', () => { img.classList.add('is-loaded'); fallback.hidden = true; }, { once: true });
    img.addEventListener('error', () => img.remove(), { once: true });
    img.src = url;
    a.append(img);
  }
  return a;
}
function recordCard(record) {
  const card = el('article', 'record-card');
  const href = discoveryLink(locale, { record: record.id });
  const content = el('div', 'record-content');
  content.append(el('div', 'record-source', sourceLabel(record.source, locale)));
  const title = el('h3', 'record-title');
  title.append(originalLink(record, record.title));
  content.append(title, el('p', 'record-meta', `${formatLabel(record.format, locale)} · ${record.date_display || t('日期不详')}`));
  const note = record.curator_note?.[locale];
  content.append(el('p', 'record-description', record.description || (note ? `${t('编者导读')} · ${note}` : t('原目录未提供摘要，可前往来源页面查看完整记录。'))));
  const bottom = el('div', 'record-bottom');
  const notes = link(t('记录说明'), href, 'record-link');
  notes.setAttribute('aria-label', t('记录说明：{title}', { title: record.title }));
  bottom.append(notes);
  content.append(bottom); card.append(preview(record), content);
  return card;
}
function render() {
  applyLanguage(locale); $('language').value = locale;
  updatePageLinks(locale);
  renderDemoBanner(catalog, locale);
  if (!catalog) return;
  $('topic-count').textContent = catalog.topics.length;
  $('browse-count').textContent = catalog.records.length;
  $('topic-menu').replaceChildren();
  const choices = [{ id: '', title: { en: 'All collected records', 'zh-CN': '全部专题资料' }, record_ids: catalog.records.map(r => r.id) }, ...catalog.topics];
  for (const topic of choices) {
    const button = el('button', 'topic-choice'); button.type = 'button';
    button.setAttribute('aria-pressed', String(active === topic.id));
    button.append(el('span', '', topic.title[locale]), el('small', '', String(topic.record_ids.length)));
    button.addEventListener('click', () => { active = topic.id; visible = 12; saveState(); render(); });
    $('topic-menu').append(button);
  }
  const topic = catalog.topics.find(topic => topic.id === active);
  $('browse-title').textContent = topic?.title[locale] || t('从一份资料，走进一段历史。');
  $('browse-description').textContent = topic?.description[locale] || t('浏览已收录的照片、地图、文献与实物记录。选择左侧专题，沿着人物、交通线与战时生活逐步展开。');
  $('topic-keywords').replaceChildren();
  for (const word of topic?.keywords[locale] || []) $('topic-keywords').append(link(word, discoveryLink(locale, { q: word }), 'topic-keyword'));
  $('topic-search').textContent = topic ? t('在资料发现中检索这个专题 ↗') : t('在资料发现中检索全部资料 ↗');
  $('topic-search').href = discoveryLink(locale, topic ? { topic: topic.id } : {});
  const records = browseRecords(catalog, active);
  $('topic-records').replaceChildren(...records.slice(0, visible).map(recordCard));
  $('browse-announcement').textContent = t('已显示 {shown} / {total} 条资料', { shown: Math.min(visible, records.length), total: records.length });
  $('topic-more').hidden = visible >= records.length;
  $('browse-empty').hidden = records.length !== 0;
  $('topic-records').setAttribute('aria-busy', 'false');
}
async function load() {
  $('browse-error').hidden = true; $('browse-loading').hidden = false; $('browse-layout').hidden = true;
  try {
    const response = await fetch('./data/catalog.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error('Catalog unavailable');
    const data = await response.json();
    if (!Array.isArray(data.records) || !Array.isArray(data.topics) || !data.topics.every(t => t.id && t.title?.en && t.title?.['zh-CN'] && Array.isArray(t.record_ids))) throw new Error('Invalid catalog');
    catalog = data; readState(); render(); $('browse-layout').hidden = false;
  } catch { catalog = null; $('browse-error').hidden = false; }
  finally { $('browse-loading').hidden = true; }
}
$('language').addEventListener('change', () => {
  locale = normalizeLocale($('language').value) || locale;
  try { localStorage.setItem(LANGUAGE_KEY, locale); } catch { /* Storage may be disabled. */ }
  saveState(); render();
});
$('topic-more').addEventListener('click', () => {
  const previous = visible; visible += 12; render();
  $('topic-records').children[previous]?.querySelector('a')?.focus({ preventScroll: true });
});
$('retry-button').addEventListener('click', load);
$('help-button').addEventListener('click', () => $('help-dialog').showModal());
$('close-help').addEventListener('click', () => $('help-dialog').close());
window.addEventListener('popstate', () => { locale = getLocale(); readState(); visible = 12; render(); });
const initial = new URL(location.href); initial.searchParams.set('lang', locale); history.replaceState(null, '', initial);
render(); load();
