import unittest
from production_assets import number_project,image_task
from ai_production import approve_stage

def project():
    return {'scenes':[{'id':'s','name':'Дом','description':'Кот дома','location_id':'l','character_ids':['c']}], 'shots':[{'id':'p','scene':'s','name':'План','description':'Кот входит','start':'','end':''}], 'entities':[{'id':'c','name':'Кот','kind':'Персонаж','description':'Рыжий, четыре лапы','reference':'c-ref','status':'Канон'},{'id':'l','name':'Дом','kind':'Локация','description':'Красная дверь','reference':'','status':'Черновик'}], 'assets':[{'id':'c-ref','name':'cat.png','type':'image/png','status':'Канон'}], 'rules':[]}

class AssetTests(unittest.TestCase):
    def test_locations_before_frames(self):
        p=project();task=image_task(p)
        self.assertEqual(task['entity_id'],'l');self.assertEqual(task['kind'],'reference')
    def test_cards_images_and_continuity(self):
        p=project();p['entities'][1].update(reference='l-ref',status='Утверждено');p['assets'].append({'id':'l-ref','name':'house.png','type':'image/png','status':'Утверждено'})
        task=image_task(p)
        self.assertEqual(task['references'],['c-ref','l-ref']);self.assertIn('четыре лапы',task['prompt']);self.assertIn('Красная дверь',task['prompt'])
        p['shots'][0]['start']='first';p['assets'].append({'id':'first','name':'first.png','type':'image/png','status':'Утверждено'})
        self.assertEqual(image_task(p)['references'],['c-ref','l-ref','first'])
    def test_scene_assignment_required(self):
        p=project();p['scenes'][0]['location_id']=''
        with self.assertRaisesRegex(ValueError,'назначьте локацию'):image_task(p)
    def test_unapproved_reference_blocks(self):
        p=project();p['entities'][0]['status']='Черновик'
        with self.assertRaisesRegex(ValueError,'Утвердите'):image_task(p)
    def test_shared_numbering_and_originals(self):
        p=project();p['scenes'].append({'id':'s2','name':'Снаружи','description':'','character_ids':['c']})
        number_project(p);self.assertEqual(p['assets'][0]['code'],'S001_S002_M001');self.assertEqual(p['assets'][0]['name'],'cat.png')
        first=p['assets'][0]['filename'];number_project(p);self.assertEqual(first,p['assets'][0]['filename'])
    def test_reference_approval(self):
        p=project();p['assets'].append({'id':'new','name':'House','type':'image/png','status':'Черновик'})
        p['production']={'stages':{'images':{'status':'На согласовании','result':{'entity_id':'l','asset_id':'new','kind':'reference'}}}}
        approve_stage(p,'images');self.assertEqual(p['entities'][1]['reference'],'new');self.assertEqual(p['assets'][1]['status'],'Утверждено')

class GenerationRequestTests(unittest.TestCase):
    def test_references_reach_provider_and_media_keep_scene(self):
        import io,json,base64
        from unittest.mock import patch
        from ai_production import generate_frame
        p=project();p['entities'][1].update(reference='l-ref',status='Канон')
        p['assets'][0]['data']='YQ=='
        p['assets'].append({'id':'l-ref','name':'house.png','type':'image/png','status':'Канон','data':'Yg=='})
        p['production']={'status':'Утверждено','stages':{'storyboard':{'status':'Утверждено'}}}
        reply=json.dumps({'data':[{'b64_json':base64.b64encode(b'\x89PNG\r\n\x1a\nfixture').decode()}]}).encode()
        with patch('ai_production.urllib.request.urlopen',return_value=io.BytesIO(reply)) as request:
            generate_frame(p,{'endpoint':'https://anymodel.org/v1','key':'test','image_model':'am/model'})
            body=json.loads(request.call_args.args[0].data)
            self.assertEqual(body['images'],['data:image/png;base64,YQ==','data:image/png;base64,Yg=='])
        self.assertEqual(p['assets'][-1]['scene_ids'],['s'])
        self.assertEqual(p['assets'][-1]['reference_ids'],['c-ref','l-ref'])
        number_project(p);self.assertTrue(p['assets'][-1]['filename'].startswith('S001_'))
