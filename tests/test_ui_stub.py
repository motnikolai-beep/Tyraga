"""Headless UI test; not an actual Tk rendering or GPU test."""
import unittest,sys,tempfile,random,types,shutil
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
class Widget:
 def __init__(self,*a,**kw):
  self.master=a[0] if a else None;self.props=dict(kw);self.children=[];self.content='';self.value=kw.get('value',0);self.index=0
  if isinstance(self.master,Widget):self.master.children.append(self)
 def __getattr__(self,k):
  if k.startswith('create_'):return lambda *a,**kw:1
  return lambda *a,**kw:None
 def config(self,*a,**kw):self.props.update(kw)
 configure=config
 def cget(self,k):return self.props.get(k,'')
 def winfo_children(self):return self.children[:]
 def winfo_width(self):return 1200
 def winfo_height(self):return 600
 def get(self,*a):return self.content if a else self.value
 def set(self,v):self.value=v
 def insert(self,pos,v,*a):self.content+=v
 def delete(self,*a):self.content=''
 def current(self,i=None):
  if i is not None:self.index=i
  return self.index
 def bbox(self,*a):return (400,90,850,220)
 def after(self,*a):return 'timer'
 def destroy(self):
  if isinstance(self.master,Widget) and self in self.master.children:self.master.children.remove(self)
fake=types.ModuleType('tkinter')
for n in ['Tk','Frame','Label','Button','Canvas','Text','Toplevel','LabelFrame','Radiobutton','IntVar','StringVar','BooleanVar','Scrollbar','Checkbutton','Menu','Menubutton','Scale','Entry','DoubleVar']:setattr(fake,n,Widget)
fake.TclError=RuntimeError;fake.ttk=types.SimpleNamespace(Style=Widget,Combobox=Widget);fake.messagebox=types.SimpleNamespace(showwarning=lambda *a:None,showinfo=lambda *a:None,showerror=lambda *a:None,askyesno=lambda *a:True);sys.modules['tkinter']=fake
import main,ai
def env(original,b):
 # Личный .env в репозиторий не входит: без него берём те же безопасные настройки, что и сборка.
 src=original/'.env';(b/'.env').write_text(src.read_text(encoding='utf8') if src.is_file() else 'CHAT_FAST_MODE=true\nGOSSIP_ENABLED=true\n',encoding='utf8')
