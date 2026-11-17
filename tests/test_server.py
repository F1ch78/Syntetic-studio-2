import base64
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

_tmp = tempfile.TemporaryDirectory()
os.environ['AI_STUDIO_DATA'] = _tmp.name
spec = importlib.util.spec_from_file_location('server', Path(__file__).parents[1] / 'server.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)

def project():
    return dict(id='p1', name='Фильм', scenes=[], shots=[], entities=[], rules=[], assets=[], history=[], script='')

class StudioTests(unittest.TestCase):
    def test_missing_materials_reported(self):
        p=project()
        p['scenes']=[dict(id='s',name='Сцена')]
        p['shots']=[dict(id='shot',name='План',scene='s',status='Черновик')]
        self.assertEqual(len(s.report(s.validate(p))['issues']),5)

    def test_missing_scene_rejected(self):
        p=project(); p['shots']=[dict(id='x',scene='absent')]
        with self.assertRaises(ValueError): s.validate(p)

    def test_archive_integrity(self):
        p=project(); data=b'original file'
        p['assets']=[dict(id='a',name='a',data=base64.b64encode(data).decode(),sha256=hashlib.sha256(data).hexdigest())]
        s.validate(p)
        p['assets'][0]['data']=base64.b64encode(b'corrupt').decode()
        with self.assertRaises(ValueError): s.validate(p)

    def test_database_persists(self):
        with s.connection() as db: db.execute('INSERT INTO projects VALUES (?,?)',('persist','{}'))
        with s.connection() as db: self.assertEqual(db.execute('SELECT body FROM projects WHERE id=?',('persist',)).fetchone()[0],'{}')

if __name__=='__main__': unittest.main()
