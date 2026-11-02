
"""Звук: процедурные эффекты и фоновые амбиенты по локациям (без внешних файлов). Воспроизведение только на Windows."""
import math,wave,struct,random
from pathlib import Path
RATE=11025
def write_wav(path,samples):
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE)
        w.writeframes(b''.join(struct.pack('<h',int(max(-1.0,min(1.0,x))*30000)) for x in samples))
def _env(i,n,att=.02,dec=True):
    a=min(1.0,i/max(1,n*att));return a*((1-i/n) if dec else 1)
def tone(freqs,dur,vol=.4,dec=True,saw=False):
    n=int(RATE*dur);out=[]
    for i in range(n):
        t=i/RATE;v=0
        for f in freqs:v+=(2*((t*f)%1)-1) if saw else math.sin(2*math.pi*f*t)
        out.append(v/len(freqs)*vol*_env(i,n,dec=dec))
    return out
def noise(dur,vol=.4,lp=.25,seed=1):
    r=random.Random(seed);n=int(RATE*dur);y=0;out=[]
    for i in range(n):
        y+=lp*(r.uniform(-1,1)-y);out.append(y*vol*(1-i/n))
    return out
def make_effect(name,vol=.7):
    if name=='click':s=tone([600],.05,.5)
    elif name=='hit':s=noise(.09,1.0,.5,3)+tone([110],.1,.8)
    elif name=='whoosh':s=noise(.14,.6,.12,4)
    elif name=='block':s=tone([300,900],.08,.7)
    elif name=='ko':s=tone([90],.5,.9)+noise(.3,.5,.1,5)
    elif name=='ok':s=tone([850],.16,.5)
    elif name=='step':s=noise(.07,1.0,.3,1)+[0]*int(RATE*.18)+noise(.07,.9,.3,2)
    elif name=='horn':s=tone([196,247],.5,.55,dec=False,saw=True)+tone([196,294],.8,.55,saw=True)
    elif name=='clang':s=tone([800,1370,2100],.6,.7)
    elif name=='ach':s=sum([tone([f],.14,.5) for f in (523,659,784,1047)],[])
    else:s=tone([440],.1,.4)
    return [x*vol for x in s]
def make_ambient(loc,seconds=8):
    n=int(RATE*seconds);r=random.Random(100+loc);root=48+(loc%6)*7;ks=[round(root*seconds),round(root*1.5*seconds),round(root*2.01*seconds)]
    lfo=2+loc%3;y=0;out=[]
    for i in range(n):
        t=i/n;v=0
        for j,k in enumerate(ks):v+=math.sin(2*math.pi*k*t)*(.5/(j+1))
        y+=.05*(r.uniform(-1,1)-y)
        out.append((v*(.7+.3*math.sin(2*math.pi*lfo*t))+y*.8)*.16)
    return out
class Sound:
    def __init__(self,base,volume=.7,music=.4):
        self.base=Path(base);self.vol=volume;self.mvol=music;self.ok=False;self.cur=None;self.paths={};self.mci=None
        try:
            import winsound,ctypes
            self.ws=winsound;self.mci=ctypes.windll.winmm.mciSendStringW;self.dir=self.base/'logs/sounds';self.dir.mkdir(parents=True,exist_ok=True);self.ok=True
        except Exception:pass
    def set_volume(self,v):self.vol=max(0.0,min(1.0,v))
    def set_music(self,v):
        self.mvol=max(0.0,min(1.0,v))
        if not self.ok:return
        if self.mvol<=0:self.stop_music()
        elif self.cur is not None:self._cmd('setaudio bgm volume to %d'%int(self.mvol*1000))
    def _path(self,name,vol):
        key=(name,round(vol,1))
        if key not in self.paths:
            p=self.dir/('%s_%d.wav'%(name,int(vol*10)))
            if not p.exists():write_wav(p,make_effect(name,vol))
            self.paths[key]=str(p)
        return self.paths[key]
    def play(self,name):
        if not self.ok or self.vol<=0:return
        try:self.ws.PlaySound(self._path(name,self.vol),self.ws.SND_FILENAME|self.ws.SND_ASYNC|self.ws.SND_NODEFAULT)
        except Exception:pass
    def _cmd(self,c):
        try:self.mci(c,None,0,None)
        except Exception:pass
    def stop_music(self):
        if self.cur is not None:self._cmd('stop bgm');self._cmd('close bgm');self.cur=None
    def music(self,loc):
        if not self.ok:return
        if self.mvol<=0:return self.stop_music()
        if loc==self.cur:return
        try:
            p=self.dir/('amb_%d.wav'%loc)
            if not p.exists():write_wav(p,make_ambient(loc))
        except Exception:return
        self.stop_music();self._cmd('open "%s" type waveaudio alias bgm'%p);self._cmd('setaudio bgm volume to %d'%int(self.mvol*1000));self._cmd('play bgm repeat');self.cur=loc
    def close(self):self.stop_music()
