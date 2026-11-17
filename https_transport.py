"""Windows system curl transport with TLS verification and private stdin configuration."""
import io
import os
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import urllib.error
from urllib.parse import urlsplit


def quote(value):
    if '\r' in value or '\n' in value or '\x00' in value:
        raise ValueError('Недопустимый символ в параметрах подключения')
    return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'


def curl_open(request, timeout=25):
    url=request.full_url
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.username or parsed.password:
        raise ValueError('Требуется HTTPS URL без встроенных учётных данных')
    config=['url = '+quote(url),'request = '+quote(request.get_method())]
    for name,value in request.header_items():
        config.append('header = '+quote(name+': '+value))
    with tempfile.TemporaryDirectory(prefix='ai-studio-http-') as directory:
        # Request body may contain project media, but never the Authorization key.
        if request.data is not None:
            body=Path(directory)/'body.bin'
            body.write_bytes(request.data)
            body.chmod(0o600)
            config.append('data-binary = '+quote('@'+body.as_posix()))
        command=['curl.exe','-q','--silent','--proto','=https','--max-time',str(timeout),'--max-filesize',str(100*1024*1024),'--config','-','--write-out','\n%{http_code}']
        try:
            result=subprocess.run(command,input=('\n'.join(config)+'\n').encode('utf-8'),capture_output=True,timeout=timeout+5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except FileNotFoundError:
            raise ValueError('Не найден системный curl.exe. Он необходим для API-подключения на Windows.') from None
        except subprocess.TimeoutExpired:
            raise urllib.error.URLError(TimeoutError()) from None
        if result.returncode:
            reasons={5:socket.gaierror(),6:socket.gaierror(),7:ConnectionRefusedError(),28:TimeoutError(),35:ssl.SSLError(),60:ssl.SSLCertVerificationError()}
            if result.returncode==63: raise ValueError('Ответ API превышает лимит 100 МБ')
            raise urllib.error.URLError(reasons.get(result.returncode,OSError('System curl failed'))) from None
        body,separator,status=result.stdout.rpartition(b'\n')
        if not separator or len(status)!=3 or not status.isdigit():
            raise ValueError('Системный curl вернул некорректный статус')
        status=int(status)
        if not 200<=status<300:
            # Never follow redirects or resend a possibly paid request automatically.
            raise urllib.error.HTTPError(url,status,'API request failed',{},io.BytesIO(body))
        return io.BytesIO(body)
