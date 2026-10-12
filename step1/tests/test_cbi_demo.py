import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import build_cbi_demo as demo


class CBIDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / 'data' / 'cbi'
        self.folder.mkdir(parents=True)
        self.page = 'https://cbi-theater.com/guide.html'
        self.asset = 'https://cbi-theater.com/photo.jpg'
        self.write('inventory', {'source_url': self.page, 'summary': {'media_files_requested': 0}, 'pages': [{'url': self.page, 'status': 'ok', 'title': 'Pocket Guide to Burma', 'images': [{'url': self.asset}]}], 'assets': [{'url': self.asset, 'kind': 'image', 'referenced_by': [self.page]}]})
        self.write('verified-matches', {'records': [{'id': 'match-1', 'cbi_page_url': self.page, 'cbi_page_title': 'Pocket Guide to Burma', 'archival_url': 'https://archive.org/details/guide', 'archival_title': 'Pocket Guide to Burma', 'match_status': 'same_work', 'thumbnail_url': self.asset}]})
        self.write('archive-records', {'records': [{'id': 'loc:123', 'source': 'LoC', 'source_url': 'https://www.loc.gov/item/123/', 'title': 'Pocket Guide to Burma', 'thumbnail_url': self.asset, 'secret': 'do-not-publish'}]})

    def write(self, name, data):
        (self.folder / (name + '.json')).write_text(json.dumps(data))

    def test_previews_accept_only_https_archival_hosts(self):
        for value in [self.asset, 'https://archives.gov.evil.test/image.jpg', 'http://tile.loc.gov/image.jpg', 'https://user:pw@www.archives.gov/x.jpg', 'https://127.0.0.1/x.jpg']:
            self.assertIsNone(demo.thumbnail_url(value))
        self.assertEqual(demo.thumbnail_url('https://tile.loc.gov/photo.jpg'), 'https://tile.loc.gov/photo.jpg')

    def test_page_comparison_never_verifies_its_photos(self):
        data = demo.build_demo(self.root)
        page = next(i for i in data['items'] if i['kind'] == 'page')
        asset = next(i for i in data['items'] if i['kind'] == 'image')
        self.assertEqual(page['review_status'], 'same_work')
        self.assertEqual(asset['review_status'], 'not_reviewed')
        self.assertEqual(asset['comparison_ids'], [])
        self.assertEqual(asset['fetch_status'], 'not_requested')

    def test_reviewed_references_outside_crawl_remain_searchable(self):
        record = json.loads((self.folder / 'verified-matches.json').read_text())
        record['records'][0]['cbi_page_url'] = 'https://cbi-theater.com/not-crawled.html'
        self.write('verified-matches', record)
        found = next(i for i in demo.build_demo(self.root)['items'] if i['review_status'] == 'same_work')
        self.assertEqual(found['fetch_status'], 'not_fetched')
        self.assertEqual(found['title'], 'Pocket Guide to Burma')

    def test_public_output_strips_nonarchival_previews_and_extra_fields(self):
        data = demo.build_demo(self.root)
        self.assertIsNone(data['records'][0]['thumbnail_url'])
        self.assertIsNone(data['comparisons'][0]['thumbnail_url'])
        self.assertNotIn('secret', data['records'][0])

    def test_keyword_overlap_is_only_a_lead(self):
        self.write('verified-matches', {'records': []})
        page = next(i for i in demo.build_demo(self.root)['items'] if i['kind'] == 'page')
        self.assertEqual(page['review_status'], 'keyword_lead')
        self.assertEqual(page['comparison_ids'], [])
        self.assertEqual(demo.title_leads('China Burma India photos', [{'id': 'a', 'title': 'China Burma India'}]), [])

    def test_writes_complete_valid_json(self):
        data = demo.write_demo(self.root)
        self.assertEqual(json.loads((self.root / 'data/cbi/review-report.json').read_text()), data)

    def test_space_in_reference_filename_is_retained_without_loading_media(self):
        raw = json.loads((self.folder / 'inventory.json').read_text())
        raw['assets'][0]['url'] = 'https://cbi-theater.com/album/Flying Tigers.jpg'
        self.write('inventory', raw)
        item = next(i for i in demo.build_demo(self.root)['items'] if i['kind'] == 'image')
        self.assertEqual(item['url'], 'https://cbi-theater.com/album/Flying%20Tigers.jpg')
        self.assertEqual(item['fetch_status'], 'not_requested')
        self.assertIsNone(demo.thumbnail_url(item['url']))
        self.assertIsNone(demo.reference_url('https://cbi-theater.com/bad\nname.jpg'))

    def test_rejects_symlink_output(self):
        target = self.root / 'outside.json'
        target.write_text('keep')
        (self.root / 'data/cbi').mkdir(parents=True, exist_ok=True)
        (self.root / 'data/cbi/review-report.json').symlink_to(target)
        with self.assertRaises(ValueError):
            demo.write_demo(self.root)
        self.assertEqual(target.read_text(), 'keep')
