import { bindPageTranslations, resolveLocale, normalizeLocale } from './i18n.mjs';
import { sourceLabel, formatLabel, filterRecords } from './search.mjs';
import { updatePageLinks } from './page-links.mjs';
import { archivalThumbnail, referenceMatches } from './cbi-demo.mjs';

const $ = id => document.getElementById(id);
const applyPageLanguage = bindPageTranslations(document);
const LANGUAGE_KEY = 'pacific-war-discovery-language';
let saved;
try { saved = localStorage.getItem(LANGUAGE_KEY); } catch {}
let locale = resolveLocale(new URLSearchParams(location.search).get('lang'), saved, navigator.languages);
let data = null, archiveLimit = 12, inventoryLimit = 40;
const tx = (en, zh) => locale === 'en' ? en : zh;
const node = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = String(text); return e; };
const statuses = {
  exact_item: ['Exact item', '同一件'], same_work: ['Same work', '同一作品'], related: ['Related material', '主题相关'],
  keyword_lead: ['Keyword lead only', '仅关键词线索'], not_reviewed: ['Not yet reviewed', '尚未核对'], unverified: ['Unverified', '待确认'],
  ok: ['Access verified', '接入通过'], missing_credential: ['Credential needed', '缺少凭据'], permission_required: ['Approval needed', '待访问审批'],
  query_not_supported: ['No keyword search on this route', '此方式不支持关键词'], manual_only: ['Web research only', '仅网页查找'],
  not_fetched: ['Page not fetched', '页面未读取'], not_requested: ['Media not requested', '未请求媒体'],
};
const label = status => statuses[status] ? tx(...statuses[status]) : status;
const material = kind => ({ page: tx('Page', '页面'), image: tx('Image reference', '图片引用'), document: tx('Document reference', '文档引用'), other_link: tx('Other reference', '其他引用'), photograph: tx('Photograph', '照片'), book: tx('Book / guide', '书籍／指南'), map: tx('Map', '地图'), personal_narrative: tx('Personal account', '个人叙述'), artifact: tx('Artifact', '实物'), article: tx('Article', '文章'), film: tx('Film', '影片'), newspaper: tx('Newspaper', '报刊'), audio: tx('Audio', '音频') }[kind] || kind);
const routeNames = { loc: '美国国会图书馆', ndl: '日本国立国会图书馆', europeana: '欧洲数字文化遗产平台', nara: '美国国家档案馆公开数据集', nara_catalog: '美国国家档案馆目录 API', dpla: '美国数字公共图书馆', tna: '英国国家档案馆', jacar: '日本亚洲历史资料中心', iwm: '英国帝国战争博物馆', taiwan: '台湾档案管理局' };
function anchor(text, value, cls) {
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return node('span', cls, text);
    const a = node('a', cls, text); a.href = url.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a;
  } catch { return node('span', cls, text); }
}
function preview(title, thumbnail, url, kind) {
  const box = anchor(tx(`Open archival record: ${title}`, `打开档案记录：${title}`), url, 'record-preview');
  box.replaceChildren();
  box.setAttribute('aria-label', tx(`Open archival record: ${title}`, `打开档案记录：${title}`));
  const fallback = node('span', 'demo-preview-fallback', tx('No archive preview available', '档案机构未提供预览'));
  box.append(fallback, node('span', 'preview-type', kind));
  const src = archivalThumbnail(thumbnail);
  if (src) {
    const img = node('img', 'record-thumbnail'); img.alt = ''; img.loading = 'lazy'; img.decoding = 'async'; img.referrerPolicy = 'no-referrer';
    fallback.textContent = tx('Loading archive preview…', '正在载入档案预览…');
    img.addEventListener('load', () => { img.classList.add('is-loaded'); fallback.hidden = true; }, { once: true });
    img.addEventListener('error', () => { img.remove(); fallback.textContent = tx('Archive preview unavailable', '档案预览暂不可用'); }, { once: true });
    img.src = src; box.append(img);
  }
  return box;
}
function details(summary, fields) {
  const d = node('details', 'demo-evidence'); d.append(node('summary', '', summary));
  for (const [name, value] of fields) {
    if (value == null || value === '' || (Array.isArray(value) && !value.length)) continue;
    const p = node('p'); p.append(node('strong', '', name + ': '), document.createTextNode(Array.isArray(value) ? value.join(' / ') : String(value))); d.append(p);
  }
  return d;
}
function renderComparisons() {
  $('comparison-count').textContent = data.comparisons.length + tx(' comparisons', ' 条对照');
  $('comparison-grid').replaceChildren(...data.comparisons.map(r => {
    const card = node('article', 'record-card comparison-card'); card.id = r.id;
    const source = locale === 'en' ? r.source_name_en || r.source : `${r.source_name_zh || r.source} (${r.source})`;
    const content = node('div', 'record-content');
    const top = node('div', 'record-top'); top.append(node('span', 'record-source', source), node('span', 'match-status ' + r.match_status, label(r.match_status)));
    const h = node('h3', 'record-title'); h.append(anchor(r.archival_title, r.archival_url));
    content.append(top, h, node('p', 'record-description', (locale !== 'en' && r.evidence_zh) || r.evidence));
    content.append(details(tx('Evidence & next check', '证据与下一步'), [[tx('Evidence', '证据'), (locale !== 'en' && r.evidence_zh) || r.evidence], [tx('Archive ID', '档案编号'), r.archival_id], [tx('Checked', '核对时间'), r.checked_at], [tx('Access', '访问'), r.access_note], [tx('Rights', '权利说明'), r.rights_note], [tx('Next check', '下一步'), (locale !== 'en' && r.next_step_zh) || r.next_step]]));
    const links = node('div', 'comparison-links'); links.append(anchor(tx('Reference: ', '参考：') + r.cbi_page_title, r.cbi_page_url), anchor(tx('Open archive ↗', '打开档案机构 ↗'), r.archival_url, 'record-link'));
    content.append(links); card.append(preview(r.archival_title, r.thumbnail_url, r.archival_url, material(r.material_type)), content); return card;
  }));
}
function renderArchives() {
  const source = $('archive-source').value;
  const records = filterRecords(data.records, { query: $('archive-query').value, sources: source ? [source] : [], types: [], access: 'all', includeUnknownDates: true, sort: 'relevance' });
  $('archive-count').textContent = `${Math.min(records.length, archiveLimit)} / ${records.length}`;
  $('archive-empty').hidden = !!records.length; $('archive-more').hidden = records.length <= archiveLimit;
  $('archive-grid').replaceChildren(...records.slice(0, archiveLimit).map(r => {
    const card = node('article', 'record-card'); const content = node('div', 'record-content');
    const h = node('h3', 'record-title'); h.append(anchor(r.title, r.source_url));
    content.append(node('div', 'record-source', sourceLabel(r.source, locale)), h, node('p', 'record-meta', `${r.date_display || tx('Date unknown', '日期不详')} · ${formatLabel(r.format, locale)}`), node('p', 'record-description', r.description || tx('No description supplied.', '未提供描述。')));
    content.append(details(tx('Full metadata & provenance', '完整元数据与出处'), [[tx('Title', '标题'), r.title], [tx('Description', '描述'), r.description], [tx('Source ID', '来源编号'), r.source_id], [tx('Query', '获取查询'), r.query_used], [tx('Retrieved', '获取时间'), r.retrieved_at], [tx('Metadata licence', '元数据许可'), r.metadata_rights], [tx('Content rights', '原件权利'), r.content_rights?.length ? r.content_rights : tx('Not supplied; check the archive.', '未提供，请核对原馆。')]]));
    const bottom = node('div', 'record-bottom'); bottom.append(node('span', 'access-badge', tx('Research candidate', '研究候选')), anchor(tx('Open archive ↗', '打开档案机构 ↗'), r.source_url, 'record-link')); content.append(bottom);
    card.append(preview(r.title, r.thumbnail_url, r.source_url, formatLabel(r.format, locale)), content); return card;
  }));
}
function renderInventory() {
  const items = data.items.filter(i => referenceMatches(i, $('inventory-query').value, $('inventory-kind').value, $('inventory-status').value));
  $('inventory-count').textContent = `${Math.min(items.length, inventoryLimit)} / ${items.length}`;
  $('inventory-empty').hidden = !!items.length; $('inventory-more').hidden = items.length <= inventoryLimit;
  const records = new Map(data.records.map(r => [r.id, r]));
  $('inventory-list').replaceChildren(...items.slice(0, inventoryLimit).map(item => {
    const row = node('details', 'inventory-item');
    const summary = node('summary'); summary.append(node('span', 'inventory-kind', material(item.kind)), node('span', 'inventory-title', item.title), node('span', 'match-status ' + item.review_status, label(item.review_status))); row.append(summary);
    const body = node('div', 'inventory-body'); body.append(node('p', 'inventory-address', item.url), node('p', '', tx('Retrieval: ', '读取状态：') + label(item.fetch_status)));
    if (item.reference_url) body.append(anchor(tx('Open reference page ↗', '打开参考页面 ↗'), item.reference_url));
    for (const id of item.comparison_ids || []) { const r = data.comparisons.find(m => m.id === id); if (r) body.append(anchor(tx('Reviewed comparison: ', '已核对线索：') + r.archival_title, r.archival_url)); }
    for (const id of item.candidate_ids || []) { const r = records.get(id); if (r) body.append(anchor(tx('Unverified title lead: ', '标题候选（待核实）：') + r.title, r.source_url)); }
    for (const url of item.archive_citations || []) body.append(anchor(tx('Archive link cited on reference page ↗', '参考页引用的档案链接 ↗'), url));
    if (!item.comparison_ids?.length && !item.candidate_ids?.length) body.append(node('p', '', tx('No item-level match established. Check creator, date, identifier and edition against the archive.', '尚未建立单件对应关系。请在原馆核对作者、日期、编号与版本。')));
    row.append(body); return row;
  }));
}
function renderOverview() {
  const c = data.coverage;
  $('demo-stats').replaceChildren(...[[c.menu_items, tx('Homepage references', '首页参考入口')], [c.pages_successful, tx('Pages inventoried', '已读取页面')], [c.unique_image_urls, tx('Image URLs identified', '已登记图片引用')], [data.records.length, tx('Archive sample records', '档案样本记录')]].map(([count, caption]) => { const d = node('div'); d.append(node('strong', '', count || 0), node('span', '', caption)); return d; }));
  const date = (data.updated_at || '').slice(0, 10);
  const matched = data.comparisons.filter(r => ['exact_item', 'same_work'].includes(r.match_status)).length;
  $('coverage-note').textContent = tx(`Inventory snapshot ${date}: ${c.menu_pages_successful || 0}/${c.menu_items || 0} homepage targets read; ${c.unvisited_pages || 0} discovered pages pending. ${matched} reviewed comparisons identify the same work/item. Every other reference remains a lead or awaits review. ${c.crawl_complete ? 'The configured crawl frontier is exhausted; unlinked material is outside its scope.' : 'Website inventory is incomplete; this is not an exhaustive item-by-item verification.'}`, `清单快照 ${date}：已读取 ${c.menu_pages_successful || 0}/${c.menu_items || 0} 个首页入口；尚有 ${c.unvisited_pages || 0} 个已发现页面待读取。${matched} 条对照识别为同一作品／单件，其余仍为线索或待复核。${c.crawl_complete ? '已遍历配置范围内的链接，未链接材料不在范围内。' : '网站清单尚未穷尽，不代表全站逐件核实已完成。'}`);
  $('access-list').replaceChildren(...data.access.map(a => {
    const row = node('article', 'access-entry'); const nara = a.source === 'nara' && data.nara_dataset_access?.status === 'ok';
    row.append(node('strong', '', locale === 'en' ? a.name || a.source : `${routeNames[a.source] || a.name} (${a.name || a.source})`), node('span', 'match-status', label(nara ? 'ok' : a.status)), node('p', '', tx('Checked: ', '检查时间：') + (nara ? data.nara_dataset_access.checked_at : a.checked_at)));
    if (a.total_results != null) row.append(node('p', '', tx(`“China Burma India”: ${a.total_results} reported hits; identity not verified.`, `“China Burma India”：接口报告 ${a.total_results} 条命中，未核实单件身份。`)));
    if (nara) row.append(node('p', '', tx('Public dataset access verified; this route has no keyword search.', '公开数据集访问通过，此方式不支持关键词检索。')));
    row.append(anchor(tx('Source / documentation ↗', '来源／接口说明 ↗'), a.documentation_url || a.portal_url)); return row;
  }));
  for (const check of data.web_checks?.platforms || []) {
    const row = node('article', 'access-entry');
    row.append(node('strong', '', tx(check.source_en, `${check.source_zh} (${check.source})`)), node('span', 'match-status', tx('Public web research · API not verified', '公开网页查找 · 未验证 API')),
      anchor(check.title, check.url), node('p', '', tx(check.note, check.note_zh)), node('p', '', tx(check.access_note, check.access_note_zh)));
    $('access-list').append(row);
  }
  $('query-list').replaceChildren(...data.queries.map(q => details(`${q.source || ''} · ${q.query || tx('Fixed dataset', '固定数据集')} · ${q.status || ''}`, [
    [tx('Retrieved / checked', '获取／检查时间'), q.retrieved_at || q.fetched_at || q.checked_at],
    [tx('Reported total', '接口报告总数'), q.total_results], [tx('Imported records', '导入条数'), q.imported_count ?? q.returned_count],
    [tx('Outcome', '结果说明'), q.note], [tx('Excluded candidates', '已排除候选'), (q.excluded_records || []).map(r => `${r.title}: ${r.reason}`).join('\n')],
  ])));
}
function setLanguage(value, save = true) {
  locale = normalizeLocale(value) || locale;
  applyPageLanguage(locale);
  document.querySelectorAll('[data-en]').forEach(e => { e.textContent = locale === 'en' ? e.dataset.en : e.dataset.zh; });
  document.title = tx('CBI demo · WWII Pacific War', 'CBI 演示 · WWII Pacific War');
  $('archive-query').placeholder = tx('Flying Tigers, Burma, Ledo…', '飞虎队、Burma、Ledo…');
  $('inventory-query').placeholder = tx('Title, filename, topic…', '标题、文件名、主题…');
  $('language').value = locale;
  $('archive-source').querySelectorAll('option:not([value=""])').forEach(o => { o.textContent = sourceLabel(o.value, locale); });
  try { localStorage.setItem(LANGUAGE_KEY, locale); } catch {}
  if (save) { const url = new URL(location.href); url.searchParams.set('lang', locale); history.pushState(null, '', url); }
  updatePageLinks(locale);
  if (data) { renderOverview(); renderComparisons(); renderArchives(); renderInventory(); }
}
async function load() {
  $('demo-loading').hidden = false; $('demo-error').hidden = true; $('demo-content').hidden = true;
  try {
    const response = await fetch('./data/cbi-demo.json', { cache: 'no-cache' }); if (!response.ok) throw new Error('Unavailable');
    const payload = await response.json();
    if (!payload.coverage || !['records', 'comparisons', 'items', 'access', 'queries'].every(k => Array.isArray(payload[k]))) throw new Error('Invalid data');
    data = payload;
    $('archive-source').querySelectorAll('option:not([value=""])').forEach(o => o.remove());
    for (const source of [...new Set(data.records.map(r => r.source))]) { const o = node('option', '', source); o.value = source; $('archive-source').append(o); }
    setLanguage(locale, false); $('demo-content').hidden = false;
  } catch { data = null; $('demo-error').hidden = false; }
  finally { $('demo-loading').hidden = true; }
}
$('language').addEventListener('change', () => setLanguage($('language').value));
$('demo-retry').addEventListener('click', load);
for (const id of ['archive-query', 'archive-source']) $(id).addEventListener('input', () => { archiveLimit = 12; if (data) renderArchives(); });
for (const id of ['inventory-query', 'inventory-kind', 'inventory-status']) $(id).addEventListener('input', () => { inventoryLimit = 40; if (data) renderInventory(); });
$('archive-more').addEventListener('click', () => { archiveLimit += 12; renderArchives(); });
$('inventory-more').addEventListener('click', () => { inventoryLimit += 40; renderInventory(); });
$('help-button').addEventListener('click', () => $('help-dialog').showModal());
$('close-help').addEventListener('click', () => $('help-dialog').close());
window.addEventListener('popstate', () => setLanguage(resolveLocale(new URLSearchParams(location.search).get('lang'), locale), false));
setLanguage(locale, false); load();
