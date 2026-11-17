"""Scene numbering, media provenance and reference-aware image tasks."""
import json

IMAGE_TYPES={'image/png','image/jpeg','image/webp'}
APPROVED={'Утверждено','Канон'}

def number_project(p):
    scenes={s['id']:s for s in p['scenes']}
    for i,s in enumerate(p['scenes'],1): s['number']=i; s['code']=f'S{i:03d}'
    counts={}
    for shot in p['shots']:
        sid=shot['scene'];counts[sid]=counts.get(sid,0)+1
        shot['code']=f"{scenes[sid]['code']}_P{counts[sid]:03d}"
    for i,a in enumerate(p['assets'],1):
        links=set(a.get('scene_ids',[]))
        if a.get('scene_id'):links.add(a['scene_id'])
        for shot in p['shots']:
            if a['id'] in [shot.get('start'),shot.get('end')]:links.add(shot['scene'])
        for s in p['scenes']:
            ids=s.get('character_ids',[])+([s['location_id']] if s.get('location_id') else [])
            if any(e['id'] in ids and e.get('reference')==a['id'] for e in p['entities']):links.add(s['id'])
        a['scene_ids']=[s['id'] for s in p['scenes'] if s['id'] in links]
        prefix='_'.join(scenes[sid]['code'] for sid in a['scene_ids']) or 'GLOBAL'
        a['code']=f'{prefix}_M{i:03d}'
        ext={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp','video/mp4':'.mp4','audio/mpeg':'.mp3','audio/wav':'.wav'}.get(a.get('type'),'')
        if not ext:
            from pathlib import PurePath
            ext=PurePath(a.get('name','')).suffix
            if len(ext)>12:ext=''
        a['filename']=a['code']+ext
    return p


def scene_entities(p,scene):
    ids=scene.get('character_ids',[])
    if not isinstance(ids,list):raise ValueError('Выберите персонажей сцены')
    if not scene.get('location_id'):raise ValueError(scene.get('code',scene['name'])+': назначьте локацию в редакторе сценария')
    wanted=ids+[scene['location_id']]
    result=[]
    for eid in wanted:
        e=next((e for e in p['entities'] if e['id']==eid),None)
        if not e:raise ValueError('В сцене указана отсутствующая карточка')
        expected='Локация' if eid==scene['location_id'] else 'Персонаж'
        if e.get('kind')!=expected:raise ValueError('Неверный тип карточки сцены')
        result.append(e)
    return result


def image_task(p, skip=None):
    skip=skip or set()
    number_project(p)
    assets={a['id']:a for a in p['assets']}
    # Prepare references before producing any missing scene frame.
    pending=[s for s in p['shots'] if not s.get('start') or not s.get('end')]
    if not pending:raise ValueError('Все кадры назначены. Для нового варианта очистите нужный START/END в раскадровке; старый файл останется в медиатеке.')
    contexts=[]
    for shot in pending:
        scene=next(s for s in p['scenes'] if s['id']==shot['scene'])
        entities=scene_entities(p,scene)
        ready=True
        for e in entities:
            ref=assets.get(e.get('reference'))
            if ref:
                if ref.get('type') not in IMAGE_TYPES:raise ValueError('Референс должен быть PNG/JPEG/WebP: '+e['name'])
                if e.get('status') not in APPROVED or ref.get('status') not in APPROVED:
                    raise ValueError('Утвердите карточку и её референс в разделе «Канон»: '+e['name'])
            else:
                ready=False
                if ('entity',e['id']) in skip:continue
                return {'entity_id':e['id'],'kind':'reference','text':'Эталон: '+e['name'], 'prompt':f"Create a consistent reference sheet for {e['kind']} {e['name']}. Exact appearance and constraints: {e['description']}. Project visual style: {p.get('bible','')}. No text labels. This is a reference, not a film scene.", 'references':[], 'scene_ids':[s['id'] for s in p['scenes'] if e['id'] in s.get('character_ids',[])+[s.get('location_id')]]}
        kind='start' if not shot.get('start') else 'end'
        if ready and (shot['id'],kind) not in skip:contexts.append((shot,scene,entities))
    if not contexts:raise ValueError('Нет независимых задач: сначала согласуйте результаты текущей партии.')
    shot,scene,entities=contexts[0]
    kind='start' if not shot.get('start') else 'end'
    refs=[];cards=[]
    for e in entities:
        aid=e['reference']
        if aid not in refs:refs.append(aid)
        cards.append({'name':e['name'],'kind':e['kind'],'description':e['description'],'reference_image':refs.index(aid)+1})
    if kind=='end' and shot.get('start') and shot['start'] not in refs:refs.append(shot['start'])
    prompt=f"Create {kind.upper()} frame for {shot['code']}: {shot['description']}. Location/action: {scene['description']}. Preserve identity, anatomy, clothing, colors and location geometry from the numbered reference images. Character/location cards: {json.dumps(cards,ensure_ascii=False)}. Canon rules: {json.dumps([r for r in p['rules'] if r.get('status') in APPROVED],ensure_ascii=False)}. Visual style: {p.get('bible','')}."
    if kind=='end':prompt+=' The last reference is the START frame; preserve continuity.'
    return {'shot_id':shot['id'],'kind':kind,'text':shot['code']+' '+kind.upper(),'prompt':prompt,'references':refs,'scene_ids':[scene['id']]}

def image_tasks(p,count):
    tasks=[];skip=set()
    for _ in range(count):
        try: task=image_task(p,skip)
        except ValueError as e:
            if tasks and str(e).startswith('Нет независимых задач'):break
            raise
        tasks.append(task)
        skip.add(('entity',task['entity_id']) if task.get('entity_id') else (task['shot_id'],task['kind']))
    return tasks
