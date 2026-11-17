import unittest
from unittest.mock import patch
import ai_production as ai

def project():
    return dict(name='Фильм',script='',history=[],scenes=[],shots=[],entities=[],rules=[],assets=[],intake={'text':'Кот идёт домой'})

def analysis():
    return dict(summary='История кота',script='',bible='Кот рыжий',entities=[dict(name='Кот',kind='Персонаж',description='Рыжий',reference='')],rules=[],scenes=[],references=[],missing=['Сценарий'],questions=[])

class AITests(unittest.TestCase):
    @patch('ai_production.call_model')
    def test_analysis_does_not_approve_or_overwrite(self,model):
        model.return_value=analysis();p=project();p['script']='Мой сценарий'
        ai.analyze(p,{})
        self.assertEqual(p['entities'],[])
        self.assertEqual(p['production']['status'],'На согласовании')
        ai.approve_analysis(p)
        self.assertEqual(p['script'],'Мой сценарий')
        self.assertEqual(p['entities'][0]['status'],'Черновик')
        with self.assertRaises(ValueError):ai.approve_analysis(p)

    @patch('ai_production.call_model')
    def test_approval_gate_and_revision(self,model):
        p=project();model.return_value=analysis();ai.analyze(p,{});ai.approve_analysis(p)
        with self.assertRaises(ValueError):ai.run_stage(p,{},'script')
        model.return_value={'text':'Библия'};ai.run_stage(p,{},'bible')
        self.assertNotEqual(p.get('bible'),'Библия')
        ai.approve_stage(p,'bible');self.assertEqual(p['bible'],'Библия')
        model.return_value={'text':'Сценарий'};ai.run_stage(p,{},'script')
        self.assertEqual(p['script'],'')
        ai.approve_stage(p,'script');self.assertEqual(p['script'],'Сценарий')

    @patch('ai_production.call_model')
    def test_bad_ai_links_rejected(self,model):
        p=project();a=analysis();a['references']=[{'asset_id':'invented'}];model.return_value=a
        with self.assertRaises(ValueError):ai.analyze(p,{})
        self.assertNotIn('production',p)

    def test_credentials_required(self):
        with self.assertRaises(ValueError):ai.call_model({},[])

    @patch('ai_production.call_model')
    def test_storyboard_validation(self,model):
        p=project();p['production']={'status':'Утверждено','analysis':analysis(),'stages':{'bible':{'status':'Утверждено','result':{'text':'b'}},'script':{'status':'Утверждено','result':{'text':'s'}}}}
        model.return_value={'text':'Планы','scenes':[{'name':'Дом','description':'Кот','shots':[{'name':'1','description':'Крупный план','duration':-5}]}]}
        with self.assertRaises(ValueError):ai.run_stage(p,{},'storyboard')
        self.assertEqual(p['shots'],[])