from minigames import Mini
class Smoke(unittest.TestCase):
 def test_scenes_bubbles_games_battle_modes(self):
  import core
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    app=main.App(Widget());app.new_game('normal');app.menu.hide();self.assertIsNotNone(app.map);app.toggle_map();app.map.draw();app.toggle_map()
    for loc in range(12):app.go(loc);self.assertTrue(app.hits);self.assertEqual('zub' in [k for rect,k in app.hits],loc==0);self.assertIn(app.npc,app.world.witnesses())
    app.toggle_cover();self.assertFalse(app.cover);app.toggle_cover();app.go(0);app.select('zub');app.do_activity('bed');app.render_cards();app.stash_window();app.caste_window()
    for kind in ['porridge','poker','chess','tunnel','dance','factory']:
     app.world.s.update(dig=0,cig=30);m=Mini(app,kind);app.mini=m;r=random.Random(8)
     for _ in range(3000):
      if m.done:break
      if kind=='porridge':m.porr(r.randrange(36))
      elif kind=='poker':m.poker(r.randrange(4))
      elif kind=='chess':m.chess(r.randrange(3))
      elif kind=='tunnel':m.move(*r.choice([(0,-1),(0,1),(1,0),(-1,0)]))
      elif kind=='dance':m.dance(r.randrange(4))
      else:m.target('gvo');m.factory('пишет стихи')
     self.assertTrue(m.done,kind);m.close();m.close();self.assertIsNone(app.mini)
    app.fight('zub');bw=app.battle_window;self.assertIs(app.battle,bw.eng)
    Ev=lambda code,sym='':types.SimpleNamespace(keycode=code,keysym=sym)
    for _ in range(80):bw.tick(1/30)
    self.assertEqual(bw.eng.phase,'fight');rr=random.Random(4)
    for i in range(9000):
     if i%7==0:bw.on_down(Ev(rr.choice([74,75,85,73,79,80])))
     if i%23==0:bw.on_down(Ev(76));bw.on_up(Ev(76))
     bw.tick(1/30)
     if bw.eng.phase=='over':break
    bw.paused=True;bw.tick(1/30);bw.paused=False
    bw.close();self.assertIsNone(app.battle);self.assertIn(bw.eng.result,('Победа','Поражение','Ничья','Отступление'))
    # Исход боя случаен. Если бот победил босса, тот «свергнут» и уходит из камеры — тогда ссоре в чате не с кем начаться.
    # Возвращаем его на место, чтобы проверка чата не зависела от того, кто выиграл.
    core.C(app.world).update(ousted=[],pending=[]);app.refresh();app.select('zub');app.close_chat(True)
    app.world.s['npc_health']={};text='щас порежу тебя';meta={'npc':'zub','text':text,'private':False};o=ai.zero();o.update(reply='Ну попробуй.',_combat_intent={'speaker':'player','target':'npc','evidence':text})
    app.job={'id':'test','kind':'chat','meta':meta};app.liveq.put(('old','zub','wrong'));app.liveq.put(('test','zub','Частичный'));app.q.put(('test',o,None));app.poll();self.assertIsNotNone(app.battle);self.assertTrue(app.bubble_hits);app.battle_window.close();app.chat_combat(meta,o);self.assertIsNone(app.battle)
    self.assertIn('Ну попробуй',app.world.s['history']['zub'][-1]['content']);app.show_history();app.reset_chat();self.assertEqual(app.world.s['history']['zub'],[])
    app.toggle_mode();self.assertEqual(app.engine.cfg['CHAT_FAST_MODE'],'false');app.toggle_mode();self.assertEqual(app.engine.cfg['CHAT_FAST_MODE'],'true');app.journal();app.residents();app.respect_window()
   finally:main.BASE=original

 def test_all_scenes_play_through_ui(self):
  import uikit,core
  from story_data import SCENES
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None),patch.object(uikit,'QuickGame',lambda app,kind,cb,parent=None:cb(True)):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    app=main.App(Widget());app.new_game('normal');app.menu.hide();app.base=b;r=random.Random(2)
    for sid in SCENES:
     app.world.s['cig']=30;app.world.s['rub']=100;ev=uikit.EventWindow(app,sid,{'slot':'Обед'});self.assertIs(app.modal,ev)
     for _ in range(12):
      chs=[c for c in ev.cur['ch'] if core.req_ok(app.world,c.get('req',{}))]
      if not chs:break
      ev.pick(r.choice(chs));g=ev.opts.children[-1].props.get('command') if ev.opts.children else None
      if not g or ev.done:break
      g()
     if not ev.done:ev.finish()
     self.assertIsNone(app.modal)
    # Случайное прохождение сцен оставляет в очереди свои события; проверяем, что очередь открывает именно ожидающую сцену.
    core.C(app.world)['pending'][:]=[{'t':'scene','id':'meal','vars':{'slot':'Завтрак'}}];app.pump();self.assertIsNotNone(app.modal);self.assertEqual(app.modal.sid,'meal');app.modal.finish()
   finally:main.BASE=original

 def test_menu_saves_settings_achievements(self):
  import meta,core
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    app=main.App(Widget());self.assertFalse(app.has_game);self.assertTrue(app.menu.visible)
    app.menu.hide();self.assertTrue(app.menu.visible)
    for sc in ['main','new','howto','authors','ach']:app.menu.go(sc)
    app.menu.go('new');app.menu.diffvar.set('hard');app.menu.start_new();self.assertTrue(app.has_game);self.assertEqual(core.diff(app.world)['name'],'Строгий режим');self.assertEqual(app.world.s['cig'],8);self.assertFalse(app.menu.visible)
    app.world.s['rub']=250;app.refresh();self.assertIn('rich',meta.ach_store(b)['unlocked'])
    app.menu.show();app.menu.go('slots',mode='save');app.menu.go('slots',mode='load')
    app.save_slot('slot1');self.assertIsNotNone(meta.summary(b,'slot1'));app.world.s['day']=7;app.load_slot('slot1');self.assertEqual(app.world.s['day'],1)
    for tab in ['gfx','snd','ai','game']:
     app.menu.go('settings',tab=tab)
     if tab=='gfx':app.menu.vars['brightness'].set(.8);app.menu.vars['fullscreen'].set(False)
     if tab=='ai':app.menu.vars['CHAT_TEMPERATURE'].set(.9);app.menu.vars['CHAT_MAX_OUTPUT_TOKENS'].set('512');app.menu.check_files()
     app.menu.apply_settings()
    self.assertAlmostEqual(app.settings['brightness'],.8);self.assertEqual(app.engine.cfg['CHAT_MAX_OUTPUT_TOKENS'],'512');self.assertIn('CHAT_MAX_OUTPUT_TOKENS=512',(b/'.env').read_text(encoding='utf8'))
    self.assertTrue((b/'settings.json').exists());app.quick_save();app.toggle_fullscreen();app.new_game('easy');self.assertTrue((b/'saves/before_newgame.json').exists())
   finally:main.BASE=original

 def test_minimal_ui_and_v10_windows(self):
  import uikit,core
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    app=main.App(Widget());app.new_game('normal');app.menu.hide();app.settings['seen_howto']=False
    self.assertFalse(app.chat_open);app.select('zub');self.assertTrue(app.chat_open);self.assertTrue(app.close_chat(True));self.assertFalse(app.chat_open);self.assertFalse(app.close_chat())
    app.status.config(text='привет');app.status.config(text='');app.open_chat();app.close_chat(True)
    app.journal_window();app.show_stats();self.assertTrue(app.menu.visible);app.menu.hide()
    tut=uikit.Tutorial(app)
    for _ in range(6):tut.step()
    self.assertTrue(app.settings['seen_howto'])
    for loc in (7,10,0,3):
     app.world.s['loc']=loc;app.refresh();app.render_cards()
    app.world.s['loc']=7;app.world.s['cig']=9;app.do_activity('exchange');self.assertIsNotNone(app.modal);app.modal.finish()
    # Заточку заказывают там, где сборка поселила мастера (v11 — локация 7, v12 — оружейная-мастерская).
    for loc in range(len(core.NAMES)):
     app.world.s['loc']=loc
     if any(a['id']=='order_shiv' for a in core.activities(app.world)):break
    app.refresh()
    app.do_activity('order_shiv');app.modal.pick(app.modal.cur['ch'][0]);app.modal.finish();self.assertTrue(core.has(app.world,'shiv_ordered'))
    app.world.s['loc']=0;app.do_activity('scout_zub');app.modal.finish()
    core.say(app.world,'тест');app.refresh()
    app.menu.show();app.menu.go('settings',tab='snd');app.menu.vars['music'].set(.2);app.menu.apply_settings();self.assertAlmostEqual(app.settings['music'],.2)
    core.C(app.world)['ending']='shaw';app.show_stats();app.menu.go('stats');app.menu.go('main')
   finally:main.BASE=original
