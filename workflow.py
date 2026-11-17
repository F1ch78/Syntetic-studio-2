"""Deterministic, non-destructive script breakdown and production tracking."""
import hashlib
import re
from uuid import uuid4


def digest(script):
    return hashlib.sha256(script.encode()).hexdigest()


def prepare(project):
    text = project.get('script', '').strip()
    if not text:
        return
    previous = project.get('workflow', {})
    if previous.get('source') == digest(text):
        return
    headings = list(re.finditer(r'(?im)^\s*(?:#{1,6}\s*)?(?:сцена\s+\d+|эпизод\s+\d+|scene\s+\d+|инт\.|нат\.|int\.|ext\.)[^\n]*', text))
    scenes = []
    if headings:
        for i, match in enumerate(headings):
            end = headings[i+1].start() if i+1 < len(headings) else len(text)
            scenes.append({'name': match.group().strip().lstrip('#').strip(), 'description': text[match.end():end].strip()})
    else:
        scenes = [{'name': 'Сцена 1 — проверить разбиение', 'description': text}]
    project['workflow'] = {'source': digest(text), 'confirmed': False, 'proposals': scenes,
                           'notice': 'Разбиение по заголовкам сценария. Проверьте границы сцен и детализацию планов.' if headings else 'Заголовки сцен не найдены. Предложена одна сцена; разделите её вручную при необходимости.'}


def accept(project):
    prepare(project)
    flow = project.get('workflow', {})
    if not flow or flow.get('confirmed'):
        return
    # Reuse exact matches; never overwrite existing scenes, shots or assets.
    for proposal in flow['proposals']:
        scene = next((s for s in project['scenes'] if s['name'] == proposal['name'] and s.get('description', '') == proposal['description']), None)
        if scene is None:
            scene = dict(proposal, id=str(uuid4()), status='Черновик')
            project['scenes'].append(scene)
        if not any(s['scene'] == scene['id'] for s in project['shots']):
            project['shots'].append(dict(id=str(uuid4()), name=scene['name'] + ' / План 1', scene=scene['id'], description=scene['description'], status='Черновик', duration=5, start='', end=''))
    flow['confirmed'] = True


def overview(p):
    flow = p.get('workflow', {})
    shots = p['shots']
    assets = {a['id']: a for a in p['assets']}
    frames = sum(bool(s.get(k)) and assets.get(s[k], {}).get('type', '').startswith('image/') for s in shots for k in ('start', 'end'))
    steps = []
    def add(name, done, detail, tab, active=False):
        steps.append(dict(name=name, status='Готово' if done else 'В работе' if active else 'Не начато', detail=detail, tab=tab))
    add('Сценарий', bool(p.get('script', '').strip()), 'Загрузите или сохраните текст сценария.', 'Сценарий')
    add('Разбор на сцены и планы', bool(flow.get('confirmed')) and bool(p['scenes']) and all(any(s['scene']==c['id'] for s in shots) for c in p['scenes']), f"Сцен: {len(p['scenes'])}; планов: {len(shots)}. Подтвердите предложенную структуру.", 'План производства', bool(flow))
    add('Персонажи, локации и реквизит', bool(p['entities']) and all(e.get('status')=='Канон' for e in p['entities']), f"Эталонов: {len(p['entities'])}. Добавьте нужные объекты и утвердите их в каноне.", 'Персонажи и локации', bool(p['entities']))
    add('Правила канона и исключения', bool(p['rules']) and all(r.get('status')=='Канон' for r in p['rules']), f"Правил: {len(p['rules'])}. Утвердите их в разделе канона.", 'Канон', bool(p['rules']))
    add('Начальные и конечные кадры', bool(shots) and frames==len(shots)*2, f'Назначено изображений: {frames} из {len(shots)*2}.', 'Раскадровка', bool(frames))
    add('Ручная проверка планов', bool(shots) and all(s.get('status')=='Канон' for s in shots), 'Проверьте и утвердите каждый план.', 'Раскадровка', bool(shots))
    for name in ['Генерация видео', 'Визуальная проверка канона', 'Озвучка, музыка и эффекты', 'Монтаж и синхронизация', 'Финальная проверка фильма', 'Экспорт MP4']:
        steps.append(dict(name=name, status='Недоступно в этой версии', detail='Этот этап ещё не реализован. Автоматическое выполнение не запускается.', tab=None))
    next_step = next((s for s in steps if s['status'] not in ['Готово', 'Недоступно в этой версии']), None)
    return dict(steps=steps, completed=sum(s['status']=='Готово' for s in steps), total=len(steps), next=next_step)
