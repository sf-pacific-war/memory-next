import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeText, expandQuery, filterRecords, getRecordYears, formatLabel, sourceLabel } from '../site/search.mjs';

const records = [
  { id: 'a', title: 'Burma Road photographs', description: 'Supply route', source: 'LoC', format: 'IMAGE', year: ['1944'], access_status: 'online' },
  { id: 'b', title: 'Supply report', description: 'Burma Road photographs', source: 'Europeana', format: 'TEXT', year: [], date_display: '1942–1945', access_status: 'unverified' },
  { id: 'c', title: 'インパール', description: 'ビルマ 戦場', source: 'IWM', format: 'MAP', year: [], date_display: null, access_status: 'unverified' },
  { id: 'd', title: 'Chinese Expeditionary Force', description: 'China and Burma', source: 'LoC', format: 'TEXT', date_display: '1950-03-01', access_status: 'online' },
  { id: 'e', title: 'Unrelated record', description: 'Events in 1944', query_used: 'Burma Road', source: 'Europeana', format: 'SOUND', date_display: null },
];
const ids = result => result.map(record => record.id);

test('normalizes full-width characters, case and whitespace', () => {
  assert.equal(normalizeText(' ＢＵＲＭＡ\n  Road '), 'burma road');
  assert.equal(normalizeText(null), '');
  assert.equal(normalizeText('Straße'), 'strasse');
});

test('Chinese topic queries expand to multilingual names with explanatory labels', () => {
  assert.deepEqual(ids(filterRecords(records, { query: '滇缅公路' })), ['a', 'b']);
  assert.deepEqual(ids(filterRecords(records, { query: '英帕尔' })), ['c']);
  assert.deepEqual(ids(filterRecords(records, { query: '中国远征军' })), ['d']);
  assert.ok(expandQuery('缅甸').terms.includes('myanmar'));
  assert.match(expandQuery('滇缅公路').label, /更广/);
});

test('ANDs separate query clauses while preserving quoted phrases and longest aliases', () => {
  assert.deepEqual(ids(filterRecords(records, { query: '"Burma Road" supply' })), ['a', 'b']);
  assert.deepEqual(ids(filterRecords(records, { query: 'Burma Road photographs' })), ['a', 'b']);
  assert.deepEqual(ids(filterRecords(records, { query: '缅甸 China' })), ['d']);
  assert.deepEqual(ids(filterRecords(records, { query: '"Road Burma"' })), []);
  assert.equal(expandQuery('unknown').label, null);
});

test('combines facets with OR within a facet and AND across facets', () => {
  assert.deepEqual(ids(filterRecords(records, { sources: ['LoC', 'IWM'], types: ['IMAGE', 'MAP'], access: 'online' })), ['a']);
  assert.deepEqual(ids(filterRecords(records, { sources: ['Europeana'], access: 'unverified' })), ['b', 'e']);
});

test('dates use explicit metadata only, recognize spans, and never infer from descriptions', () => {
  assert.deepEqual(getRecordYears(records[1]), { start: 1942, end: 1945 });
  assert.deepEqual(getRecordYears(records[3]), { start: 1950, end: 1950 });
  assert.deepEqual(getRecordYears(records[4]), { start: null, end: null });
  assert.deepEqual(getRecordYears({ date_display: 'Battle of Burma, 1944' }), { start: null, end: null });
  assert.deepEqual(getRecordYears({ year: ['1945', '1941'], date_display: '1950' }), { start: 1941, end: 1945 });
});

test('range overlap includes unknown dates by default and can explicitly exclude them', () => {
  assert.deepEqual(ids(filterRecords(records, { startYear: '1943', endYear: '1943' })), ['b', 'c', 'e']);
  assert.deepEqual(ids(filterRecords(records, { startYear: '1943', endYear: '1943', includeUnknownDates: false })), ['b']);
  assert.deepEqual(filterRecords(records, { startYear: '1950', endYear: '1940' }), []);
});

test('sorts chronologically with unknowns last and ranks title matches over descriptions', () => {
  assert.deepEqual(ids(filterRecords(records, { sort: 'newest' })), ['d', 'b', 'a', 'c', 'e']);
  assert.deepEqual(ids(filterRecords(records, { sort: 'oldest' })), ['b', 'a', 'd', 'c', 'e']);
  assert.deepEqual(ids(filterRecords([...records].reverse(), { query: '滇缅公路' })), ['a', 'b']);
  assert.deepEqual(ids(filterRecords(records)), ['a', 'b', 'c', 'd', 'e']);
});

