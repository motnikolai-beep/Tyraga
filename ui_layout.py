"""Screen-bound Tk geometry and reusable scrolling containers.

Pure sizing functions are unit tested without a display; scroll_frame uses real Tk
when available. A small screen cannot fit fixed 1540x980/840x860 windows.
"""

def screen_size(root):
    try:
        w=int(root.winfo_screenwidth());h=int(root.winfo_screenheight())
        if w>=640 and h>=480:return w,h
    except (TypeError,ValueError,AttributeError):pass
    return 1600,1000  # headless widget stubs; not a guessed real display size

def fit(requested,screen,margin=64,floor=320):
    """Fit dimensions within display while keeping usable minimum sizes."""
    return max(min(floor,screen-margin),min(requested,max(1,screen-margin)))

def window_size(w,h,screen):
    sw,sh=screen
    return fit(w,sw,margin=32,floor=360),fit(h,sh,margin=72,floor=300)

def main_size(screen):
    sw,sh=screen
    return fit(1540,sw,margin=32,floor=760),fit(980,sh,margin=72,floor=520)

def card_count(width):return max(2,min(7,(max(0,int(width))-75)//175))

def text_wrap(width,padding=50):return max(180,int(width)-padding)

def scroll_frame(parent,bg,height=None):
    """Return an ordinary Frame in a scrollable Canvas. Its children stay testable."""
    import tkinter as tk
    outer=tk.Frame(parent,bg=bg)
    canvas=tk.Canvas(outer,bg=bg,highlightthickness=0,height=height or 400)
    bar=tk.Scrollbar(outer,orient='vertical',command=canvas.yview)
    canvas.configure(yscrollcommand=bar.set)
    bar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
    body=tk.Frame(canvas,bg=bg)
    item=canvas.create_window((0,0),window=body,anchor='nw')
    body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
    # Bind only this view; wheel scrolling never hijacks the main canvas or chat.
    canvas.bind('<MouseWheel>',lambda e:canvas.yview_scroll(-int(e.delta/120) if e.delta else 0,'units'))
    return outer,body

def fight_viewport(window_width,window_height,arena=(960,470)):
    """Uniformly fit the whole combat arena, never crop a fighter or the HUD."""
    aw,ah=arena
    factor=min(1.0,max(1,window_width-24)/aw,max(1,window_height-24)/ah)
    return max(1,round(aw*factor)),max(1,round(ah*factor)),factor


def scale_canvas(canvas,factor):
    """Scale vector arena geometry and text fonts together; image assets are pre-sized."""
    if factor>=.999:return
    import re
    canvas.scale('all',0,0,factor,factor)
    try:items=canvas.find_all()
    except (AttributeError,TypeError):return
    for item in items or ():
        if canvas.type(item)!='text':continue
        name=canvas.itemcget(item,'font')
        match=re.search(r'(?<!\d)(\d+)(?!\d)',name)
        if not match:continue
        size=max(7,round(int(match.group())*factor))
        # Tk's canvas scaling never scales text/font automatically.
        canvas.itemconfigure(item,font=('Segoe UI',size,'bold' if 'bold' in name else 'normal'))
        width=canvas.itemcget(item,'width')
        if width:
            try:canvas.itemconfigure(item,width=max(1,int(float(width)*factor)))
            except ValueError:pass

def menu_chars(screen_width,scale=1.0,limit=60):
    """Approximate Tk character widths conservatively for positive-point UI fonts."""
    return max(14,min(limit,int((screen_width-150)/(10*max(.8,scale)))))
