import json,sys
from pathlib import Path
from world import fresh,save
BASE=Path(__file__).resolve().parent
if __name__=='__main__':
 src=Path(sys.argv[1] if len(sys.argv)>1 else input('Path to OLD JSON: ').strip().strip('"'))
 target=BASE/'saves/town_v4.json'
 if target.exists():raise RuntimeError('town_v4.json already exists. Back it up before importing.')
 old=json.loads(src.read_text(encoding='utf-8-sig'));npcs=json.loads((BASE/'npcs.json').read_text(encoding='utf8'));s=fresh(npcs)
 for k in ['day','food','hp','stamina','rub','loc','dig','mice','respect']:
  if type(old.get(k)) is int:s[k]=old[k]
 s['loc']=max(0,min(14,s['loc']));s['hp']=max(1,min(s['hp_max'],s['hp']))
 s['stamina']=max(0,min(s['stamina_max'],s['stamina']))
 if type(old.get('cig')) is int:s['inv']['cig']=max(0,old['cig'])
 if type(old.get('time')) is int:s['time']=max(0,min(1439,old['time']))
 for key in ['history','memory','relations']:
  source=old.get(key,old.get('memories',{}) if key=='memory' else {})
  if not isinstance(source,dict):continue
  for k,v in source.items():
   if k not in npcs:continue
   if key=='history' and isinstance(v,list):s[key][k]=[m for m in v if isinstance(m,dict) and m.get('role') in ('user','assistant') and isinstance(m.get('content'),str)][-160:]
   elif key=='memory' and isinstance(v,list):s[key][k]=[t for t in v if isinstance(t,str)][-15:]
   elif key=='relations' and type(v) is int:s[key][k]=max(-100,min(100,v))
 if isinstance(old.get('karma'),dict):
  for k in s['karma']:
   if type(old['karma'].get(k)) is int:s['karma'][k]=max(-100,min(100,old['karma'][k]))
 if isinstance(old.get('defeated'),list):s['defeated']=[k for k in old['defeated'] if k in npcs]
 save(s,target);print('Imported supported data into v8 save. Source was not changed.')
