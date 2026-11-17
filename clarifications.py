"""Persisted answers linked to original questions, with reanalysis freshness checks."""
import hashlib
import json


def context(p):
    rows=p.get('clarifications',[])
    if not isinstance(rows,list):raise ValueError('Некорректный список ответов')
    assets={a['id']:a for a in p['assets']}
    result=[]
    for row in rows:
        if not isinstance(row,dict) or not all(isinstance(row.get(k,''),str) for k in ['kind','prompt','answer']):
            raise ValueError('Некорректный ответ на вопрос')
        ids=row.get('asset_ids',[])
        if not isinstance(ids,list) or any(not isinstance(aid,str) or aid not in assets for aid in ids):
            raise ValueError('Не найден приложенный к ответу файл')
        if row.get('answer','').strip() or ids:
            result.append({'kind':row.get('kind','question'),'prompt':row.get('prompt',''),'answer':row.get('answer',''),
                           'attachments':[{'asset_id':aid,'name':assets[aid]['name'],'type':assets[aid]['type'],'sha256':assets[aid].get('sha256'),'text':assets[aid].get('text','')} for aid in ids]})
    return result


def signature(p):
    rows=context(p)
    return hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode()).hexdigest() if rows else ''


def require_current(p):
    if signature(p)!=p.get('production',{}).get('clarifications_signature',''):
        raise ValueError('Ответы сохранены, но ещё не учтены AI. Нажмите «Учесть ответы и уточнить разбор» перед согласованием.')