class MastersOfPlaces(unittest.TestCase):
 """v12: четыре новых босса на экране локации и в занятиях (Tk заменён заглушкой, окно не рисуется)."""
 def app(self,td,original):
  b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
  app=main.App(Widget());app.new_game('normal');app.menu.hide();app.base=b;return app
 def test_new_bosses_on_screen_and_in_activities(self):
  import core
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   try:
    app=self.app(td,original)
    for k,(loc,act,_what) in core.TURF.items():
     # На экране локации двое: жилец и хозяин; хозяина можно выбрать и заговорить с ним.
     app.world.s['loc']=loc;app.refresh();faces=[x for rect,x in app.hits]
     self.assertIn(k,faces);self.assertEqual(len(faces),2);app.select(k);self.assertEqual(app.npc,k);app.close_chat(True)
     # Занятие открывает сцену «по правилам хозяина», и говорит в ней он сам.
     app.world.s['cig']=9;app.world.s['stamina']=90;app.render_cards();app.do_activity(act)
     self.assertIsNotNone(app.modal,k);self.assertEqual(app.modal.sid,act+'_'+k);self.assertEqual(app.modal.cur['who'],k)
     app.modal.pick(app.modal.cur['ch'][1]);app.modal.finish();self.assertIsNone(app.modal)
    # Письмо — раз в день: вторая попытка не открывает сцену, а объясняет почему.
    app.world.s['loc']=7;app.refresh();self.assertTrue(core.has(app.world,'letter_today'));app.do_activity('letter')
    self.assertIsNone(app.modal);self.assertIn('письмо',app.status.l.cget('text'))
    # Когда хозяин свергнут, то же занятие открывает обычную сцену.
    core.boss_down(app.world,'kip');core.C(app.world)['pending'].clear();app.world.s['loc']=4;app.refresh();app.do_activity('wash')
    self.assertEqual(app.modal.sid,'wash');app.modal.finish()
   finally:main.BASE=original
 def test_ousted_boss_stays_as_former(self):
  import core
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   try:
    app=self.app(td,original)
    # Выбран сосед босса. Босса свергают — он остаётся в локации «бывшим»: с пометкой у имени и без боссовского запаса здоровья.
    app.world.s['loc']=1;app.refresh();app.select('zina');app.close_chat(True);self.assertEqual(set(app.local_ids),{'zina','polkan'})
    core.boss_down(app.world,'polkan');app.refresh()
    self.assertEqual(set(app.local_ids),{'zina','polkan'});self.assertEqual(app.npc,'zina')
    self.assertEqual(sorted(x for rect,x in app.hits),['polkan','zina'])
    self.assertIn('бывший',core.shown_name(app.world,'polkan'));self.assertEqual(core.max_hp(app.world,'polkan'),90);self.assertEqual(core.max_hp(app.world,'zina'),90)
    # С бывшим можно говорить, и его сцена «после падения» ждёт в его локации.
    app.select('polkan');self.assertEqual(app.npc,'polkan');app.close_chat(True)
    self.assertIn('ex_polkan',list(__import__('story_data').available(app.world)))
   finally:main.BASE=original
