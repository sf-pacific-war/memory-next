import { filterRecords, expandQuery, formatLabel, sourceLabel } from './search.mjs';

const $ = (id) => document.getElementById(id);
const PAGE_SIZE = 10;
const defaults = () => ({ query: '', sources: [], types: [], access: 'all', startYear: '', endYear: '', includeUnknownDates: true, sort: 'relevance' });
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
  return value && !Number.isNaN(date.valueOf()) ? date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }) : '日期未提供';
}
function languageLabel(record) {
  const names = { eng: '英语', en: '英语', english: '英语', jpn: '日语', ja: '日语', japanese: '日语', fr: '法语', fre: '法语', fra: '法语', french: '法语', chi: '中文', zho: '中文', zh: '中文', dut: '荷兰语', nld: '荷兰语' };
  return [...new Set(list(record.language).map(v => names[v.toLowerCase()] || v))].join('、') || '语种未标注';
}
function readURL() {
  const params = new URLSearchParams(location.search);
  state = defaults();
  state.query = (params.get('q') || '').slice(0, 240);
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
  if (state.query) params.set('q', state.query);
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
  document.querySelectorAll('[data-query]').forEach(n => { n.setAttribute('aria-pressed', String(n.dataset.query === state.query)); });
}
function validDates() {
  const validYear = value => value === '' || (/^\d{4}$/.test(value) && Number(value) >= 1000 && Number(value) <= 2100);
  let error = '';
  if (!validYear(state.startYear) || !validYear(state.endYear)) error = '请输入 1000–2100 之间的四位年份。';
  else if (state.startYear && state.endYear && Number(state.startYear) > Number(state.endYear)) error = '起始年份不能晚于结束年份。';
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
    button.setAttribute('aria-label', `移除筛选：${text}`);
    button.addEventListener('click', () => { remove(); syncControls(); update(); });
    container.append(button);
  }
  if (state.query) chip(`“${state.query}”`, () => { state.query = ''; });
  state.sources.forEach(v => chip(sourceLabel(v), () => { state.sources = state.sources.filter(x => x !== v); }));
  state.types.forEach(v => chip(formatLabel(v), () => { state.types = state.types.filter(x => x !== v); }));
  if (state.startYear || state.endYear) chip(`${state.startYear || '不限'}—${state.endYear || '不限'}`, () => { state.startYear = ''; state.endYear = ''; });
  if (!state.includeUnknownDates) chip('仅有明确日期', () => { state.includeUnknownDates = true; });
  if (state.access !== 'all') chip(state.access === 'online' ? '有在线资源' : '访问条件待确认', () => { state.access = 'all'; });
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
  div.append(el('span', '', ['IMAGE', 'TEXT', 'SOUND', 'MAP', 'VIDEO'].includes(type) ? type : 'RECORD'));
  return div;
}
function recordCard(record, index) {
  const article = el('article', 'record-card');
  const content = el('div', 'record-content');
  const top = el('div', 'record-top');
  top.append(el('span', 'record-source', `${record.source} / ${sourceLabel(record.source)}`), el('span', 'record-number', String(index + 1).padStart(3, '0')));
  const title = el('h3', 'record-title');
  const button = el('button', '', record.title || '未提供标题');
  button.type = 'button';
  button.addEventListener('click', () => openRecord(record));
  title.append(button);
  const meta = el('div', 'record-meta');
  [record.date_display || '日期不详', formatLabel(record.format), languageLabel(record)].forEach((value, i) => {
    if (i) meta.append(el('span', 'meta-dot', '·'));
    meta.append(el('span', '', value));
  });
  const description = el('p', 'record-description', record.description || '原目录未提供摘要，可前往来源页面查看完整记录。');
  const bottom = el('div', 'record-bottom');
  bottom.append(el('span', `access-badge${record.access_status === 'online' ? ' online' : ''}`, record.access_status === 'online' ? '有在线资源' : '访问条件待确认'));
  const original = link('原馆记录 ↗', record.source_url, 'record-link');
  if (original) bottom.append(original);
  content.append(top, title, meta);
  if (record.record_group) content.append(el('p', 'record-context', `档案组 RG ${record.record_group} · ${list(record.archival_context)[0] || '查看详情了解档案层级'}`));
  content.append(description, bottom);
  article.append(typeVisual(record.format), content);
  return article;
}
function renderResults() {
  const shown = filtered.slice(0, visibleCount);
  $('results').replaceChildren(...shown.map(recordCard));
  $('results-heading').firstChild.textContent = state.query ? '检索结果 ' : '全部资料 ';
  $('result-count').textContent = filtered.length;
  $('empty-state').hidden = filtered.length !== 0;
  $('results-bottom').hidden = filtered.length === 0;
  $('shown-count').textContent = `已显示 ${shown.length} / ${filtered.length} 条资料`;
  $('load-more').hidden = shown.length >= filtered.length;
  $('result-announcement').textContent = `找到 ${filtered.length} 条目录样本，已显示 ${shown.length} 条。`;
  $('results').setAttribute('aria-busy', 'false');
}
function update({ save = true, resetPage = true } = {}) {
  if (!catalog) return;
  if (resetPage) visibleCount = PAGE_SIZE;
  const valid = validDates();
  filtered = valid ? filterRecords(catalog.records, state) : [];
  renderChips();
  const expanded = expandQuery(state.query);
  $('expansion-note').hidden = !expanded.label;
  $('expansion-note').textContent = expanded.label ? `${expanded.label}。检索词：${expanded.terms.join(' / ')}` : '';
  renderResults();
  if (!valid) {
    $('empty-state').hidden = true;
    $('result-announcement').textContent = $('date-error').textContent;
  }
  document.querySelectorAll('[data-query]').forEach(n => { n.setAttribute('aria-pressed', String(n.dataset.query === state.query)); });
  if (save) writeURL();
}
function openRecord(record) {
  const container = $('detail-content');
  container.replaceChildren();
  const title = el('h2', '', record.title || '未提供标题');
  title.id = 'detail-title';
  container.append(el('p', 'eyebrow', `${record.source} / ${sourceLabel(record.source)}`), title, el('p', 'detail-description', record.description || '原目录未提供描述。'));
  const grid = el('dl', 'detail-grid');
  const fields = [
    ['收藏机构', list(record.holding_institution).join('；') || '原记录未标注'],
    ['元数据提供方', list(record.metadata_provider).join('；') || sourceLabel(record.source)],
    ['目录日期', record.date_display || '日期不详'],
    ['资料类型 / 语种', `${formatLabel(record.format)} / ${languageLabel(record)}`],
    ['访问状态', record.access_status === 'online' ? '来源标有在线数字资源；实际访问条件以原馆为准。' : '只有目录或聚合记录，尚未确认公开全文／媒体访问。'],
    ['主题词', list(record.subjects).join(' · ') || '原记录未提供'],
    ['元数据许可', record.metadata_rights || '此记录未单独提供许可，请核对来源条款。'],
    ['原件权利说明', list(record.content_rights).join('\n') || '未提供；不代表无版权限制。'],
    ['来源记录编号', record.source_id || record.id],
    ['样本获取时间', formatDate(record.retrieved_at)],
  ];
  if (record.level_of_description) {
    const levels = { recordGroup: '档案组', collection: '集合', series: '系列', fileUnit: '案卷', item: '单件' };
    fields.splice(2, 0, ['目录层级', levels[record.level_of_description] || record.level_of_description]);
  }
  if (record.record_group) fields.push(['档案组', `RG ${record.record_group}`]);
  if (list(record.archival_context).length) fields.push(['所属档案背景（参与检索）', list(record.archival_context).join('\n')]);
  if (record.dataset_updated_at) fields.push(['公开数据文件更新时间', formatDate(record.dataset_updated_at)]);
  for (const [name, value] of fields) {
    const row = el('div');
    row.append(el('dt', '', name), el('dd', '', value));
    grid.append(row);
  }
  container.append(grid, el('p', 'detail-note', '本条为待核对的目录候选。目录日期可能是创作或出版日期；战后回忆录的出版年份不表示事件发生年份。元数据许可不等于图片、音频或全文的使用许可。'));
  if (record.source === 'NARA') container.append(el('p', 'detail-note', 'NARA 记录来自官方开放数据集。系列和档案组记录可能描述多份材料；命中所属档案背景不等于每个下属文件都讨论该关键词。数字目录可访问，不代表原件已数字化。'));
  const links = el('div', 'detail-links');
  const original = link('前往原馆记录 ↗', record.source_url, 'primary-button');
  if (original) links.append(original);
  if (record.aggregator_url !== record.source_url) {
    const aggregator = link('查看聚合目录 ↗', record.aggregator_url, 'secondary-button');
    if (aggregator) links.append(aggregator);
  }
  if (record.dataset_url) {
    const dataset = link('公开数据文件 ↗', record.dataset_url, 'secondary-button');
    if (dataset) links.append(dataset);
  }
  container.append(links);
  $('detail-dialog').showModal();
  $('detail-dialog').scrollTop = 0;
}
function renderSources() {
  $('source-cards').replaceChildren();
  for (const source of catalog.sources) {
    const card = el('article', 'source-card');
    const heading = el('div', 'source-card-heading');
    heading.append(el('span', 'source-abbr', source.id === 'Europeana' ? 'EUROPEANA' : source.id.toUpperCase()), el('span', `source-state${source.count ? '' : ' unavailable'}`, source.count ? `${source.count} 条样本` : '暂未接入'));
    card.append(heading, el('h3', '', source.label || sourceLabel(source.id)), el('p', '', source.description || '公开目录元数据样本。'));
    const url = link('访问来源网站 ↗', source.url);
    if (url) card.append(url);
    $('source-cards').append(card);
  }
  $('scope-note').textContent = `样本范围说明：当前索引包含 ${catalog.records.length} 条真实目录记录，经过初步排除同名误命中；仍需逐条核对史料相关性。NDL 样本包括战后出版的回忆录与研究书目。更多结果需在原馆继续检索。`;
  $('sample-count').textContent = catalog.records.length;
  $('source-count').textContent = catalog.sources.filter(s => s.count > 0).length;
  const dates = catalog.sources.map(s => s.fetched_at).filter(Boolean).sort();
  $('updated-date').textContent = `样本更新 ${formatDate(dates.at(-1))}`;
}
async function loadCatalog() {
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
    renderSources();
    syncControls();
    update({ save: false });
  } catch {
    catalog = null;
    $('results').replaceChildren();
    $('results').setAttribute('aria-busy', 'false');
    $('results-bottom').hidden = true;
    $('error-state').hidden = false;
    $('updated-date').textContent = '样本载入失败';
    $('result-announcement').textContent = '目录样本载入失败，可点击重新载入。';
  }
}
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
  state.query = button.dataset.query;
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
$('close-detail').addEventListener('click', () => $('detail-dialog').close());
for (const id of ['detail-dialog', 'help-dialog']) $(id).addEventListener('click', e => {
  const rect = $(id).getBoundingClientRect();
  if (e.target === $(id) && (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom)) $(id).close();
});
window.addEventListener('popstate', () => { if (catalog) { readURL(); syncControls(); update({ save: false }); } });
loadCatalog();
