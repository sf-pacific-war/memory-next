import { filterRecords, expandQuery, formatLabel as typeName, sourceLabel as sourceName } from './search.mjs';
import { updatePageLinks } from './page-links.mjs';
import { archivalThumbnail } from './archive-media.mjs';
import { bindPageTranslations, resolveLocale, normalizeLocale, translate } from './i18n.mjs';

const $ = (id) => document.getElementById(id);
const PAGE_SIZE = 12;
const LANGUAGE_KEY = 'pacific-war-discovery-language';
function savedLocale() {
  try { return localStorage.getItem(LANGUAGE_KEY); } catch { return null; }
}
let locale = resolveLocale(new URLSearchParams(location.search).get('lang'), savedLocale(), navigator.languages || [navigator.language]);
const t = (message, values) => translate(message, locale, values);
const sourceLabel = source => sourceName(source, locale);
const formatLabel = type => typeName(type, locale);
const applyPageLanguage = bindPageTranslations(document);
let selectedRecord = null;
let loadFailed = false;
const defaults = () => ({ query: '', topic: '', sources: [], types: [], access: 'all', startYear: '', endYear: '', includeUnknownDates: true, sort: 'relevance' });
let state = defaults();
let catalog = null;
let visibleCount = PAGE_SIZE;
let filtered = [];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}
function list(value) { return Array.isArray(value) ? value.filter(v => typeof v === 'string') : typeof value === 'string' ? [value] : []; }
function safeURL(value) {
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}
function link(label, url, className) {
  const href = safeURL(url);
  if (!href) return null;
  const node = el('a', className, label);
  node.href = href;
  node.target = '_blank';
  node.rel = 'noopener noreferrer';
  return node;
}
function formatDate(value) {
  const date = new Date(value);
  return value && !Number.isNaN(date.valueOf()) ? date.toLocaleDateString(locale, { year: 'numeric', month: '2-digit', day: '2-digit' }) : t('日期未提供');
}
function languageLabel(record) {
  const names = { eng: t('英语'), en: t('英语'), english: t('英语'), jpn: t('日语'), ja: t('日语'), japanese: t('日语'), fr: t('法语'), fre: t('法语'), fra: t('法语'), french: t('法语'), chi: t('中文'), zho: t('中文'), zh: t('中文'), dut: t('荷兰语'), nld: t('荷兰语') };
  return [...new Set(list(record.language).map(v => names[v.toLowerCase()] || v))].join(locale === 'en' ? ', ' : '、') || t('语种未标注');
}
function readURL() {
  const params = new URLSearchParams(location.search);
  state = defaults();
  state.query = (params.get('q') || '').slice(0, 240);
  state.topic = (catalog.topics || []).some(t => t.id === params.get('topic')) ? params.get('topic') : '';
  state.sources = params.getAll('source').filter(v => catalog.sources.some(s => s.id === v));
  state.types = params.getAll('type').filter(v => catalog.records.some(r => r.format === v));
  state.access = ['online', 'unverified'].includes(params.get('access')) ? params.get('access') : 'all';
  state.startYear = params.get('from') || '';
  state.endYear = params.get('to') || '';
  state.includeUnknownDates = params.get('unknown') !== '0';
  state.sort = ['oldest', 'newest'].includes(params.get('sort')) ? params.get('sort') : 'relevance';
}
function writeURL() {
  const params = new URLSearchParams();
  params.set('lang', locale);
  if (state.query) params.set('q', state.query);
  if (state.topic) params.set('topic', state.topic);
  state.sources.forEach(v => params.append('source', v));
  state.types.forEach(v => params.append('type', v));
  if (state.access !== 'all') params.set('access', state.access);
  if (state.startYear) params.set('from', state.startYear);
  if (state.endYear) params.set('to', state.endYear);
  if (!state.includeUnknownDates) params.set('unknown', '0');
  if (state.sort !== 'relevance') params.set('sort', state.sort);
  const query = params.toString();
  const url = `${location.pathname}${query ? `?${query}` : ''}${location.hash}`;
  if (url !== `${location.pathname}${location.search}${location.hash}`) history.pushState(null, '', url);
  updatePageLinks(locale);
}
function checkOption(container, value, label, count, kind) {
  const row = el('label', 'check-row');
  const input = el('input');
  input.type = 'checkbox';
  input.value = value;
  input.dataset.kind = kind;
  input.addEventListener('change', () => {
    state[kind] = [...document.querySelectorAll(`input[data-kind="${kind}"]:checked`)].map(n => n.value);
    update();
  });
  row.append(input, el('span', '', label), el('small', 'facet-count', count));
  container.append(row);
}
function renderFilters() {
  $('source-filters').replaceChildren();
  for (const source of catalog.sources.filter(s => s.count > 0)) {
    checkOption($('source-filters'), source.id, sourceLabel(source.id), source.count, 'sources');
  }
  $('type-filters').replaceChildren();
  const types = [...new Set(catalog.records.map(r => r.format))];
  const order = ['IMAGE', 'TEXT', 'MAP', 'SOUND', 'VIDEO', 'MIXED'];
  const position = type => order.includes(type) ? order.indexOf(type) : order.length;
  types.sort((a, b) => position(a) - position(b));
  for (const type of types) checkOption($('type-filters'), type, formatLabel(type), catalog.records.filter(r => r.format === type).length, 'types');
}
function syncControls() {
  $('query').value = state.query;
  for (const input of document.querySelectorAll('input[data-kind]')) input.checked = state[input.dataset.kind].includes(input.value);
  $('start-year').value = state.startYear;
  $('end-year').value = state.endYear;
  $('unknown-dates').checked = state.includeUnknownDates;
  $('sort').value = state.sort;
  document.querySelectorAll('input[name="access"]').forEach(n => { n.checked = n.value === state.access; });
  document.querySelectorAll('[data-query]').forEach(n => { n.setAttribute('aria-pressed', String([n.dataset.query, n.dataset.queryEn].includes(state.query))); });
}
function validDates() {
  const validYear = value => value === '' || (/^\d{4}$/.test(value) && Number(value) >= 1000 && Number(value) <= 2100);
  let error = '';
  if (!validYear(state.startYear) || !validYear(state.endYear)) error = t('请输入 1000–2100 之间的四位年份。');
  else if (state.startYear && state.endYear && Number(state.startYear) > Number(state.endYear)) error = t('起始年份不能晚于结束年份。');
  $('date-error').hidden = !error;
  $('date-error').textContent = error;
  for (const id of ['start-year', 'end-year']) $(id).setAttribute('aria-invalid', String(Boolean(error)));
  return !error;
}
function renderChips() {
  const container = $('active-filters');
  container.replaceChildren();
  function chip(text, remove) {
    const button = el('button', 'filter-chip', `${text} ×`);
    button.type = 'button';
    button.setAttribute('aria-label', t('移除筛选：{text}', { text }));
    button.addEventListener('click', () => { remove(); syncControls(); update(); });
    container.append(button);
  }
  if (state.query) chip(`“${state.query}”`, () => { state.query = ''; });
  if (state.topic) chip((catalog.topics || []).find(t => t.id === state.topic)?.title[locale] || state.topic, () => { state.topic = ''; });
  state.sources.forEach(v => chip(sourceLabel(v), () => { state.sources = state.sources.filter(x => x !== v); }));
  state.types.forEach(v => chip(formatLabel(v), () => { state.types = state.types.filter(x => x !== v); }));
  if (state.startYear || state.endYear) chip(`${state.startYear || t('不限')}—${state.endYear || t('不限')}`, () => { state.startYear = ''; state.endYear = ''; });
  if (!state.includeUnknownDates) chip(t('仅有明确日期'), () => { state.includeUnknownDates = true; });
  if (state.access !== 'all') chip(state.access === 'online' ? t('有在线资源') : t('访问条件待确认'), () => { state.access = 'all'; });
}
function typeVisual(type) {
  const kind = { IMAGE: 'photo', SOUND: 'sound', MAP: 'map', TEXT: 'text', VIDEO: 'photo' }[type] || 'text';
  const div = el('div', `record-visual ${kind}`);
  div.setAttribute('aria-hidden', 'true');
  const paths = {
    IMAGE: '<rect x="5" y="7" width="30" height="25" rx="1"/><circle cx="26" cy="15" r="3"/><path d="m6 29 9-10 8 8 5-5 6 6"/>',
    TEXT: '<path d="M10 4h14l7 7v25H10zM24 4v8h7M15 19h11M15 24h11M15 29h7"/>',
    SOUND: '<path d="M7 17v7M12 12v17M18 6v29M24 10v21M30 15v11M35 18v5"/>',
    MAP: '<path d="m4 9 10-4 12 5 10-4v25l-10 4-12-5-10 4zM14 5v25M26 10v25"/>',
    VIDEO: '<rect x="4" y="8" width="32" height="24" rx="2"/><path d="m17 15 10 5-10 5z"/>',
  };
  // Fixed decorative SVG only; catalogue strings are always inserted as text.
  div.innerHTML = `<svg viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.2">${paths[type] || paths.TEXT}</svg>`;
  return div;
}
function recordPreview(record) {
  const button = el('button', 'record-preview');
  button.type = 'button';
  button.setAttribute('aria-label', t('查看资料：{title}（{type}）', { title: record.title || t('未提供标题'), type: formatLabel(record.format) }));
  button.addEventListener('click', () => openRecord(record));
  const fallback = typeVisual(record.format);
  const caption = el('span', 'preview-caption', t('无预览图'));
  fallback.append(caption);
  button.append(fallback, el('span', 'preview-type', formatLabel(record.format)));
  const url = archivalThumbnail(record.thumbnail_url);
  if (url?.startsWith('https://')) {
    const image = el('img', 'record-thumbnail');
    image.alt = '';
    image.loading = 'lazy';
    image.decoding = 'async';
    image.referrerPolicy = 'no-referrer';
    caption.textContent = t('正在载入预览…');
    image.addEventListener('load', () => {
      image.classList.add('is-loaded');
      fallback.hidden = true;
    }, { once: true });
    image.addEventListener('error', () => {
      image.remove();
      caption.textContent = t('无预览图');
    }, { once: true });
    image.src = url;
    button.append(image);
  }
  return button;
}
function recordCard(record, index) {
  const article = el('article', 'record-card');
  const content = el('div', 'record-content');
  const top = el('div', 'record-top');
  top.append(el('span', 'record-source', `${record.source} / ${sourceLabel(record.source)}`), el('span', 'record-number', String(index + 1).padStart(3, '0')));
  const title = el('h3', 'record-title');
  const button = el('button', '', record.title || t('未提供标题'));
  button.type = 'button';
  button.title = record.title || t('未提供标题');
  button.addEventListener('click', () => openRecord(record));
  title.append(button);
  const meta = el('div', 'record-meta');
  [record.date_display || t('日期不详'), languageLabel(record)].forEach((value, i) => {
    if (i) meta.append(el('span', 'meta-dot', '·'));
    meta.append(el('span', '', value));
  });
  const note = record.curator_note?.[locale];
  const description = el('p', 'record-description', record.description || (note ? `${t('编者导读')} · ${note}` : t('原目录未提供摘要，可前往来源页面查看完整记录。')));
  const bottom = el('div', 'record-bottom');
  bottom.append(el('span', `access-badge${record.access_status === 'online' ? ' online' : ''}`, record.access_status === 'online' ? t('有在线资源') : t('访问条件待确认')));
  const original = link(t('原馆记录 ↗'), record.source_url, 'record-link');
  if (original) bottom.append(original);
  content.append(top, title, meta);
  if (record.record_group) content.append(el('p', 'record-context', t('档案组 RG {group} · {context}', { group: record.record_group, context: list(record.archival_context)[0] || t('查看详情了解档案层级') })));
  content.append(description, bottom);
  article.append(recordPreview(record), content);
  return article;
}
function renderResults() {
  const shown = filtered.slice(0, visibleCount);
  $('results').replaceChildren(...shown.map(recordCard));
  $('results-heading').firstChild.textContent = `${state.query ? t('检索结果') : t('全部资料')} `;
  $('result-count').textContent = filtered.length;
  $('empty-state').hidden = filtered.length !== 0;
  $('results-bottom').hidden = filtered.length === 0;
  $('shown-count').textContent = t('已显示 {shown} / {total} 条资料', { shown: shown.length, total: filtered.length });
  $('load-more').hidden = shown.length >= filtered.length;
  $('result-announcement').textContent = t('找到 {total} 条目录样本，已显示 {shown} 条。', { total: filtered.length, shown: shown.length });
  $('results').setAttribute('aria-busy', 'false');
}
function update({ save = true, resetPage = true } = {}) {
  if (!catalog) return;
  if (resetPage) visibleCount = PAGE_SIZE;
  const valid = validDates();
  filtered = valid ? filterRecords(catalog.records, state) : [];
  renderChips();
  const expanded = expandQuery(state.query, locale);
  $('expansion-note').hidden = !expanded.label;
  $('expansion-note').textContent = expanded.label ? t('{label}。检索词：{terms}', { label: expanded.label, terms: expanded.terms.join(' / ') }) : '';
  renderResults();
  document.querySelectorAll('[data-topic-id]').forEach(n => n.setAttribute('aria-pressed', String(n.dataset.topicId === state.topic)));
  if (!valid) {
    $('empty-state').hidden = true;
    $('result-announcement').textContent = $('date-error').textContent;
  }
  document.querySelectorAll('[data-query]').forEach(n => { n.setAttribute('aria-pressed', String([n.dataset.query, n.dataset.queryEn].includes(state.query))); });
  if (save) writeURL();
}
function openRecord(record, { save = true } = {}) {
  selectedRecord = record;
  const container = $('detail-content');
  container.replaceChildren();
  const title = el('h2', '', record.title || t('未提供标题'));
  title.id = 'detail-title';
  container.append(el('p', 'eyebrow', `${record.source} / ${sourceLabel(record.source)}`), title, el('p', 'detail-description', record.description || t('原目录未提供描述。')));
  if (record.curator_note?.[locale]) container.append(el('p', 'detail-note', `${t('编者导读')} · ${record.curator_note[locale]}`));
  const grid = el('dl', 'detail-grid');
  const fields = [
    [t('收藏机构'), list(record.holding_institution).join('；') || t('原记录未标注')],
    [t('元数据提供方'), list(record.metadata_provider).join('；') || sourceLabel(record.source)],
    [t('目录日期'), record.date_display || t('日期不详')],
    [t('资料类型 / 语种'), `${formatLabel(record.format)} / ${languageLabel(record)}`],
    [t('访问状态'), record.access_status === 'online' ? t('来源标有在线数字资源；实际访问条件以原馆为准。') : t('只有目录或聚合记录，尚未确认公开全文／媒体访问。')],
    [t('主题词'), list(record.subjects).join(' · ') || t('原记录未提供')],
    [t('元数据许可'), record.metadata_rights || t('此记录未单独提供许可，请核对来源条款。')],
    [t('原件权利说明'), list(record.content_rights).join('\n') || t('未提供；不代表无版权限制。')],
    [t('来源记录编号'), record.archival_id || record.source_id || record.id],
    [t('样本获取时间'), formatDate(record.retrieved_at)],
  ];
  if (record.level_of_description) {
    const levels = { recordGroup: t('档案组'), collection: t('集合'), series: t('系列'), fileUnit: t('案卷'), item: t('单件') };
    fields.splice(2, 0, [t('目录层级'), levels[record.level_of_description] || record.level_of_description]);
  }
  if (record.record_group) fields.push([t('档案组'), `RG ${record.record_group}`]);
  if (list(record.archival_context).length) fields.push([t('所属档案背景（参与检索）'), list(record.archival_context).join('\n')]);
  if (record.dataset_updated_at) fields.push([t('公开数据文件更新时间'), formatDate(record.dataset_updated_at)]);
  if (record.access_note) fields.push([t('访问说明'), record.access_note]);
  if (record.checked_at) fields.push([t('来源核查时间'), formatDate(record.checked_at)]);
  if (record.topic_ids?.length) fields.push([t('专题标签（编辑整理）'), (catalog.topics || []).filter(topic => record.topic_ids.includes(topic.id)).map(topic => topic.title[locale]).join(' · ')]);
  if (record.record_origin === 'curated') fields.push([t('收录方式'), t('人工整理的原馆记录／研究入口')]);
  for (const [name, value] of fields) {
    const row = el('div');
    row.append(el('dt', '', name), el('dd', '', value));
    grid.append(row);
  }
  container.append(grid, el('p', 'detail-note', t('本条为待核对的目录候选。目录日期可能是创作或出版日期；战后回忆录的出版年份不表示事件发生年份。元数据许可不等于图片、音频或全文的使用许可。')));
  if (record.source === 'NARA' && record.record_origin === 'dataset') container.append(el('p', 'detail-note', t('NARA 记录来自官方开放数据集。系列和档案组记录可能描述多份材料；命中所属档案背景不等于每个下属文件都讨论该关键词。数字目录可访问，不代表原件已数字化。')));
  const links = el('div', 'detail-links');
  const original = link(t('前往原馆记录 ↗'), record.source_url, 'primary-button');
  if (original) links.append(original);
  if (record.aggregator_url !== record.source_url) {
    const aggregator = link(t('查看聚合目录 ↗'), record.aggregator_url, 'secondary-button');
    if (aggregator) links.append(aggregator);
  }
  if (record.dataset_url) {
    const dataset = link(t('公开数据文件 ↗'), record.dataset_url, 'secondary-button');
    if (dataset) links.append(dataset);
  }
  container.append(links);
  if (!$('detail-dialog').open) $('detail-dialog').showModal();
  $('detail-dialog').scrollTop = 0;
  if (save) {
    const url = new URL(location.href);
    if (url.searchParams.get('record') !== record.id) {
      url.searchParams.set('record', record.id);
      history.pushState(null, '', url);
    }
  }
}
function closeRecord() {
  $('detail-dialog').close();
  selectedRecord = null;
  const url = new URL(location.href);
  if (url.searchParams.has('record')) {
    url.searchParams.delete('record');
    history.replaceState(null, '', url);
  }
}
function renderSourceSummary() {
  $('sample-count').textContent = catalog.records.length;
  $('source-count').textContent = catalog.sources.filter(s => s.count > 0).length;
  const dates = catalog.sources.flatMap(s => [s.fetched_at, s.checked_at]).filter(Boolean).sort();
  $('updated-date').textContent = t('样本更新 {date}', { date: formatDate(dates.at(-1)) });
}
function renderTopics() {
  const container = $('topic-shortcuts');
  container.replaceChildren();
  for (const topic of catalog.topics || []) {
    const button = el('button', 'topic-shortcut');
    button.type = 'button';
    button.dataset.topicId = topic.id;
    button.setAttribute('aria-pressed', String(state.topic === topic.id));
    button.append(el('span', '', topic.title[locale]), el('small', '', topic.record_ids.length));
    button.addEventListener('click', () => {
      state = { ...defaults(), topic: topic.id };
      syncControls(); update();
    });
    container.append(button);
  }
}
async function loadCatalog() {
  loadFailed = false;
  $('error-state').hidden = true;
  $('empty-state').hidden = true;
  $('results').setAttribute('aria-busy', 'true');
  try {
    const response = await fetch('./data/catalog.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error('Catalogue unavailable');
    const data = await response.json();
    if (!Array.isArray(data.records) || !Array.isArray(data.sources) || !data.records.every(r => r && typeof r.id === 'string' && typeof r.title === 'string' && typeof r.source === 'string')) throw new Error('Invalid catalogue');
    catalog = data;
    readURL();
    renderFilters();
    renderSourceSummary();
    renderTopics();
    syncControls();
    update({ save: false });
    const requested = data.records.find(record => record.id === new URLSearchParams(location.search).get('record'));
    if (requested) openRecord(requested, { save: false });
  } catch {
    catalog = null;
    loadFailed = true;
    $('results').replaceChildren();
    $('results').setAttribute('aria-busy', 'false');
    $('results-bottom').hidden = true;
    $('error-state').hidden = false;
    $('updated-date').textContent = t('样本载入失败');
    $('result-announcement').textContent = t('目录样本载入失败，可点击重新载入。');
  }
}
function changeLanguage(value, { save = true } = {}) {
  locale = normalizeLocale(value) || locale;
  applyPageLanguage(locale);
  $('language').value = locale;
  try { localStorage.setItem(LANGUAGE_KEY, locale); } catch { /* Storage may be disabled. */ }
  if (catalog) {
    const draftQuery = $('query').value;
    renderFilters();
    for (const input of document.querySelectorAll('input[data-kind]')) input.checked = state[input.dataset.kind].includes(input.value);
    renderSourceSummary();
    renderTopics();
    update({ save: false, resetPage: false });
    $('query').value = draftQuery;
    if ($('detail-dialog').open && selectedRecord) openRecord(selectedRecord, { save: false });
  } else if (loadFailed) {
    $('updated-date').textContent = t('样本载入失败');
    $('result-announcement').textContent = t('目录样本载入失败，可点击重新载入。');
  }
  if (save) {
    const url = new URL(location.href);
    url.searchParams.set('lang', locale);
    history.pushState(null, '', `${url.pathname}${url.search}${url.hash}`);
  }
  updatePageLinks(locale);
}
$('language').addEventListener('change', () => changeLanguage($('language').value));

function reset(keepQuery = false) {
  const query = keepQuery ? state.query : '';
  state = { ...defaults(), query };
  syncControls();
  update();
}
$('search-form').addEventListener('submit', e => {
  e.preventDefault();
  state.query = $('query').value.trim();
  update();
});
document.querySelectorAll('[data-query]').forEach(button => button.addEventListener('click', () => {
  state.query = locale === 'en' ? button.dataset.queryEn : button.dataset.query;
  $('query').value = state.query;
  update();
}));
$('reset-filters').addEventListener('click', () => reset(true));
$('clear-all').addEventListener('click', () => reset());
for (const [id, name] of [['start-year', 'startYear'], ['end-year', 'endYear']]) {
  $(id).addEventListener('input', () => { state[name] = $(id).value; update({ save: false }); });
  $(id).addEventListener('change', () => { state[name] = $(id).value; update(); });
}
$('unknown-dates').addEventListener('change', () => { state.includeUnknownDates = $('unknown-dates').checked; update(); });
document.querySelectorAll('input[name="access"]').forEach(n => n.addEventListener('change', () => { state.access = n.value; update(); }));
$('sort').addEventListener('change', () => { state.sort = $('sort').value; update(); });
$('load-more').addEventListener('click', () => {
  const previousCount = visibleCount;
  visibleCount += PAGE_SIZE;
  renderResults();
  $('results').children[previousCount]?.querySelector('button')?.focus({ preventScroll: true });
});
$('retry-button').addEventListener('click', loadCatalog);
$('filter-toggle').addEventListener('click', () => {
  const open = $('filters').classList.toggle('is-open');
  $('filter-toggle').setAttribute('aria-expanded', String(open));
  $('filter-toggle').lastElementChild.textContent = open ? '－' : '＋';
});
$('help-button').addEventListener('click', () => $('help-dialog').showModal());
$('close-help').addEventListener('click', () => $('help-dialog').close());
$('close-detail').addEventListener('click', closeRecord);
$('detail-dialog').addEventListener('cancel', e => { e.preventDefault(); closeRecord(); });
for (const id of ['detail-dialog', 'help-dialog']) $(id).addEventListener('click', e => {
  const rect = $(id).getBoundingClientRect();
  if (e.target === $(id) && (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom)) {
    if (id === 'detail-dialog') closeRecord(); else $(id).close();
  }
});
window.addEventListener('popstate', () => {
  if (catalog) { readURL(); syncControls(); }
  changeLanguage(resolveLocale(new URLSearchParams(location.search).get('lang'), savedLocale(), navigator.languages || [navigator.language]), { save: false });
  const requested = catalog?.records.find(record => record.id === new URLSearchParams(location.search).get('record'));
  if (requested) openRecord(requested, { save: false });
  else { $('detail-dialog').close(); selectedRecord = null; }
});
// Make the initial language explicit so Back restores it even after preferences change.
const initialURL = new URL(location.href);
initialURL.searchParams.set('lang', locale);
history.replaceState(null, '', `${initialURL.pathname}${initialURL.search}${initialURL.hash}`);
changeLanguage(locale, { save: false });
loadCatalog();
