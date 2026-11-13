"""Real art coordinates, saved world effects and headless Tk click path (not a Windows screenshot)."""
import json,sys,tempfile,shutil,types,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import core,hotspots16
from world import World
NP=json.loads((ROOT/'npcs.json').read_text(encoding='utf8'))
def mk():return World(NP,seed=11)

class Polygons(unittest.TestCase):
    def test_all_twelve_places_both_shipped_art_styles_have_two_visible_targets(self):
        for loc in range(12):
            for style in ('legacy','master'):
                marks=hotspots16.objects(loc,style)
                self.assertGreaterEqual(len(marks),2,(loc,style))
                self.assertEqual(len({id for id,_,_ in marks}),len(marks))
                for id,title,poly in marks:
                    self.assertIn(id,hotspots16.LORE)
                    self.assertTrue(title)
                    self.assertGreaterEqual(len(poly),3)
                    self.assertTrue(all(0<=u<=1 and 0<=v<=1 for u,v in poly))
                    pixels=hotspots16.transform(poly,(1200,675),(3840,2160))
                    cx=sum(x for x,y in pixels)/len(pixels);cy=sum(y for x,y in pixels)/len(pixels)
                    self.assertTrue(hotspots16.inside(cx,cy,pixels),(loc,id,style))
        self.assertNotEqual([x[0] for x in hotspots16.objects(7,'master')],[x[0] for x in hotspots16.objects(7,'legacy')])
        self.assertIn('bed',[x[0] for x in hotspots16.objects(0,'master')])

    def test_cover_and_letterboxing_align_actual_image_and_hit(self):
        for cover in (True,False):
            area=hotspots16.transform([(.5,.5),(.1,.2)],(1200,600),(3840,2160),cover)
            self.assertEqual(area[0],(600,300))
            self.assertNotEqual(area[1],hotspots16.transform([(.1,.2)],(1200,600),(3840,2160),not cover)[0])
        for style,width in [('legacy',2560),('master',3840)]:
            with tempfile.TemporaryDirectory() as td:
                p=Path(td)/'assets';p.mkdir()
                Image.new('RGB',(width,int(width*9/16)),'#101720').save(p/'loc_0.jpg')
                self.assertEqual(hotspots16.variant(td,0),style)
                items=hotspots16.placed(td,0,(1200,600),cover=True)
                self.assertEqual(len(items),2)
                poly=items[0][2];x=sum(q[0] for q in poly)/len(poly);y=sum(q[1] for q in poly)/len(poly)
                self.assertEqual(hotspots16.hit(x,y,items)[0],'bed')
                self.assertIsNone(hotspots16.hit(1199,599,items))

class Actions(unittest.TestCase):
    def test_bed_rest_is_capped_and_night_sleep_advances_day(self):
        w=mk();a=core.C(w)['abs'];w.s['stamina']=50
        self.assertIn('Присесть',hotspots16.perform(w,'bed','legacy'))
        self.assertEqual(core.C(w)['abs']-a,20)
        self.assertEqual(w.s['stamina'],56)
        before=len(w.s['events']);self.assertIn('уже',hotspots16.perform(w,'bed','legacy'))
        self.assertEqual(len(w.s['events']),before)
        self.assertTrue(all(e['public'] is False for e in w.s['events'] if e['kind']=='environment'))
        core.C(w)['abs']=23*60;day=w.s['day']
        self.assertIn('Сон до утра',hotspots16.perform(w,'bed','legacy'))
        self.assertEqual(w.s['day'],day+1)
        self.assertEqual(core.hhmm(w),'06:00')
        self.assertIn('Место отдыха',' '.join(hotspots16.journal(w)))

    def test_only_visible_props_and_no_money_farming(self):
        w=mk();w.s['loc']=7;money=w.s['rub']
        with self.assertRaises(ValueError):hotspots16.perform(w,'bed','master')
        with self.assertRaises(ValueError):hotspots16.perform(w,'machine','master')
        with self.assertRaises(ValueError):hotspots16.perform(w,'shelves','unknown')
        self.assertIn('книгу',hotspots16.perform(w,'shelves','master'))
        self.assertEqual(w.s['rub'],money)
        self.assertEqual(len(core.C(w)['environment16']),1)
        self.assertIn('Книги',' '.join(hotspots16.journal(w)))
        w.s['loc']=9;core.C(w)['abs']=23*60;old=w.s['day']
        hotspots16.perform(w,'cot','master');self.assertEqual(w.s['day'],old+1)

    def test_real_ui_dialog_has_action_and_does_not_duplicate_npc_click(self):
        from test_ui_stub import Widget,main,env
        original=main.BASE
        with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
            b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
            try:
                app=main.App(Widget());app.new_game('normal');app.menu.hide()
                self.assertEqual(app.scene_variant,hotspots16.variant(b,0))
                bed=next(poly for id,_,poly in app.env_shapes if id=='bed')
                x=sum(a for a,_ in bed)/len(bed);y=sum(a for _,a in bed)/len(bed)
                app.click(types.SimpleNamespace(x=x,y=y))
                self.assertIsNotNone(app.env_window)
                self.assertTrue(app.blocked())
                def walk(item):
                    yield item
                    for child in item.children:yield from walk(child)
                btn=next(child for child in walk(app.env_window) if child.props.get('text')=='Присесть на нары')
                start=core.C(app.world)['abs'];btn.props['command']()
                self.assertIsNone(app.env_window)
                self.assertEqual(core.C(app.world)['abs'],start+20)
                self.assertEqual(app.world.s['loc'],0)
            finally:main.BASE=original

if __name__=='__main__':unittest.main()
