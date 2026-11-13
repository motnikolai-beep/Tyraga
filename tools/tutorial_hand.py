"""Original small hand pointer for the v14 coach; rerun to redraw without external art."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
S=3;im=Image.new('RGBA',(54*S,70*S));d=ImageDraw.Draw(im)
def p(coords):return [(int(x*S),int(y*S)) for x,y in coords]
# Raised forefinger, curled knuckles and cuff: outlined warm comic silhouette.
shape=[(21,68),(17,61),(11,54),(7,48),(6,41),(10,39),(14,41),(20,47),(17,24),(16,11),(18,5),(22,3),(26,5),(28,11),(28,36),(30,29),(34,27),(38,29),(41,34),(42,32),(46,32),(50,36),(49,50),(45,59),(40,68)]
d.polygon(p(shape),fill='#09121b')
inner=[(23,63),(19,57),(13,50),(10,44),(12,43),(21,51),(23,49),(21,21),(20,10),(22,7),(24,9),(25,39),(29,42),(32,33),(35,30),(38,33),(38,43),(42,44),(44,36),(47,39),(46,48),(42,58),(38,63)]
d.polygon(p(inner),fill='#e7b66f')
d.line(p([(20,50),(29,56),(34,56)]),fill='#9e5d3c',width=2*S)
d.line(p([(22,12),(22,35)]),fill='#ffdd98',width=2*S)
d.rectangle((18*S,60*S,43*S,69*S),fill='#354d68',outline='#09121b',width=3*S)
im.resize((54,70),Image.Resampling.LANCZOS).save(Path(__file__).resolve().parents[1]/'assets/tutorial_hand.png')
