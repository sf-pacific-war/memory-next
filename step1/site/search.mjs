/** Pure, dependency-free helpers for the local discovery sample. */
export function normalizeText(value) {
  return String(value ?? '').normalize('NFKC').toLocaleLowerCase('und')
    .replace(/ß/g, 'ss').replace(/ς/g, 'σ').replace(/\s+/gu, ' ').trim();
}

const TOPICS = [
  { aliases: ['滇缅公路', '滇緬公路', 'Burma Road', 'ビルマ公路', '援蒋ルート'], label: '滇缅公路：跨语言扩展；“援蒋ルート”含更广的援助路线' },
  { aliases: ['缅甸', '緬甸', 'Burma', 'Myanmar', 'ビルマ', 'ミャンマー'], label: '缅甸：含 Burma、Myanmar 与日文别名，跨时期名称需核对' },
  { aliases: ['英帕尔', '英帕爾', 'Imphal', 'インパール'], label: '英帕尔：中英日地名扩展' },
  { aliases: ['中国远征军', '中國遠征軍', 'Chinese Expeditionary Force', '中国遠征軍'], label: '中国远征军：中英日名称扩展' },
].map(topic => ({ ...topic, terms: topic.aliases.map(normalizeText) }));

function clausesFor(query) {
  const normalized = normalizeText(query);
  const tokens = [...normalized.matchAll(/"([^"]+)"|'([^']+)'|(\S+)/gu)]
    .map(match => ({ value: match[1] ?? match[2] ?? match[3], quoted: Boolean(match[1] ?? match[2]) }));
  const clauses = [];
  for (let i = 0; i < tokens.length;) {
    let found = null;
    let consumed = 1;
    // Prefer the longest matching alias: Burma Road must not become Burma AND Road.
    for (let n = Math.min(4, tokens.length - i); n >= 1; n--) {
      if (n > 1 && tokens.slice(i, i + n).some(token => token.quoted)) continue;
      const value = tokens.slice(i, i + n).map(token => token.value).join(' ');
      const topic = TOPICS.find(candidate => candidate.terms.includes(value));
      if (topic) { found = topic; consumed = n; break; }
    }
    clauses.push(found ? { terms: found.terms, label: found.label } : { terms: [tokens[i].value], label: null });
    i += consumed;
  }
  return clauses;
}

export function expandQuery(query) {
  const clauses = clausesFor(query);
  return {
    terms: [...new Set(clauses.flatMap(clause => clause.terms))],
    label: [...new Set(clauses.map(clause => clause.label).filter(Boolean))].join('；') || null,
  };
}

function parseDate(value) {
  const text = normalizeText(value);
  let match = text.match(/^\[?(\d{4})\]?年?$/u);
  if (match) return [Number(match[1]), Number(match[1])];
  match = text.match(/^(\d{4})\s*(?:-|–|—|\/|至|到)\s*(\d{4})年?$/u);
  if (match && Number(match[1]) <= Number(match[2])) return [Number(match[1]), Number(match[2])];
  match = text.match(/^(\d{4})-(\d{2})(?:-(\d{2}))?$/u);
  if (match && Number(match[2]) >= 1 && Number(match[2]) <= 12 && (!match[3] || (Number(match[3]) >= 1 && Number(match[3]) <= 31))) {
    return [Number(match[1]), Number(match[1])];
  }
  return null;
}

export function getRecordYears(record) {
  const rawYears = Array.isArray(record.year) ? record.year : record.year == null ? [] : [record.year];
  const spans = rawYears.map(parseDate).filter(Boolean);
  if (spans.length) return { start: Math.min(...spans.map(span => span[0])), end: Math.max(...spans.map(span => span[1])) };
  const fallback = parseDate(record.date_display);
  return { start: fallback?.[0] ?? null, end: fallback?.[1] ?? null };
}

export function formatLabel(type) {
  return ({ IMAGE: '图像', TEXT: '文献', MAP: '地图', SOUND: '音频', VIDEO: '影像', MIXED: '综合资料' })[String(type ?? '').toUpperCase()] ?? '其他';
}

export function sourceLabel(source) {
  return ({ loc: '美国国会图书馆', ndl: '日本国会图书馆', europeana: '欧洲数字文化遗产', nara: '美国国家档案馆' })[normalizeText(source)] ?? String(source ?? '未知来源');
}

function fieldText(value) {
  return normalizeText(Array.isArray(value) ? value.map(fieldText).join(' ') : value);
}

function searchFields(record) {
  return [fieldText(record.title), fieldText(record.description), fieldText([
    record.source, record.source_id, record.holding_institution, record.metadata_provider,
    record.subject, record.subjects, record.archival_context, record.place, record.language, record.date_display,
    record.format, sourceLabel(record.source), formatLabel(record.format),
  ])];
}

export function filterRecords(records, options = {}) {
  const { query = '', sources = [], types = [], access = 'all', startYear = '', endYear = '', includeUnknownDates = true, sort = 'relevance' } = options;
  const clauses = clausesFor(query);
  const chosenSources = sources.map(normalizeText);
  const chosenTypes = types.map(normalizeText);
  const lower = /^\d{4}$/.test(String(startYear)) ? Number(startYear) : -Infinity;
  const upper = /^\d{4}$/.test(String(endYear)) ? Number(endYear) : Infinity;
  if (lower > upper) return [];
  const matches = [];
  records.forEach((record, index) => {
    if (chosenSources.length && !chosenSources.includes(normalizeText(record.source))) return;
    if (chosenTypes.length && !chosenTypes.includes(normalizeText(record.format))) return;
    if (access !== 'all' && (record.access_status ?? 'unverified') !== access) return;
    const years = getRecordYears(record);
    if (years.start === null ? !includeUnknownDates : years.end < lower || years.start > upper) return;
    const fields = searchFields(record);
    let score = 0;
    for (const clause of clauses) {
      const firstMatch = fields.findIndex(field => clause.terms.some(term => field.includes(term)));
      if (firstMatch === -1) return;
      score += [100, 30, 10][firstMatch];
    }
    matches.push({ record, index, years, score });
  });
  matches.sort((a, b) => {
    if (sort === 'newest' || sort === 'oldest') {
      if (a.years.start === null || b.years.start === null) {
        if (a.years.start !== b.years.start) return a.years.start === null ? 1 : -1;
      } else {
        const delta = sort === 'newest' ? b.years.end - a.years.end : a.years.start - b.years.start;
        if (delta) return delta;
      }
    } else if (a.score !== b.score) return b.score - a.score;
    return a.index - b.index;
  });
  return matches.map(match => match.record);
}
