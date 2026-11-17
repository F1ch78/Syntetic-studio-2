import unittest
from workflow import prepare, accept, overview


def project(script):
    return dict(script=script, scenes=[], shots=[], entities=[], rules=[], assets=[])

class WorkflowTests(unittest.TestCase):
    def test_proposals_require_confirmation(self):
        p=project('СЦЕНА 1. Дом\nКот спит.\nСЦЕНА 2. Улица\nКот идёт.')
        prepare(p)
        self.assertEqual(len(p['workflow']['proposals']),2)
        self.assertEqual(p['scenes'],[])
        accept(p)
        self.assertEqual(len(p['shots']),2)
        accept(p)
        self.assertEqual(len(p['shots']),2)

    def test_revision_preserves_existing_work(self):
        p=project('Сцена 1\nСтарый текст')
        accept(p); original=p['shots'][0].copy()
        p['script']='Сцена 1\nНовый текст'
        prepare(p)
        self.assertFalse(p['workflow']['confirmed'])
        accept(p)
        self.assertEqual(p['shots'][0],original)
        self.assertEqual(len(p['scenes']),2)

    def test_plain_text_fallback_and_empty(self):
        p=project('');prepare(p);self.assertNotIn('workflow',p)
        p['script']='Просто история без заголовков'
        prepare(p);self.assertEqual(len(p['workflow']['proposals']),1)
        self.assertIn('не найдены',p['workflow']['notice'])

    def test_status_is_based_on_materials(self):
        p=project('Сцена 1\nТекст');accept(p)
        r=overview(p)
        self.assertEqual(r['completed'],2)
        self.assertEqual(r['next']['tab'],'Персонажи и локации')
        self.assertEqual(sum(s['status']=='Недоступно в этой версии' for s in r['steps']),6)
        p['shots'][0]['start']='missing'
        self.assertEqual(overview(p)['steps'][4]['status'],'Не начато')
