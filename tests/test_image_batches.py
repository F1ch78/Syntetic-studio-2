import unittest
from unittest.mock import patch
from test_production_assets import project
from production_assets import image_tasks
from ai_production import generate_batch,approve_stage

class BatchTests(unittest.TestCase):
    def ready(self):
        p=project();p['entities'][1].update(reference='l-ref',status='Канон');p['assets'].append({'id':'l-ref','name':'House','type':'image/png','status':'Канон'})
        p['shots'].append({**p['shots'][0],'id':'p2'})
        p['production']={'status':'Утверждено','stages':{'storyboard':{'status':'Утверждено'}}};p['image_batch_size']=10
        return p
    def test_starts_batch_does_not_use_unapproved_end(self):
        tasks=image_tasks(self.ready(),10)
        self.assertEqual([(t['shot_id'],t['kind']) for t in tasks],[('p','start'),('p2','start')])
    def test_missing_references_deduplicated(self):
        p=project();p['entities'][0]['reference']='';p['shots'].append({**p['shots'][0],'id':'p2'})
        tasks=image_tasks(p,10)
        self.assertEqual([t['entity_id'] for t in tasks],['c','l'])
    def test_invalid_counts(self):
        for value in [0,11,True,1.5,'2']:
            p=self.ready();p['image_batch_size']=value
            with self.assertRaises(ValueError):generate_batch(p,{})
    @patch('ai_production.generate_frame')
    def test_partial_success_preserved_and_approved(self,generate):
        p=self.ready()
        def work(local,config,task):
            if task['shot_id']=='p2':raise ValueError('Provider failure')
            local['assets'].append({'id':'new','status':'Черновик'})
            local['production']['stages']['images']={'result':{**task,'asset_id':'new'}}
        generate.side_effect=work
        generate_batch(p,{})
        r=p['production']['stages']['images']['result']
        self.assertEqual(len(r['items']),1);self.assertEqual(len(r['errors']),1)
        self.assertEqual(p['shots'][0]['start'],'')
        approve_stage(p,'images')
        self.assertEqual(p['shots'][0]['start'],'new');self.assertEqual(p['shots'][1]['start'],'')