test('returns zero results without matching collection query labels; never mutates records', () => {
  const copy = structuredClone(records);
  assert.deepEqual(filterRecords(records, { query: 'not-present-anywhere' }), []);
  assert.deepEqual(filterRecords([records[4]], { query: 'Burma Road' }), []);
  filterRecords(records, { sort: 'newest' });
  assert.deepEqual(records, copy);
});

test('provides Chinese labels and preserves unknown source names', () => {
  assert.equal(formatLabel('IMAGE'), '图像');
  assert.equal(formatLabel('MIXED'), '综合资料');
  assert.equal(formatLabel('unknown'), '其他');
  assert.equal(sourceLabel('LoC'), '美国国会图书馆');
  assert.equal(sourceLabel('IWM'), '英国帝国战争博物馆');
  assert.equal(sourceLabel('Europeana'), '欧洲数字文化遗产');
  assert.equal(sourceLabel('NARA'), '美国国家档案馆');
  assert.equal(sourceLabel('Other Archive'), 'Other Archive');
});

test('switches presentation labels to English without translating unknown source names', () => {
  assert.equal(formatLabel('image', 'en'), 'Image');
  assert.equal(formatLabel('MIXED', 'en'), 'Mixed material');
  assert.equal(formatLabel('unknown', 'en'), 'Other');
  assert.equal(sourceLabel('LoC', 'en'), 'Library of Congress');
  assert.equal(sourceLabel('IWM', 'en'), 'Imperial War Museums');
  assert.equal(sourceLabel('Europeana', 'en'), 'Europeana');
  assert.equal(sourceLabel('NARA', 'en'), 'U.S. National Archives');
  assert.equal(sourceLabel(null, 'en'), 'Unknown source');
  assert.equal(sourceLabel('Other Archive', 'en'), 'Other Archive');
});

test('topic explanations translate while expanded search terms and original records remain unchanged', () => {
  const original = structuredClone(records);
  for (const query of ['滇缅公路', '缅甸', '英帕尔', '中国远征军', 'Burma Road Imphal']) {
    const chinese = expandQuery(query, 'zh-CN');
    const english = expandQuery(query, 'en');
    assert.deepEqual(english.terms, chinese.terms);
    assert.notEqual(english.label, chinese.label);
    for (const record of filterRecords(records, { query })) {
      sourceLabel(record.source, 'en');
      formatLabel(record.format, 'en');
      assert.equal(record, records.find(item => item.id === record.id));
    }
  }
  assert.match(expandQuery('滇缅公路', 'en').label, /broader aid routes/);
  assert.match(expandQuery('缅甸', 'en').label, /historical period/);
  assert.equal(expandQuery('unknown', 'en').label, null);
  assert.deepEqual(records, original);
});

test('institution and material names are searchable in both interface languages', () => {
  for (const query of ['美国国会图书馆', 'Library of Congress', '"Library of Congress"']) {
    assert.deepEqual(ids(filterRecords(records, { query })), ['a', 'd']);
  }
  for (const query of ['英国帝国战争博物馆', 'Imperial War Museums']) {
    assert.deepEqual(ids(filterRecords(records, { query })), ['c']);
  }
  assert.deepEqual(ids(filterRecords(records, { query: 'Library of Congress 图像' })), ['a']);
  assert.deepEqual(ids(filterRecords(records, { query: '美国国会图书馆 Image' })), ['a']);
});

test('NARA matches genuine archival context while retaining source and date filters', () => {
  const nara = { id: 'nara:123', source: 'NARA', title: 'Weekly Reports', format: 'TEXT',
    year: ['1943', '1945'], archival_context: ['Records of U.S. Army Forces in the China-Burma-India Theaters of Operations'] };
  assert.deepEqual(ids(filterRecords([...records, nara], { query: '缅甸', sources: ['NARA'], startYear: '1944', endYear: '1944' })), ['nara:123']);
  assert.deepEqual(filterRecords([nara], { query: '滇缅公路' }), []);
});
