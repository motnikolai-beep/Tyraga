"""Render original comic-ink item icons. No external art/model required. Run: python tools/item_icons.py"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter

OUT=Path(__file__).resolve().parents[1]/'assets/items'
SIZE=192
INK='#09121b';GOLD='#f3bf62';PAPER='#e9e2cf';STEEL='#a7c3cf';RED='#dc7763';BLUE='#5c97a7'

def poly(d,points,fill):
    d.polygon(points,fill=INK)
    cx=96;cy=90
    # line thickness is achieved by drawing a slightly smaller polygon rather than a generic Pillow stroke
    d.polygon([(cx+(x-cx)*.92,cy+(y-cy)*.92) for x,y in points],fill=fill)

def line(d,points,fill=INK,width=6):d.line(points,fill=fill,width=width,joint='curve')

def draw(kind,d):
    if kind=='fist':
        poly(d,[(38,86),(50,68),(71,70),(86,62),(99,70),(117,66),(139,78),(147,102),(120,132),(110,147),(68,145),(44,123)],GOLD)
        for x in (69,91,115):line(d,[(x,77),(x-3,99)],INK,4)
        line(d,[(41,103),(72,113),(75,131)],INK,5)
    elif kind=='shiv':
        poly(d,[(43,142),(59,155),(102,109),(88,95)],'#94634c')
        poly(d,[(82,102),(102,122),(113,109),(94,90)],GOLD)
        poly(d,[(97,92),(112,108),(151,34),(143,27)],STEEL)
        line(d,[(111,91),(139,40)],PAPER,4)
        line(d,[(54,130),(72,144)],INK,4)
    elif kind=='armor':
        poly(d,[(54,38),(79,47),(114,47),(141,38),(155,65),(142,79),(140,151),(53,151),(49,79),(37,65)],'#617781')
        poly(d,[(72,56),(121,56),(130,91),(119,131),(73,131),(63,91)],'#425967')
        line(d,[(65,61),(79,82),(111,82),(127,61)],GOLD,6)
        line(d,[(79,91),(113,91)],PAPER,4)
        for y in (108,121):line(d,[(84,y),(108,y)],INK,4)
    elif kind=='bandage':
        poly(d,[(48,127),(126,48),(147,69),(69,148)],PAPER)
        for x,y in ((72,104),(92,84),(112,64)):
            line(d,[(x-10,y-9),(x+14,y+14)],RED,5)
        d.rectangle((82,88,112,118),fill=INK)
        d.rectangle((87,93,107,113),fill='#efd2b1')
        for x,y in ((91,98),(101,98),(91,108),(101,108)):d.ellipse((x-2,y-2,x+2,y+2),fill=RED)
    elif kind=='phone':
        d.rounded_rectangle((57,25,136,160),radius=12,fill=INK)
        d.rounded_rectangle((65,32,128,151),radius=7,fill='#546d75')
        d.rounded_rectangle((71,42,122,124),radius=3,fill='#1f3943')
        line(d,[(76,55),(113,55)],GOLD,4)
        line(d,[(76,66),(103,66)],PAPER,3)
        d.ellipse((91,133,101,143),fill=GOLD)
    elif kind=='tea':
        poly(d,[(51,44),(133,41),(142,143),(54,151)],'#83633c')
        poly(d,[(59,55),(126,54),(132,131),(62,138)],'#9c7646')
        d.ellipse((72,62,121,104),fill=INK)
        d.ellipse((77,67,116,99),fill=GOLD)
        for y in (114,123):line(d,[(77,y),(118,y)],PAPER,4)
        for x,y in ((49,135),(139,49)):line(d,[(x,y),(x+13,y-6)],INK,4)
    elif kind=='key':
        d.ellipse((40,34,109,102),fill=INK)
        d.ellipse((48,42,101,94),fill=GOLD)
        d.ellipse((64,58,85,79),fill=INK)
        poly(d,[(94,84),(110,74),(157,128),(148,142),(136,132),(130,141),(119,128),(112,136)],GOLD)
        line(d,[(111,96),(143,129)],PAPER,3)
    elif kind=='letter':
        poly(d,[(31,52),(161,52),(161,140),(31,140)],PAPER)
        line(d,[(37,57),(96,105),(155,57)],INK,7)
        line(d,[(39,134),(81,101)],INK,5)
        line(d,[(153,134),(112,101)],INK,5)
        d.ellipse((84,100,110,126),fill=RED)
    elif kind=='parcel':
        poly(d,[(29,77),(95,41),(165,72),(166,137),(96,162),(29,139)],'#a47748')
        line(d,[(29,77),(95,103),(166,72)],INK,7)
        line(d,[(95,103),(96,161)],INK,7)
        line(d,[(61,58),(132,87),(132,148)],GOLD,8)
        line(d,[(49,144),(49,86),(115,47)],GOLD,7)
    elif kind=='cig':
        poly(d,[(33,109),(137,70),(151,88),(44,129)],PAPER)
        poly(d,[(30,108),(61,97),(72,113),(41,128)],'#c5844b')
        d.ellipse((146,70,165,90),fill=RED)
        for x,y in ((113,56),(121,46),(131,36)):line(d,[(x,y),(x-5,y-12),(x,y-21)],STEEL,4)
    elif kind=='coin':
        d.ellipse((36,28,158,158),fill=INK)
        d.ellipse((44,36,150,150),fill=GOLD)
        d.ellipse((53,44,141,141),outline=INK,width=6)
        line(d,[(94,62),(94,125)],INK,7)
        line(d,[(75,64),(109,64),(115,80),(79,87),(74,101),(80,114),(113,114)],INK,6)
    elif kind=='gloves':
        for offset in (0,45):
            poly(d,[(36+offset,55),(77+offset,50),(92+offset,65),(93+offset,108),(68+offset,139),(42+offset,124),(32+offset,96)],'#8b4738')
            line(d,[(40+offset,79),(76+offset,77)],GOLD,5)
            line(d,[(43+offset,117),(74+offset,119)],INK,5)
    elif kind=='boots':
        for offset in (0,63):
            poly(d,[(30+offset,41),(71+offset,41),(74+offset,112),(91+offset,121),(96+offset,142),(27+offset,144)],'#6a5350')
            for y in (76,90):line(d,[(39+offset,y),(64+offset,y)],GOLD,4)
            line(d,[(30+offset,132),(89+offset,132)],INK,6)
    else:raise ValueError(kind)

def make(kind):
    im=Image.new('RGBA',(SIZE,SIZE),(0,0,0,0));d=ImageDraw.Draw(im)
    d.rounded_rectangle((5,5,187,187),radius=30,fill=INK,outline=GOLD,width=5)
    d.rounded_rectangle((13,13,179,179),radius=23,fill='#263a48')
    # angular comic panel highlights
    d.polygon([(17,16),(130,16),(17,105)],fill='#304958')
    d.polygon([(177,134),(177,177),(132,177)],fill='#192a35')
    draw(kind,d)
    d.line((18,170,59,170),fill=GOLD,width=4)
    d.line((140,22,174,22),fill=GOLD,width=4)
    OUT.mkdir(parents=True,exist_ok=True)
    im.save(OUT/(kind+'.png'))

if __name__=='__main__':
    for kind in ('fist','shiv','armor','bandage','phone','tea','key','letter','parcel','cig','coin','gloves','boots'):make(kind)
    print('Icons:',len(list(OUT.glob('*.png'))))
