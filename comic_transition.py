"""v13 comic-book travel panel: the actual departure and arrival backgrounds, not a fabricated screenshot.

Pure Pillow renderer. The words about the past come from a recent local event if there is one;
otherwise the card describes the place honestly. The future is a prospect, not a guarantee.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps,ImageEnhance
import core

# A factual fallback for every actual location; short enough for the loading card.
LEAVING=(
 'За спиной осталась камера: нары и чужие секреты.',
 'Двор остался за спиной: прожекторы гаснут вдалеке.',
 'Позади кухня: грохот посуды стихает.',
 'Вы вышли из коридора с его эхо и шагами.',
 'Позади душевая: пар оседает на плитке.',
 'Вы покинули жилой блок и его тесные нары.',
 'Позади оружейная-мастерская: звон железа остался внутри.',
 'Библиотека за спиной: тихий шорох страниц.',
 'Вы вышли из часовни и оставили свечи гореть.',
 'Позади изолятор: дверь закрылась беззвучно.',
 'Вы покинули театр; занавес остался позади.',
 'Вы вышли из подземного прохода на свет.')
AHEAD=(
 'Впереди тесная камера: здесь слушают даже стены.',
 'Впереди двор: вышка и чужие взгляды.',
 'Впереди кухня: пахнет хлебом и чужой пайкой.',
 'Впереди коридор: шаги здесь слышны заранее.',
 'Впереди душевая: горячая вода зависит от хозяина.',
 'Впереди жилой блок: долги и разговоры у нар.',
 'Впереди оружейная-мастерская: железо и работа.',
 'Впереди библиотека: книги, письма, чужие тайны.',
 'Впереди часовня: свечи и кошачьи глаза.',
 'Впереди изолятор: тишина и Анальгин.',
 'Впереди театр: сцена, свидания и ставки.',
 'Впереди подземный проход: тьма, шаги и выбор.')

def copy(w,src,dst):
    """What actually happened locally; what *may* await. No spoilers or remote/all-knowing events."""
    past=next((e['text'] for e in reversed(w.s.get('events',[]))
               if e.get('loc')==src and e.get('day')==w.s['day']
               and e.get('kind') not in ('zone_news','speech','denunciation','dialogue_income')
               and isinstance(e.get('text'),str)), None)
    # The feed can contain unrelated NPC news; don't assert that this happened here.
    left=('Только что: '+past[:145]+('…' if len(past)>145 else '')) if past else LEAVING[src]
    boss=next((k for k,l in core.BOSS_LOC.items() if l==dst and core.in_power(w,k)),None)
    if boss:
        right=AHEAD[dst]+' Здесь пока правит '+w.npcs[boss]['name']+'.'
    else:right=AHEAD[dst]+' Хозяина здесь больше нет.'
    return left,right

def _font(base,size,bold=False):
    paths=[Path(base)/'assets/fonts/Oswald-Bold.ttf'] if bold else []
    paths += [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),Path('C:/Windows/Fonts/arial.ttf'),Path(base)/'assets/fonts/Oswald-Bold.ttf']
    for p in paths:
        try:return ImageFont.truetype(str(p),size)
        except OSError:pass
    return ImageFont.load_default()

def _lines(draw,txt,font,width):
    out=[];line=''
    for word in txt.split():
        trial=(line+' '+word).strip()
        if draw.textbbox((0,0),trial,font=font)[2]>width and line:out.append(line);line=word
        else:line=trial
    if line:out.append(line)
    return out

def render(base,w,src,dst,size=(1200,680)):
    if src==dst or src not in range(12) or dst not in range(12):raise ValueError('Неверный переход')
    base=Path(base);W,H=size
    if W<600 or H<380:raise ValueError('Слишком маленькая панель')
    a=ImageOps.fit(Image.open(base/'assets'/f'loc_{src}.jpg').convert('RGB'),size,method=Image.Resampling.LANCZOS)
    b=ImageOps.fit(Image.open(base/'assets'/f'loc_{dst}.jpg').convert('RGB'),size,method=Image.Resampling.LANCZOS)
    a=ImageEnhance.Color(a).enhance(.7);b=ImageEnhance.Color(b).enhance(1.3)
    a=ImageEnhance.Brightness(a).enhance(.65);b=ImageEnhance.Brightness(b).enhance(.67)
    # Inked diagonal split; left = the past, right = the future. The same pair gives a different composition in reverse.
    mask=Image.new('L',size);m=ImageDraw.Draw(mask)
    m.polygon([(int(.56*W),0),(W,0),(W,H),(int(.41*W),H)],fill=255)
    panel=Image.composite(b,a,mask);d=ImageDraw.Draw(panel)
    ink='#0a1018';gold='#f4b64b';white='#f4ece0'
    d.line([(int(.56*W),0),(int(.41*W),H)],fill=ink,width=25)
    d.line([(int(.56*W)+12,0),(int(.41*W)+12,H)],fill=gold,width=7)
    d.rectangle((0,0,W,12),fill=ink);d.rectangle((0,H-14,W,H),fill=ink)
    # Comic captions are drawn on the picture; no text is baked into the location art.
    ftitle=_font(base,36,True);fbody=_font(base,21);fsmall=_font(base,18,True)
    from_name=core.NAMES[src].upper();to_name=core.NAMES[dst].upper()
    d.rounded_rectangle((28,26,int(.48*W),93),radius=8,fill=ink,outline=gold,width=3)
    name='ОТКУДА  /  '+from_name
    face=ftitle if d.textbbox((0,0),name,font=ftitle)[2]<int(.48*W)-65 else _font(base,25,True)
    d.text((44,35),name,font=face,fill=white)
    d.rounded_rectangle((int(.60*W),26,W-28,93),radius=8,fill=ink,outline=gold,width=3)
    name='КУДА  /  '+to_name
    face=ftitle if d.textbbox((0,0),name,font=ftitle)[2]<int(.38*W)-30 else _font(base,24,True)
    d.text((int(.62*W),35),name,font=face,fill=gold)
    left,right=copy(w,src,dst)
    for x0,x1,txt,heading in ((28,int(.46*W),left,'РАНЬШЕ'),(int(.57*W),W-28,right,'ВПЕРЕДИ')):
        lines=_lines(d,txt,fbody,x1-x0-26)
        height=max(120,74+len(lines)*30)
        y0=H-88-height
        d.rounded_rectangle((x0,y0,x1,H-88),radius=12,fill=ink,outline=gold,width=3)
        d.text((x0+14,y0+12),heading,font=fsmall,fill=gold)
        for i,line in enumerate(lines[:5]):d.text((x0+14,y0+44+i*30),line,font=fbody,fill=white)
    mins=core.hops(src,dst)*core.HOP
    foot='ПЕРЕХОД  •  %d МИН  •  %s → %s'%(mins,core.NAMES[src].upper(),core.NAMES[dst].upper())
    d.rounded_rectangle((int(.18*W),H-64,int(.82*W),H-20),radius=8,fill=ink,outline=gold,width=2)
    d.text((int(.2*W),H-58),foot,font=fsmall,fill=white)
    return panel
