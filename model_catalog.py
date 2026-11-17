"""Read-only authenticated provider discovery; never sends keys on redirects."""
from https_transport import curl_open
from network_errors import explain
from provider_errors import http_message
import json
import os
import urllib.request
import urllib.error
from urllib.parse import urlsplit
from datetime import datetime, timezone


def normalize_endpoint(value):
    endpoint=value.strip().rstrip('/')
    url=urlsplit(endpoint)
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('Укажите базовый HTTPS URL без ключа, параметров и имени пользователя')
    return endpoint


def merge_settings(incoming, previous):
    endpoint=normalize_endpoint(incoming.get('endpoint',previous.get('endpoint','https://anymodel.org/v1')))
    changed=endpoint!=previous.get('endpoint','').rstrip('/')
    # Never silently forward a saved key to a newly entered provider.
    key=incoming.get('key','').strip() or (previous.get('key','') if not changed else '')
    return {'endpoint':endpoint,'key':key,'model':incoming.get('model',previous.get('model','') if not changed else ''),'image_model':incoming.get('image_model',previous.get('image_model','') if not changed else '')}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


def discover(config):
    endpoint=normalize_endpoint(config['endpoint'])
    key=config.get('key') or os.environ.get('AI_STUDIO_API_KEY')
    if not key: raise ValueError('Введите API-ключ для этого базового URL')
    req=urllib.request.Request(endpoint+'/models',headers={'Authorization':'Bearer '+key,'Accept':'application/json'})
    try:
        with (curl_open(req,timeout=25) if os.name=='nt' else urllib.request.build_opener(NoRedirect()).open(req,timeout=25)) as response:
            raw=response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024: raise ValueError('Список моделей слишком большой')
        payload=json.loads(raw)
        data=payload.get('data') if isinstance(payload,dict) else None
        if not isinstance(data,list): raise ValueError('API вернул неизвестный формат списка моделей; ожидается data: [...]')
        models=[];seen=set()
        for item in data:
            if not isinstance(item,dict) or not isinstance(item.get('id'),str) or not item['id'].strip():
                raise ValueError('API вернул некорректную запись модели')
            if item['id'] in seen: continue
            seen.add(item['id'])
            model={'id':item['id']}
            if urlsplit(endpoint).hostname=='anymodel.org':
                model['kind']=item.get('kind') or 'text'
            elif isinstance(item.get('kind'),str):
                model['kind']=item['kind']
            models.append(model)
        return {'models':sorted(models,key=lambda x:x['id']), 'checked_at':datetime.now(timezone.utc).isoformat(), 'status':'connected', 'message':f'Подключение успешно. API вернул моделей: {len(models)}. Генерация и баланс не проверены. Назначение моделей уточняйте у провайдера.'}
    except urllib.error.HTTPError as e:
        raise ValueError(http_message(e,endpoint,key)) from None
    except (urllib.error.URLError,OSError) as e:
        raise ValueError(explain(e)) from None
    except (json.JSONDecodeError,UnicodeDecodeError):
        raise ValueError('Сервер вернул не JSON. Проверьте базовый URL API.') from None
