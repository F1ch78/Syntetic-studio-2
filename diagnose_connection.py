"""Credential-free comparison of Python TLS and the OS curl client."""
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import urllib.request
import urllib.error
from model_catalog import normalize_endpoint, NoRedirect
from network_errors import explain


def main():
    root=Path(__file__).parent
    settings=Path(os.environ.get('AI_STUDIO_DATA',root/'data'))/'ai-settings.json'
    config=json.loads(settings.read_text(encoding='utf-8')) if settings.exists() else {}
    endpoint=normalize_endpoint(config.get('endpoint','https://anymodel.org/v1'))
    print('No API key is sent. HTTP 401/403 can be expected in this diagnostic.')
    print('Python:',sys.version.split()[0], '|',ssl.OPENSSL_VERSION)
    print('Proxy configured:',bool(urllib.request.getproxies()))
    url=endpoint+'/models'
    try:
        req=urllib.request.Request(url,headers={'Accept':'application/json'})
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=20) as response:
            print('Python: TLS OK, HTTP',response.status)
    except urllib.error.HTTPError as e: print('Python: received HTTP',e.code,'(a proxy may also produce this status)')
    except (urllib.error.URLError,OSError) as e: print('Python:',explain(e))
    try:
        # No verbose output, headers, key, body, redirects or disabled verification.
        result=subprocess.run(['curl.exe' if os.name=='nt' else 'curl','-q','--silent','--output',os.devnull,'--max-time','20','--write-out','%{http_code}',url],capture_output=True,text=True,timeout=25)
        status=result.stdout.strip()
        print('OS curl: exit',result.returncode,'HTTP',status if status.isdigit() else 'unknown')
        print('curl exit 0: HTTP response; 6: DNS; 7: connection; 28: timeout; 35: TLS; 60: certificate.')
    except (OSError,subprocess.TimeoutExpired): print('OS curl unavailable or timed out')

if __name__=='__main__':main()
