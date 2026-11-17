import socket
import ssl
import unittest
from urllib.error import URLError
from unittest.mock import patch
from model_catalog import discover
from network_errors import explain

class NetworkTests(unittest.TestCase):
    def test_classification_and_redaction(self):
        cases=[(socket.gaierror(-2,'private-key'),'DNS:'),(TimeoutError('private-key'),'TIMEOUT:'),(ssl.SSLCertVerificationError(1,'private-key'),'TLS_CERTIFICATE:'),(ssl.SSLError('private-key'),'TLS_HANDSHAKE:'),(ConnectionRefusedError('private-key'),'CONNECTION_REFUSED:'),(ConnectionResetError('private-key'),'CONNECTION_RESET:'),(OSError('Tunnel connection failed: private-key'),'PROXY_TUNNEL:'),(OSError('private-key'),'NETWORK:')]
        for error,code in cases:
            with self.subTest(code=code):
                text=explain(URLError(error))
                self.assertTrue(text.startswith(code))
                self.assertNotIn('private-key',text)
    @patch('model_catalog.urllib.request.build_opener')
    def test_catalog_surfaces_specific_error(self,build):
        build.return_value.open.side_effect=URLError(ssl.SSLCertVerificationError(1,'secret'))
        with self.assertRaisesRegex(ValueError,'TLS_CERTIFICATE:'):
            discover({'endpoint':'https://example.com/v1','key':'test'})