class SocialDossierUI(unittest.TestCase):
 """Stub widgets exercise navigation and event flow; this is NOT a real Windows/Tk screenshot."""
 def test_profile_scene_and_friend_search(self):
  import core,profile
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    app=main.App(Widget());app.new_game('normal','cat');app.menu.hide()
    app.profile_window()
    def walk(widget):
     yield widget
     for child in widget.children:yield from walk(child)
    self.assertTrue(any('Оскорбление начальственного кота' in x.content for x in walk(app.root)))
    self.assertEqual(profile.origin(app.world),profile.ORIGINS['cat'])
    app.world.s['relations']['kol']=45;app.world.s['companion']='kol'
    core.C(app.world)['inv']['shiv']=1
    core.C(app.world)['pending'][:]=[{'t':'scene','id':'shmon'}]
    app.pump();self.assertEqual(app.modal.sid,'friend_search')
    app.modal.pick(app.modal.cur['ch'][0]);app.modal.finish()
    self.assertEqual(core.C(app.world)['inv']['shiv'],0)
    self.assertEqual(core.stash_get(app.world,0)['shiv'],1)
    self.assertFalse(core.C(app.world)['pending'])
   finally:main.BASE=original

class ComicTravelUI(unittest.TestCase):
 """Opening and skipping the loading screen must commit exactly one journey."""
 def test_travel_overlay_blocks_input_then_commits_once(self):
  import core
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    app=main.App(Widget());app.new_game('normal');app.menu.hide()
    start=core.C(app.world)['abs'];self.assertEqual(app.world.s['loc'],0)
    app.toggle_map();app.travel(1)
    self.assertIsNotNone(app.transition)
    self.assertTrue(app.blocked())
    self.assertEqual(app.world.s['loc'],0)  # travel is only committed when card closes
    self.assertEqual(core.C(app.world)['abs'],start)
    card=app.transition;app.travel(2)       # a second input is ignored
    self.assertEqual(app.world.s['loc'],0)
    card.finish();self.assertIsNone(app.transition)
    self.assertEqual(app.world.s['loc'],1)
    self.assertEqual(core.C(app.world)['abs'],start+core.HOP)
    self.assertEqual(app.view,'scene')
    card.finish();self.assertEqual(core.C(app.world)['abs'],start+core.HOP)
    # A distant room is directly selectable; returning uses the reverse comic.
    from comic_transition import render
    with patch('comic_transition.render',wraps=render) as pictures:
     for target in (11,1):
      source=app.world.s['loc'];before=core.C(app.world)['abs']
      app.toggle_map();app.map.draw()
      x0,y0,x1,y1=app.map.rects[target]
      app.map.click(types.SimpleNamespace(x=(x0+x1)//2,y=(y0+y1)//2))
      pictures.assert_called_with(app.base,app.world,source,target)
      self.assertEqual(app.world.s['loc'],source)
      self.assertIsNotNone(app.transition)
      app.transition.finish()
      self.assertEqual(app.world.s['loc'],target)
      self.assertEqual(core.C(app.world)['abs']-before,core.hops(source,target)*core.HOP)
   finally:main.BASE=original

if __name__=='__main__':unittest.main()
