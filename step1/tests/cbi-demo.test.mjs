import test from 'node:test';
import assert from 'node:assert/strict';
import { archivalThumbnail, referenceMatches } from '../site/cbi-demo.mjs';

test('never renders CBI media or deceptive archive hosts as previews', () => {
  for (const value of ['https://cbi-theater.com/image.jpg', 'https://www.cbi-theater.com/image.jpg', 'https://archives.gov.evil.test/image.jpg', 'https://archives.gov@cbi-theater.com/image.jpg', 'http://www.archives.gov/image.jpg', 'javascript:alert(1)']) assert.equal(archivalThumbnail(value), null);
  assert.equal(archivalThumbnail('https://www.archives.gov/files/photo.jpg'), 'https://www.archives.gov/files/photo.jpg');
  assert.equal(archivalThumbnail('https://archive.org/services/img/a'), 'https://archive.org/services/img/a');
});
test('reference search combines terms and filters without altering match confidence', () => {
  const item = { kind:'image',title:'Flying Tigers P-40',url:'https://cbi-theater.com/p40.jpg',review_status:'not_reviewed' };
  assert.ok(referenceMatches(item, 'FLYING p-40', 'image', 'not_reviewed'));
  assert.ok(!referenceMatches(item, 'Flying missing', '', ''));
  assert.ok(!referenceMatches(item, '', 'page', ''));
  assert.ok(!referenceMatches(item, '', '', 'same_work'));
  assert.equal(item.review_status, 'not_reviewed');
});
test('reference search preserves Unicode titles and treats metacharacters as literal', () => {
  const item={title:'飞虎队 Ｐ－４０ [album]',kind:'page',review_status:'related'};
  assert.ok(referenceMatches(item,'飞虎队 P-40','',''));
  assert.ok(referenceMatches(item,'[album]','',''));
  assert.ok(!referenceMatches(item,'.*','',''));
});
