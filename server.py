"""AI Studio local MVP. Python 3.12+, no external dependencies."""
from workflow import prepare, accept, overview
from ai_production import analyze, approve_analysis, run_stage, approve_stage
import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from uuid import uuid4
from datetime import datetime, timezone

ROOT = Path(__file__).parent
DATA = Path(os.environ.get('AI_STUDIO_DATA', ROOT / 'data'))
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / 'studio.sqlite3'
MAX_BODY = 100 * 1024 * 1024
SETTINGS = DATA / 'ai-settings.json'
def ai_config():
    return json.loads(SETTINGS.read_text()) if SETTINGS.exists() else {'endpoint':'https://anymodel.org/v1','model':''}


def connection():
    db = sqlite3.connect(DB)
    db.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
    return db

def validate(p):
    if not isinstance(p, dict) or not isinstance(p.get('name'), str) or not p['name'].strip():
        raise ValueError('Укажите название проекта')
    for key in ['scenes', 'shots', 'entities', 'rules', 'assets', 'history']:
        if not isinstance(p.get(key), list):
            raise ValueError('Некорректный раздел: ' + key)
    ids = {}
    for key in ['scenes', 'shots', 'entities', 'rules', 'assets']:
        ids[key] = set()
        for item in p[key]:
            if not isinstance(item, dict) or not isinstance(item.get('id'), str) or item['id'] in ids[key]:
                raise ValueError('Некорректный идентификатор: ' + key)
            ids[key].add(item['id'])
    for shot in p['shots']:
        if shot.get('scene') not in ids['scenes']:
            raise ValueError('План ссылается на отсутствующую сцену')
        for field in ['start', 'end']:
            if shot.get(field) and shot[field] not in ids['assets']:
                raise ValueError('Отсутствует изображение плана')
    for a in p['assets']:
        raw = base64.b64decode(a.get('data', ''), validate=True)
        if hashlib.sha256(raw).hexdigest() != a.get('sha256'):
            raise ValueError('Нарушена целостность файла: ' + str(a.get('name')))
    return p

def report(p):
    issues = []
    if not p.get('script', '').strip(): issues.append('Не заполнен сценарий')
    if not p['scenes']: issues.append('Нет сцен')
    for scene in p['scenes']:
        if not any(s.get('scene') == scene['id'] for s in p['shots']): issues.append('Нет планов: ' + scene['name'])
    for s in p['shots']:
        for f, label in [('start', 'START'), ('end', 'END')]:
            if not s.get(f): issues.append(s['name'] + ': отсутствует ' + label)
        if s.get('status') != 'Канон': issues.append(s['name'] + ': не включён в канон')
    if not p['rules']: issues.append('Не заданы правила канона')
    return {'issues': issues, 'shots': len(p['shots']), 'approved': sum(s.get('status') == 'Канон' for s in p['shots']), 'scope': 'Структурная проверка. Визуальное соответствие не анализируется.'}

class Handler(BaseHTTPRequestHandler):
    def send(self, status, obj, content_type='application/json; charset=utf-8'):
        data = json.dumps(obj, ensure_ascii=False).encode() if content_type.startswith('application/json') else obj
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/projects':
            with connection() as db:
                projects = [json.loads(r[0]) for r in db.execute('SELECT body FROM projects')]
            return self.send(200, projects)
        if path == '/api/settings':
            cfg = ai_config()
            return self.send(200, {k:v for k,v in cfg.items() if k != 'key'} | {'configured':bool(cfg.get('key') or os.environ.get('AI_STUDIO_API_KEY'))})
        if path == '/api/health': return self.send(200, {'status': 'ok'})
        files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if path not in files: return self.send(404, {'error': 'Не найдено'})
        name, mime = files[path]
        return self.send(200, (ROOT / 'web' / name).read_bytes(), mime)

    def do_POST(self):
        # Browser mutations must originate from this server.
        origin = self.headers.get('Origin')
        if origin and urlparse(origin).netloc != self.headers.get('Host'):
            return self.send(403, {'error': 'Запрещённый источник запроса'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > MAX_BODY: return self.send(413, {'error': 'Максимальный размер запроса — 100 МБ'})
            p = json.loads(self.rfile.read(length))
            path = urlparse(self.path).path
            if path == '/api/settings':
                old = ai_config()
                cfg = {'endpoint':p.get('endpoint','https://anymodel.org/v1').rstrip('/'), 'model':p.get('model',''), 'image_model':p.get('image_model',''), 'key':p.get('key') or old.get('key','')}
                if not cfg['endpoint'].startswith('https://') or not cfg['model'].strip():
                    raise ValueError('Укажите HTTPS-адрес и название текстовой модели')
                SETTINGS.write_text(json.dumps(cfg), encoding='utf-8')
                SETTINGS.chmod(0o600)
                return self.send(200, {'saved':True})
            if path == '/api/workflow':
                validate(p)
                prepare(p)
                return self.send(200, {'workflow': p.get('workflow'), **overview(p)})
            if path == '/api/report': return self.send(200, report(validate(p)))
            if path not in ['/api/projects', '/api/restore', '/api/accept-workflow', '/api/analyze', '/api/approve-analysis', '/api/run-stage', '/api/approve-stage']: return self.send(404, {'error': 'Не найдено'})
            validate(p)
            with connection() as db:
                if path == '/api/restore':
                    p['id'] = str(uuid4())
                    p['name'] += ' (восстановлено)'
                    p['revision'] = 0
                old = db.execute('SELECT body FROM projects WHERE id=?', (p['id'],)).fetchone()
                if old and json.loads(old[0]).get('revision', 0) != p.get('revision', 0):
                    return self.send(409, {'error': 'Проект изменён в другом окне. Перезагрузите страницу.'})
                if path == '/api/analyze': analyze(p, ai_config())
                if path == '/api/approve-analysis': approve_analysis(p)
                if path == '/api/run-stage': run_stage(p, ai_config(), p.pop('_stage',''), p.pop('_feedback',''))
                if path == '/api/approve-stage': approve_stage(p, p.pop('_stage',''))
                prepare(p)
                if path == '/api/accept-workflow':
                    accept(p)
                db.execute('BEGIN IMMEDIATE')
                current = db.execute('SELECT body FROM projects WHERE id=?', (p['id'],)).fetchone()
                if current and json.loads(current[0]).get('revision',0) != p.get('revision',0):
                    return self.send(409, {'error':'Проект изменился во время операции. Перезагрузите страницу; запрос AI мог быть оплачен.'})
                p['revision'] = p.get('revision', 0) + 1
                p['updated'] = datetime.now(timezone.utc).isoformat()
                db.execute('INSERT OR REPLACE INTO projects VALUES (?, ?)', (p['id'], json.dumps(p, ensure_ascii=False)))
            self.send(200, p)
        except (ValueError, KeyError, TypeError) as e:
            self.send(400, {'error': str(e)})

if __name__ == '__main__':
    connection().close()
    host = os.environ.get('AI_STUDIO_HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '8000'))
    print(f'AI Studio running on {host}:{port}', flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
