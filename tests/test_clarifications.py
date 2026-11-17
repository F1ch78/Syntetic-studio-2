import unittest
import json
from unittest.mock import patch
from clarifications import context,signature,require_current
from ai_production import analyze,approve_analysis,run_stage
from test_ai_production import project,analysis

class ClarificationTests(unittest.TestCase):
    def test_stale_answers_block_approval(self):
        p=project();p['production']={'status':'На согласовании','analysis':analysis()};p['clarifications']=[{'kind':'question','prompt':'Какой голос?','answer':'Низкий','asset_ids':[]}]
        with self.assertRaisesRegex(ValueError,'ещё не учтены'):approve_analysis(p)
    @patch('ai_production.call_model')
    def test_answers_and_files_passed_to_ai(self,model):
        p=project();p['assets']=[{'id':'doc','name':'world.txt','type':'text/plain','text':'Город ночью','sha256':'d'},{'id':'img','name':'city.png','type':'image/png','data':'YQ==','sha256':'i'}]
        p['clarifications']=[{'kind':'missing','prompt':'Город?','answer':'Вот референс','asset_ids':['doc','img']}]
        model.return_value=analysis();analyze(p,{})
        content=model.call_args.args[1][1]['content'];text=json.loads(content[0]['text'])
        self.assertEqual(text['clarifications'][0]['attachments'][0]['text'],'Город ночью')
        self.assertTrue(any(x['type']=='image_url' for x in content))
        require_current(p);approve_analysis(p)
        self.assertEqual(p['production']['status'],'Утверждено')
        p['clarifications'][0]['answer']='Город утром'
        with self.assertRaises(ValueError):run_stage(p,{},'bible')
    @patch('ai_production.call_model',side_effect=ValueError('API failed'))
    def test_failure_preserves_previous_analysis(self,model):
        p=project();p['production']={'analysis':analysis(),'stages':{'bible':{'result':'old'}}}
        original=json.dumps(p,sort_keys=True)
        with self.assertRaises(ValueError):analyze(p,{})
        self.assertEqual(original,json.dumps(p,sort_keys=True))
    def test_bad_attachment_link_rejected(self):
        p=project();p['clarifications']=[{'answer':'a','asset_ids':['missing']}]
        with self.assertRaises(ValueError):context(p)
