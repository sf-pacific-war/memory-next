import test from 'node:test';
import assert from 'node:assert/strict';
import { archivalThumbnail } from '../site/archive-media.mjs';

test('never renders CBI media or deceptive archive hosts as previews', () => {
  for (const value of ['https://cbi-theater.com/image.jpg', 'https://www.cbi-theater.com/image.jpg', 'https://archives.gov.evil.test/image.jpg', 'https://archives.gov@cbi-theater.com/image.jpg', 'http://www.archives.gov/image.jpg', 'javascript:alert(1)']) assert.equal(archivalThumbnail(value), null);
  assert.equal(archivalThumbnail('https://www.archives.gov/files/photo.jpg'), 'https://www.archives.gov/files/photo.jpg');
  assert.equal(archivalThumbnail('https://archive.org/services/img/a'), 'https://archive.org/services/img/a');
});
