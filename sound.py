import math,wave,struct
from pathlib import Path
class Sound:
 def __init__(self,base):
  self.ok=False;self.paths={}
  try:
   import winsound
   self.ws=winsound;p=Path(base)/'logs/sounds';p.mkdir(parents=True,exist_ok=True)
   for name,freq,dur in [('click',600,.05),('hit',140,.12),('ok',850,.16)]:
    f=p/(name+'.wav');rate=22050;n=int(rate*dur)
    with wave.open(str(f),'wb') as w:
     w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(b''.join(struct.pack('<h',int(4000*math.sin(2*math.pi*freq*i/rate)*(1-i/n))) for i in range(n)))
    self.paths[name]=str(f)
   self.ok=True
  except Exception:pass
 def play(self,name):
  if self.ok:
   try:self.ws.PlaySound(self.paths[name],self.ws.SND_FILENAME|self.ws.SND_ASYNC|self.ws.SND_NODEFAULT)
   except Exception:pass
