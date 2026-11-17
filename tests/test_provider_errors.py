import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch
from provider_errors import http_message
from model_catalog import discover

class ProviderTests(unittest.TestCase):
    def error(self,status,body):
        return HTTPError('https://anymodel.org/v1/models',status,'',{},io.BytesIO(json.dumps(body).encode()))
    def test_inactive_account_is_not_balance(self):
        text=http_message(self.error(403,{'error':{'code':'insufficient_quota','request_id':'req-123','message':'SECRET'}}),'https://anymodel.org/v1','SECRET')
        self.assertIn('не активен',text);self.assertIn('req-123',text);self.assertNotIn('SECRET',text)
    def test_payment_code(self):
        self.assertIn('недостаточно средств',http_message(self.error(402,{'error':{'code':'payment_required'}}),'https://anymodel.org/v1'))
    def test_other_provider_not_misclassified(self):
        self.assertNotIn('не активен',http_message(self.error(403,{'error':{'code':'insufficient_quota'}}),'https://other.example/v1'))
    def test_html_gateway_error(self):
        error=HTTPError('https://anymodel.org',403,'',{},io.BytesIO(b'<html>blocked SECRET</html>'))
        text=http_message(error,'https://anymodel.org/v1');self.assertIn('не подтверждает',text);self.assertNotIn('SECRET',text)
    def test_secret_request_id_not_displayed(self):
        text=http_message(self.error(403,{'error':{'request_id':'SECRET'}}),'https://anymodel.org/v1','SECRET')
        self.assertNotIn('SECRET',text)
    @patch('model_catalog.urllib.request.build_opener')
    def test_anymodel_kinds_and_full_ids(self,build):
        build.return_value.open.return_value.__enter__.return_value.read.return_value=json.dumps({'data':[{'id':'am/text'},{'id':'am/image','kind':'image'},{'id':'am/vision','kind':'imageToText'}]}).encode()
        models=discover({'endpoint':'https://anymodel.org/v1','key':'test'})['models']
        self.assertEqual({m['id']:m['kind'] for m in models},{'am/text':'text','am/image':'image','am/vision':'imageToText'})
