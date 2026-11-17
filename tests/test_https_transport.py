import json
import subprocess
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch
from https_transport import curl_open, quote
from provider_errors import http_message

class CurlTransportTests(unittest.TestCase):
    @patch('https_transport.subprocess.run')
    def test_key_in_stdin_only_and_verified_tls(self,run):
        run.return_value=subprocess.CompletedProcess([],0,b'{"data":[]}\n200',b'')
        req=urllib.request.Request('https://anymodel.org/v1/models',headers={'Authorization':'Bearer TEST_SECRET'})
        with curl_open(req) as r:self.assertEqual(json.load(r),{'data':[]})
        args=run.call_args.args[0];kwargs=run.call_args.kwargs
        self.assertNotIn('TEST_SECRET',' '.join(args));self.assertIn(b'TEST_SECRET',kwargs['input'])
        for unsafe in ['--insecure','-k','--location','-L','--retry']:self.assertNotIn(unsafe,args)
        self.assertIn('-q',args)
    @patch('https_transport.subprocess.run')
    def test_json_error_retained(self,run):
        run.return_value=subprocess.CompletedProcess([],0,b'{"error":{"code":"insufficient_quota"}}\n403',b'')
        with self.assertRaises(urllib.error.HTTPError) as caught:curl_open(urllib.request.Request('https://anymodel.org/v1/models'))
        self.assertIn('не активен',http_message(caught.exception,'https://anymodel.org/v1'))
    @patch('https_transport.subprocess.run')
    def test_certificate_failure_no_retry_or_leak(self,run):
        run.return_value=subprocess.CompletedProcess([],60,b'',b'private error')
        with self.assertRaises(urllib.error.URLError) as caught:curl_open(urllib.request.Request('https://example.com'))
        self.assertNotIn('private',str(caught.exception));self.assertEqual(run.call_count,1)
    def test_config_injection_blocked(self):
        with self.assertRaises(ValueError):quote('key\ninsecure')
    @patch('https_transport.subprocess.run')
    def test_post_body_temporary_and_preserved(self,run):
        from pathlib import Path
        seen=[]
        def fake(args,**kw):
            config=kw['input'].decode();line=next(x for x in config.splitlines() if x.startswith('data-binary'))
            path=Path(line.split('"@')[1][:-1]);seen.append(path)
            self.assertEqual(path.read_bytes(),b'{"prompt":"hello"}')
            return subprocess.CompletedProcess([],0,b'{}\n200',b'')
        run.side_effect=fake
        curl_open(urllib.request.Request('https://example.com',data=b'{"prompt":"hello"}'))
        self.assertFalse(seen[0].exists())
