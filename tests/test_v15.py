"""v15: three actual days, bounded offline consequences and epistemic prompt separation."""
import json,sys,threading,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import ai,boss15,core,life15,meta,former
from world import World
from story_data import SCENES,available
NP=json.loads((ROOT/'npcs.json').read_text(encoding='utf8'))
def mk():return World(NP,meta.new_state(NP),seed=9)

class ThreeDays(unittest.TestCase):
    def test_letter_requires_separate_days_and_remains_optional(self):
        w=mk();c=core.C(w);c['done'].append('c1_intro');w.s['day']=2
        self.assertIn('life15_letter_start',list(available(w)))
        core.apply(w,{'life_letter':'quiet'});core.finish_scene(w,'life15_letter_start')
        self.assertNotIn('life15_letter_middle',list(available(w)))
        w.s['day']=3;self.assertIn('life15_letter_middle',list(available(w)))
        self.assertIn('Никто',life15.letter_intro(w))
        core.apply(w,{'life_letter':'postpone'});core.finish_scene(w,'life15_letter_middle')
        self.assertNotIn('life15_letter_end',list(available(w)))
        w.s['day']=4;self.assertIn('life15_letter_end',list(available(w)))
        self.assertIn('Лист',life15.letter_end_intro(w))
        core.apply(w,{'life_letter':'keep_link'});core.finish_scene(w,'life15_letter_end')
        self.assertEqual(life15.state(w)['letters']['stage'],3)
        self.assertNotIn('life15_letter_end',list(available(w)))
        self.assertIn('связь',life15.journal(w)[0])
        self.assertEqual(w.s['rub'],20)

    def test_stages_cannot_be_sped_up_or_replayed(self):
        w=mk();w.s['day']=6
        core.apply(w,{'life_letter':'help'})
        before=len(w.s['events']);core.apply(w,{'life_letter':'share'})
        self.assertEqual(len(w.s['events']),before)
        core.apply(w,{'life_letter':'honest'});self.assertEqual(life15.state(w)['letters']['stage'],1)
        w.s['day']=7;core.apply(w,{'life_letter':'honest'})
        core.apply(w,{'life_letter':'close'});self.assertEqual(life15.state(w)['letters']['stage'],2)
        w.s['day']=8;core.apply(w,{'life_letter':'close'})
        self.assertEqual(life15.state(w)['letters']['stage'],3)

    def test_work_and_contacts_are_preparation_not_release(self):
        w=mk();w.work();life15.work(w)
        self.assertEqual(life15.state(w)['outside']['skill_days'],[1])
        self.assertIn('полезной работы 1',life15.journal(w)[-1])
        self.assertFalse(core.C(w).get('ending'))
        pair=':'.join(sorted(('polkan','zina')))
        core.C(w)['npc_relations'][pair]=-9
        self.assertIn(-9,[x['отношение'] for x in boss15.context(w,'polkan')['знакомые']])
        self.assertNotIn('знакомые',boss15.context(w,'cenz'))

    def test_old_save_and_daily_choice_bounded(self):
        w=mk();self.assertNotIn('life15',core.C(w))
        core.C(w)['abs']=23*60;core.sleep(w)
        self.assertEqual(sum(p['id']=='life15_round' for p in core.C(w)['pending']),1)
        self.assertEqual(w.s['day'],2)
        w.s['food']=3;core.apply(w,{'life_routine':'share'})
        self.assertEqual(w.s['food'],3)
        w.s['food']=6;core.apply(w,{'life_routine':'share'})
        self.assertEqual(w.s['food'],0)
        first=len(w.s['events']);core.apply(w,{'life_routine':'share'})
        self.assertEqual(len(w.s['events']),first)
        self.assertIn('распорядок',life15.journal(w)[1].lower())

class Bosses(unittest.TestCase):
    def test_all_twelve_have_motives_not_omniscient(self):
        self.assertEqual(set(boss15.MOTIVES),set(core.BOSS_LOC))
        w=mk()
        for k in core.BOSS_LOC:
            self.assertIn('личный_мотив',boss15.context(w,k))
            self.assertNotIn('личный_мотив',boss15.context(w,'kol'))
        self.assertNotIn('личный_мотив',boss15.context(w,'kol'))
        self.assertIn(NP['zub']['name'],boss15.journal(w)[0])
        self.assertNotIn(NP['cenz']['name'],' '.join(boss15.journal(w)))
        core.boss_down(w,'cenz');self.assertIn('возможный_путь',boss15.context(w,'cenz'))
        self.assertIn(NP['cenz']['name'],' '.join(boss15.journal(w)))

    def test_actual_choices_change_trust_fear_without_inventing_rumors(self):
        w=mk();w.decision('kol','help')
        self.assertEqual(life15.context(w,'kol')['доверие_по_поступкам'],5)
        w.decision('kol','theft')
        self.assertGreater(life15.context(w,'kol')['опасение_по_поступкам'],0)
        self.assertEqual(life15.context(w,'cenz')['доверие_по_поступкам'],0)
        core.boss_down(w,'zub');former.peace(w,'zub')
        self.assertTrue(boss15.context(w,'zub')['память_о_падении']['примирились'])
        self.assertGreater(life15.context(w,'zub')['доверие_по_поступкам'],0)

    def test_letter_knowledge_cannot_be_leaked_to_remote_people(self):
        w=mk();w.s['day']=2;life15.letter(w,'quiet')
        self.assertNotIn('письмо',life15.context(w,'graf'))
        self.assertNotIn('письмо',life15.context(w,'cenz'))
        self.assertNotIn('письмо',life15.context(w,'kol'))
        self.assertNotIn('письмо',life15.context(w,'zub'))
        # A later shared reply is known to its addressee, not to every NPC by magic.
        w.s['day']=3;life15.letter(w,'honest')
        self.assertIn('письмо',life15.context(w,'cenz'))
        self.assertIsNone(life15.context(w,'cenz')['письмо']['выбор_игрока'])
        self.assertNotIn('письмо',life15.context(w,'graf'))

    def test_real_chat_prompt_contains_only_this_boss_perspective(self):
        w=mk();w.s['day']=2;life15.letter(w,'quiet')
        class Engine:
            cfg={'CHAT_HISTORY_MESSAGES':'5','CHAT_FAST_MODE':'true','CHAT_EVALUATE_KARMA':'false','CHAT_THREAT_AI':'false'}
            def __init__(self):self.messages=[]
            def chat(self,msg,**kw):self.messages=msg;return 'Я слушаю.'
        eng=Engine();ai.generate_chat(eng,w,'polkan','Как дела?',lambda x:None,threading.Event())
        sysmsg=eng.messages[0]['content'];ctx=json.loads(sysmsg.split('\n',1)[1])
        self.assertEqual(ctx['мотивы_хозяина']['личный_мотив'],boss15.MOTIVES['polkan'][0])
        self.assertNotIn('письмо',ctx['быт'])
        self.assertNotIn(boss15.MOTIVES['cenz'][0],sysmsg)
        self.assertNotIn('содержание письма',sysmsg)

if __name__=='__main__':unittest.main()
