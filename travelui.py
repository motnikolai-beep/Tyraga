"""Short interactive loading overlay; it finishes a travel exactly once and never changes saves before the panel is shown."""
import tkinter as tk
from PIL import Image,ImageTk
import comic_transition

class TravelCard:
    def __init__(self,app,dest):
        self.app=app;self.dest=dest;self.done=False;self.job=None
        src=app.world.s['loc']
        self.top=app.window('Переход · комикс',1220,755)
        image=comic_transition.render(app.base,app.world,src,dest)
        width,height=getattr(self.top,'_layout_size',(1220,755))
        image.thumbnail((max(1,width-20),max(1,height-72)),Image.Resampling.LANCZOS)
        self.top.transient(app.root);self.top.grab_set()
        self.top.protocol('WM_DELETE_WINDOW',self.finish)
        self.picture=ImageTk.PhotoImage(image)
        tk.Label(self.top,image=self.picture,bg='#090d12').pack(fill='both',expand=True,padx=10,pady=(10,2))
        tk.Button(self.top,text='Дальше ▶',command=self.finish,bg='#e5b767',fg='#111821',relief='flat',font=('Segoe UI',12,'bold'),padx=24,pady=8).pack(pady=9)
        self.top.bind('<Return>',lambda e:self.finish())
        self.top.bind('<Escape>',lambda e:self.finish())
        self.job=app.root.after(1800,self.finish)
    def finish(self):
        if self.done:return
        self.done=True
        if self.job:
            try:self.app.root.after_cancel(self.job)
            except tk.TclError:pass
        try:self.top.grab_release();self.top.destroy()
        except tk.TclError:pass
        self.app.transition=None
        self.app.go(self.dest)
        self.app.show_scene()
