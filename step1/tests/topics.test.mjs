import test from 'node:test';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import { browseRecords, discoveryLink } from '../site/topics.mjs';
import { pageURL } from '../site/page-links.mjs';
import { filterRecords, expandQuery } from '../site/search.mjs';

const topic = { id: 'flying-tigers', title: { en: 'Flying Tigers', 'zh-CN': '飞虎队' }, keywords: { en: ['Flying Tigers', 'American Volunteer Group'], 'zh-CN': ['飞虎队', '飛虎隊'] }, record_ids: ['a', 'b'] };
const records = [
  { id: 'a', title: 'P-40 fighter planes', source: 'NARA', topic_ids: ['flying-tigers'], topic_keywords: ['飞虎队', 'Flying Tigers'], format: 'IMAGE', record_origin: 'curated', thumbnail_url: 'https://www.archives.gov/photo.jpg' },
  { id: 'b', title: 'A pilot log', source: 'LoC', topic_ids: ['flying-tigers'], topic_keywords: ['飞虎队', 'Flying Tigers'], format: 'TEXT', record_origin: 'api' },
  { id: 'c', title: 'Burma Road map', source: 'LoC', topic_ids: ['roads'], format: 'MAP' },
];

test('topic membership intersects with the main search and source filters', () => {
  assert.deepEqual(filterRecords(records, { topic: topic.id }).map(r => r.id), ['a', 'b']);
  assert.deepEqual(filterRecords(records, { topic: topic.id, sources: ['LoC'], query: 'pilot' }).map(r => r.id), ['b']);
  assert.deepEqual(filterRecords(records, { topic: 'missing' }), []);
});
test('curated multilingual keywords are searchable and keep distinct AND clauses', () => {
  assert.deepEqual(filterRecords(records, { query: '飛虎隊', topics: [topic] }).map(r => r.id), ['a', 'b']);
  assert.deepEqual(filterRecords(records, { query: 'American Volunteer Group pilot', topics: [topic] }).map(r => r.id), ['b']);
  assert.match(expandQuery('飞虎队', 'en', [topic]).label, /Flying Tigers/);
  assert.deepEqual(filterRecords(records, { query: '飞虎队 missing', topics: [topic] }), []);
});
test('browsing uses explicit membership, prioritizes previews, and does not mutate the shared catalog', () => {
  const catalog = { topics: [topic], records: [...records].reverse() };
  const original = structuredClone(catalog);
  assert.deepEqual(browseRecords(catalog, topic.id).map(r => r.id), ['a', 'b']);
  assert.equal(browseRecords(catalog).length, 3);
  assert.deepEqual(catalog, original);
});
test('topic and keyword links intentionally begin a fresh discovery query', () => {
  const url = new URL(discoveryLink('zh-CN', { q: '飞虎队 & P-40' }), 'https://example.test/topics.html');
  assert.equal(url.searchParams.get('q'), '飞虎队 & P-40');
  assert.equal(url.searchParams.get('lang'), 'zh-CN');
  assert.equal(url.pathname, '/');
  assert.equal(new URL(discoveryLink('en', { topic: 'flying-tigers' }), url).searchParams.get('topic'), 'flying-tigers');
});
test('navigation preserves the submitted search but excludes page-only browsing and detail state', () => {
  const url = new URL(pageURL('./', '?q=Burma&source=LoC&source=NARA&browse=roads&record=a', 'en'), 'https://example.test/topics.html');
  assert.equal(url.searchParams.get('q'), 'Burma');
  assert.deepEqual(url.searchParams.getAll('source'), ['LoC', 'NARA']);
  assert.equal(url.searchParams.has('browse'), false);
  assert.equal(url.searchParams.has('record'), false);
});

test('related topic keywords are not expanded into one synonym group', () => {
  const catalog = JSON.parse(fs.readFileSync(new URL('../site/data/catalog.json', import.meta.url)));
  const news = filterRecords(catalog.records, { query: 'newspaper' });
  assert.ok(news.length > 0 && news.length < 10);
  assert.ok(!news.some(record => record.id === 'loc:2004676827'));
  const hump = filterRecords(catalog.records, { query: '驼峰' });
  assert.deepEqual(new Set(hump.map(record => record.id)), new Set(catalog.topics.find(topic => topic.id === 'hump-airlift').record_ids));
});
