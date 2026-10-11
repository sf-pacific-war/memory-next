import test from 'node:test';
import assert from 'node:assert/strict';
import { bindPageTranslations, messages, normalizeLocale, resolveLocale, translate } from '../site/i18n.mjs';

test('resolves an explicit URL language before saved and browser preferences', () => {
  assert.equal(resolveLocale('en-GB', 'zh-CN', ['zh-TW']), 'en');
  assert.equal(resolveLocale('zh-TW', 'en', ['en-US']), 'zh-CN');
  assert.equal(resolveLocale('unsupported', 'zh', ['en-US']), 'zh-CN');
  assert.equal(resolveLocale(null, null, ['fr-FR', 'zh-HK', 'en']), 'zh-CN');
  assert.equal(resolveLocale(null, null, ['fr-FR']), 'en');
  assert.equal(normalizeLocale(null), null);
  assert.equal(normalizeLocale('english'), null);
});

test('interpolates literal values once without evaluating replacement syntax or inherited keys', () => {
  assert.equal(translate('已显示 {shown} / {total} 条资料', 'en', { shown: 0, total: 31 }), 'Showing 0 of 31 records');
  assert.equal(translate('移除筛选：{text}', 'en', { text: '$& <archive> {total}' }), 'Remove filter: $& <archive> {total}');
  assert.equal(translate('Unknown {value}', 'en', {}), 'Unknown {value}');
  assert.equal(translate('Unknown {value}', 'en', Object.create({ value: 'inherited' })), 'Unknown {value}');
  assert.equal(translate('A verbatim archival title', 'zh-CN'), 'A verbatim archival title');
});

test('both supported translations retain every interpolation parameter', () => {
  const parameters = value => [...value.matchAll(/\{(\w+)\}/g)].map(match => match[1]).sort();
  for (const [key, localized] of Object.entries(messages)) {
    assert.equal(typeof localized.en, 'string', `Missing English: ${key}`);
    assert.equal(typeof localized['zh-CN'], 'string', `Missing Chinese: ${key}`);
    assert.deepEqual(parameters(localized.en), parameters(localized['zh-CN']), key);
  }
});

function textNode(value, tagName = 'SPAN', languageOption = false) {
  return {
    nodeValue: value,
    parentElement: { tagName, closest: selector => languageOption && selector === '#language' ? {} : null },
  };
}

function elementWithAttributes(attributes) {
  const values = { ...attributes };
  return { getAttribute: key => values[key] ?? null, setAttribute: (key, value) => { values[key] = value; } };
}

test('binds UI text and accessibility attributes without replacing controls or later archival content', () => {
  const label = textNode('  搜索资料\n');
  const title = textNode('资料发现 · 太平洋战争档案', 'TITLE');
  const option = textNode('中文', 'OPTION', true);
  const script = textNode('搜索资料', 'SCRIPT');
  const style = textNode('搜索资料', 'STYLE');
  const noScript = textNode('搜索资料', 'NOSCRIPT');
  const nodes = [label, title, option, script, style, noScript];
  const input = elementWithAttributes({ 'aria-label': '搜索资料', placeholder: '起始年' });
  input.value = 'Unsubmitted Burma Road query';
  const originalInput = input;
  const meta = elementWithAttributes({ content: '跨来源发现中国与缅甸战场的历史资料。检索真实目录样本，查看出处并前往原馆。' });
  const document = {
    documentElement: { lang: 'zh-CN' },
    createTreeWalker() {
      let position = 0;
      return { nextNode: () => nodes[position++] || null };
    },
    querySelectorAll: () => [input, meta],
  };
  const apply = bindPageTranslations(document);
  // Records are rendered after bindings are created. Even a title matching a UI
  // dictionary key must stay in its source language when the UI switches.
  const archivalTitle = textNode('搜索资料');
  const archivalDescription = textNode('1941 滇緬運輸記錄 / Original record');
  nodes.push(archivalTitle, archivalDescription);

  apply('en');
  assert.equal(document.documentElement.lang, 'en');
  assert.equal(label.nodeValue, '  Search\n');
  assert.equal(title.nodeValue, 'Discovery · Pacific War Archives');
  assert.equal(input, originalInput);
  assert.equal(input.value, 'Unsubmitted Burma Road query');
  assert.equal(input.getAttribute('aria-label'), 'Search');
  assert.equal(input.getAttribute('placeholder'), 'From year');
  assert.match(meta.getAttribute('content'), /^Discover historical sources/);
  assert.equal(option.nodeValue, '中文');
  for (const skipped of [script, style, noScript]) assert.equal(skipped.nodeValue, '搜索资料');
  assert.equal(archivalTitle.nodeValue, '搜索资料');
  assert.equal(archivalDescription.nodeValue, '1941 滇緬運輸記錄 / Original record');

  apply('zh-CN');
  assert.equal(document.documentElement.lang, 'zh-CN');
  assert.equal(label.nodeValue, '  搜索资料\n');
  assert.equal(input.getAttribute('aria-label'), '搜索资料');
  assert.equal(input.value, 'Unsubmitted Burma Road query');
  assert.equal(archivalTitle.nodeValue, '搜索资料');
});
