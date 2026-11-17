import io
import unittest
from unittest.mock import patch,MagicMock
from urllib.error import HTTPError
from model_catalog import discover, merge_settings, normalize_endpoint

class CatalogTests(unittest.TestCase):
    def test_changed_provider_does_not_reuse_key(self):
        old={'endpoint':'https://one.example/v1','key':'private','model':'old'}
        self.assertEqual(merge_settings({'endpoint':'https://two.example/v1'},old)['key'],'')
        self.assertEqual(merge_settings({'endpoint':'https://one.example/v1/'},old)['key'],'private')
    def test_reject_url_credentials(self):
        for url in ['http://host/v1','https://user:secret@host/v1','https://host/v1?key=x']:
            with self.assertRaises(ValueError): normalize_endpoint(url)
    @patch('model_catalog.urllib.request.build_opener')
    def test_discover_deduplicates(self,build):
        build.return_value.open.return_value.__enter__.return_value.read.return_value=b'{"data":[{"id":"z"},{"id":"a"},{"id":"z"}]}'
        result=discover({'endpoint':'https://example.com/v1','key':'test'})
        self.assertEqual(result['models'],[{'id':'a'},{'id':'z'}])
        self.assertNotIn('key',result)
        req=build.return_value.open.call_args.args[0]
        self.assertEqual(req.full_url,'https://example.com/v1/models')
    @patch('model_catalog.urllib.request.build_opener')
    def test_auth_error_does_not_leak_body(self,build):
        build.return_value.open.side_effect=HTTPError('https://example.com',401,'secret message',{},io.BytesIO(b'secret'))
        with self.assertRaisesRegex(ValueError,'Ключ не принят') as caught:discover({'endpoint':'https://example.com','key':'secret'})
        self.assertNotIn('secret',str(caught.exception))
    @patch('model_catalog.urllib.request.build_opener')
    def test_invalid_and_empty_catalogs(self,build):
        reader=build.return_value.open.return_value.__enter__.return_value.read
        reader.return_value=b'{"data":[]}'
        self.assertEqual(discover({'endpoint':'https://example.com','key':'x'})['models'],[])
        reader.return_value=b'{"data":[{}]}'
        with self.assertRaises(ValueError):discover({'endpoint':'https://example.com','key':'x'})
