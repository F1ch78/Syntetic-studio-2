"""Interpret documented provider codes without exposing raw bodies or credentials."""
import json
import re
from urllib.parse import urlsplit


def http_message(error, endpoint, secret=''):
    body={}
    try:
        raw=error.read(65537)
        if len(raw)<=65536:
            payload=json.loads(raw)
            if isinstance(payload,dict) and isinstance(payload.get('error'),dict): body=payload['error']
    except (ValueError,OSError,TypeError): pass
    code=body.get('code')
    anymodel=urlsplit(endpoint).hostname=='anymodel.org'
    if anymodel and error.code==403 and code=='insufficient_quota':
        message='HTTP 403 / insufficient_quota: аккаунт AnyModel не активен. Проверьте подтверждение электронной почты и статус аккаунта. Если почта подтверждена, обратитесь в поддержку AnyModel. Это не сообщение о нехватке денег.'
    elif anymodel and error.code==402 and code=='payment_required':
        message='HTTP 402 / payment_required: на аккаунте AnyModel недостаточно средств. Проверьте баланс в личном кабинете.'
    else:
        messages={401:'Ключ не принят. Проверьте API-ключ.',403:'Доступ запрещён. Ответ не подтверждает причину: возможен запрет провайдера или сетевого шлюза.',404:'Ресурс не найден. Проверьте базовый URL и выбранную модель.',429:'Лимит запросов превышен. Повторите позже.'}
        message=f'HTTP {error.code}: '+messages.get(error.code,'API отклонил запрос. Проверка не завершена.')
    request_id=body.get('request_id') or (error.headers.get('X-Request-Id') if error.headers else None)
    if isinstance(request_id,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}',request_id) and not request_id.startswith('sk-') and (not secret or secret not in request_id):
        message+=' Номер запроса для поддержки: '+request_id
    return message
