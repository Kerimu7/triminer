import threading, time, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "miners"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.slider import Slider
from duino_miner import DuinoMiner
from nimiq_miner import NimiqMiner
from riecoin_miner import RiecoinMiner
from pool_monitor import PoolMonitor

BG=get_color_from_hex("#060a0f")
PANEL=get_color_from_hex("#0b1118")
BORDER=get_color_from_hex("#1a2535")
TEXT=get_color_from_hex("#c8d8e8")
DIM=get_color_from_hex("#4a6070")
DUINO_C=get_color_from_hex("#f7c948")
NIMIQ_C=get_color_from_hex("#1a9aff")
RIEC_C=get_color_from_hex("#00e5a0")
GREEN=get_color_from_hex("#00ff88")
RED=get_color_from_hex("#ff4455")
YELLOW=get_color_from_hex("#ffaa00")
Window.clearcolor=BG

def fmt_hash(val,unit="H/s"):
    if val>=1000000:return f"{val/1000000:.2f} M{unit}"
    if val>=1000:return f"{val/1000:.2f} K{unit}"
    return f"{val:.1f} {unit}"

def make_label(text,size=14,color=TEXT,bold=False,halign="left",**kw):
    lbl=Label(text=text,font_size=dp(size),color=color,bold=bold,halign=halign,**kw)
    lbl.bind(size=lbl.setter("text_size"))
    return lbl

def dark_button(text,color=DUINO_C,callback=None,height=dp(44)):
    btn=Button(text=text,size_hint_y=None,height=height,background_normal="",background_color=(*color[:3],0.15),color=color,bold=True,font_size=dp(13))
    if callback:btn.bind(on_press=callback)
    return btn

class SetupScreen(Screen):
    def __init__(self,app_ref,**kw):
        super().__init__(**kw)
        self.app=app_ref
        self._build()
    def _build(self):
        root=BoxLayout(orientation="vertical",padding=dp(16),spacing=dp(10))
        root.add_widget(make_label("TRIMINER SETUP",size=20,color=DUINO_C,bold=True,halign="center"))
        root.add_widget(make_label("Enter wallet addresses to begin mining.",size=12,color=DIM,halign="center"))
        scroll=ScrollView()
        form=BoxLayout(orientation="vertical",spacing=dp(14),size_hint_y=None,padding=[0,dp(8),0,dp(8)])
        form.bind(minimum_height=form.setter("height"))
        form.add_widget(make_label("DUINO-COIN",size=13,color=DUINO_C,bold=True))
        self.duino_user=self._input("Username","e.g. MyDuinoUser")
        self.duino_threads=self._slider(DUINO_C)
        form.add_widget(self.duino_user)
        form.add_widget(self.duino_threads["layout"])
        form.add_widget(make_label("NIMIQ",size=13,color=NIMIQ_C,bold=True))
        self.nimiq_wallet=self._input("NQ Wallet","e.g. NQ07...")
        self.nimiq_threads=self._slider(NIMIQ_C)
        form.add_widget(self.nimiq_wallet)
        form.add_widget(self.nimiq_threads["layout"])
        form.add_widget(make_label("RIECOIN",size=13,color=RIEC_C,bold=True))
        self.riec_wallet=self._input("RIC Wallet","e.g. ric1q...")
        self.riec_threads=self._slider(RIEC_C)
        form.add_widget(self.riec_wallet)
        form.add_widget(self.riec_threads["layout"])
        scroll.add_widget(form)
        root.add_widget(scroll)
        root.add_widget(dark_button("START MINING ALL",color=GREEN,callback=self._on_start,height=dp(52)))
        self.add_widget(root)
    def _input(self,label,hint):
        box=BoxLayout(orientation="vertical",size_hint_y=None,height=dp(66),spacing=dp(2))
        box.add_widget(make_label(label,size=11,color=DIM))
        ti=TextInput(hint_text=hint,multiline=False,size_hint_y=None,height=dp(40),background_color=PANEL,foreground_color=TEXT,font_size=dp(13),padding=[dp(10),dp(10)])
        box.add_widget(ti)
        return box
    def _slider(self,color):
        box=BoxLayout(size_hint_y=None,height=dp(50),spacing=dp(8))
        box.add_widget(make_label("Threads",size=11,color=DIM,size_hint_x=0.3))
        sl=Slider(min=1,max=4,value=2,step=1,size_hint_x=0.5,value_track=True,value_track_color=[*color[:3],1])
        vl=make_label("2",size=13,color=color,bold=True,size_hint_x=0.2,halign="center")
        sl.bind(value=lambda i,v:setattr(vl,"text",str(int(v))))
        box.add_widget(sl);box.add_widget(vl)
        return{"layout":box,"slider":sl}
    def _on_start(self,*_):
        self.app.config={"duino_user":self.duino_user.children[0].text.strip(),"duino_threads":int(self.duino_threads["slider"].value),"nimiq_wallet":self.nimiq_wallet.children[0].text.strip(),"nimiq_pool":"eu.nimpool.io:8444","nimiq_threads":int(self.nimiq_threads["slider"].value),"riec_wallet":self.riec_wallet.children[0].text.strip(),"riec_pool":"ric.riesenprime.de:5000","riec_threads":int(self.riec_threads["slider"].value)}
        self.app.start_all_miners()
        self.manager.transition=SlideTransition(direction="left")
        self.manager.current="dashboard"

class MinerColumn(BoxLayout):
    def __init__(self,coin_id,color,name,unit,app_ref,**kw):
        super().__init__(orientation="vertical",spacing=dp(2),padding=[dp(4),dp(4)],**kw)
        self.coin_id=coin_id;self.color=color;self.unit=unit;self.app=app_ref
        self.add_widget(make_label(name,size=12,color=color,bold=True,halign="center"))
        self.hash_lbl=make_label("0",size=22,color=color,bold=True,halign="center")
        self.unit_lbl=make_label(unit,size=9,color=DIM,halign="center")
        self.status_lbl=make_label("IDLE",size=9,color=DIM,halign="center")
        self.add_widget(self.hash_lbl);self.add_widget(self.unit_lbl);self.add_widget(self.status_lbl)
        self.shares_lbl=self._row("Shares","0")
        self.reject_lbl=self._row("Rejected","0")
        self.earned_lbl=self._row("Earned","0.000")
        self.toggle_btn=Button(text="START",size_hint_y=None,height=dp(36),background_normal="",background_color=(*color[:3],0.2),color=color,bold=True,font_size=dp(11))
        self.toggle_btn.bind(on_press=self._toggle)
        self.add_widget(self.toggle_btn)
        self.log_scroll=ScrollView(size_hint_y=None,height=dp(80))
        self.log_box=BoxLayout(orientation="vertical",size_hint_y=None,spacing=dp(1))
        self.log_box.bind(minimum_height=self.log_box.setter("height"))
        self.log_scroll.add_widget(self.log_box)
        self.add_widget(self.log_scroll)
    def _row(self,label,value):
        row=BoxLayout(size_hint_y=None,height=dp(22))
        row.add_widget(make_label(label,size=9,color=DIM,size_hint_x=0.5))
        vl=make_label(value,size=10,color=self.color,bold=True,size_hint_x=0.5,halign="right")
        row.add_widget(vl);self.add_widget(row)
        return vl
    def update(self,state):
        hr=state["hashrate"]
        self.hash_lbl.text=f"{hr/1000:.2f}K" if hr>=1000 else f"{hr:.1f}"
        self.shares_lbl.text=str(state["accepted"])
        self.reject_lbl.text=str(state["rejected"])
        self.earned_lbl.text=f"{state.get('earned',0):.5f}"
        running=state["running"]
        self.status_lbl.text="MINING" if running else "IDLE"
        self.status_lbl.color=GREEN if running else DIM
        self.toggle_btn.text="STOP" if running else "START"
        self.toggle_btn.color=RED if running else self.color
        for msg,level in state.get("new_logs",[]):
            self._log(msg,level)
        state["new_logs"]=[]
    def _log(self,msg,level):
        c={"ok":GREEN,"warn":YELLOW,"err":RED,"info":DIM}.get(level,TEXT)
        lbl=make_label(msg,size=8,color=c);lbl.size_hint_y=None;lbl.height=dp(14)
        self.log_box.add_widget(lbl)
        if len(self.log_box.children)>30:self.log_box.remove_widget(self.log_box.children[-1])
        self.log_scroll.scroll_y=0
    def _toggle(self,*_):
        if self.app.state[self.coin_id]["running"]:self.app.stop_miner(self.coin_id)
        else:self.app.start_miner(self.coin_id)

class DashboardScreen(Screen):
    def __init__(self,app_ref,**kw):
        super().__init__(**kw)
        self.app=app_ref;self._build()
    def _build(self):
        root=BoxLayout(orientation="vertical")
        top=BoxLayout(size_hint_y=None,height=dp(48),padding=[dp(8),dp(6)],spacing=dp(6))
        top.add_widget(make_label("TRIMINER",size=15,color=DUINO_C,bold=True,size_hint_x=0.3))
        self.lbl_total=make_label("0 H/s",size=12,color=GREEN,bold=True,size_hint_x=0.3,halign="center")
        top.add_widget(self.lbl_total)
        top.add_widget(dark_button("MONITOR",color=NIMIQ_C,height=dp(34),callback=self._monitor))
        top.add_widget(dark_button("STOP ALL",color=RED,height=dp(34),callback=self._stop))
        root.add_widget(top)
        strip=BoxLayout(size_hint_y=None,height=dp(28),padding=[dp(8),0])
        self.lbl_uptime=make_label("UP:00:00:00",size=10,color=DIM,size_hint_x=0.4)
        self.lbl_acc=make_label("0 accepted",size=10,color=GREEN,size_hint_x=0.6,halign="right")
        strip.add_widget(self.lbl_uptime);strip.add_widget(self.lbl_acc)
        root.add_widget(strip)
        cols=BoxLayout(spacing=0)
        self.col_d=MinerColumn("duino",DUINO_C,"DUINO","H/s",self.app)
        self.col_n=MinerColumn("nimiq",NIMIQ_C,"NIMIQ","H/s",self.app)
        self.col_r=MinerColumn("riecoin",RIEC_C,"RIECOIN","P/s",self.app)
        cols.add_widget(self.col_d);cols.add_widget(self.col_n);cols.add_widget(self.col_r)
        root.add_widget(cols);self.add_widget(root)
        Clock.schedule_interval(self._refresh,2)
        self._t0=time.time()
    def _refresh(self,dt):
        s=self.app.state
        up=int(time.time()-self._t0);h,r=divmod(up,3600);m,sec=divmod(r,60)
        self.lbl_uptime.text=f"UP:{h:02d}:{m:02d}:{sec:02d}"
        total=sum(s[c]["hashrate"] for c in["duino","nimiq","riecoin"])
        self.lbl_total.text=fmt_hash(total)
        self.lbl_acc.text=f"{sum(s[c]['accepted'] for c in['duino','nimiq','riecoin'])} accepted"
        self.col_d.update(s["duino"]);self.col_n.update(s["nimiq"]);self.col_r.update(s["riecoin"])
    def _monitor(self,*_):
        self.manager.transition=SlideTransition(direction="left");self.manager.current="monitor"
    def _stop(self,*_):
        self.app.stop_all_miners();self.manager.transition=SlideTransition(direction="right");self.manager.current="setup"

class MonitorScreen(Screen):
    def __init__(self,app_ref,**kw):
        super().__init__(**kw)
        self.app=app_ref;self._tab="duino";self._build()
    def _build(self):
        root=BoxLayout(orientation="vertical")
        top=BoxLayout(size_hint_y=None,height=dp(48),padding=[dp(8),dp(6)],spacing=dp(6))
        top.add_widget(dark_button("BACK",color=DIM,height=dp(34),callback=self._back))
        top.add_widget(make_label("POOL MONITOR",size=14,color=TEXT,bold=True,halign="center"))
        top.add_widget(dark_button("REFRESH",color=NIMIQ_C,height=dp(34),callback=self._refresh_now))
        root.add_widget(top)
        tabs=BoxLayout(size_hint_y=None,height=dp(40))
        for coin,label,color in[("duino","DUINO",DUINO_C),("nimiq","NIMIQ",NIMIQ_C),("riecoin","RIECOIN",RIEC_C)]:
            btn=Button(text=label,background_normal="",background_color=(*color[:3],0.15),color=color,font_size=dp(11),bold=True)
            btn.bind(on_press=lambda x,c=coin:self._switch(c))
            tabs.add_widget(btn)
        root.add_widget(tabs)
        self.scroll=ScrollView()
        self.content=BoxLayout(orientation="vertical",spacing=dp(8),padding=[dp(12),dp(8)],size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter("height"))
        self.scroll.add_widget(self.content)
        root.add_widget(self.scroll);self.add_widget(root)
        Clock.schedule_interval(self._auto,30)
        self._switch("duino")
    def _switch(self,coin):
        self._tab=coin;self.content.clear_widgets()
        data=self.app.monitor_data.get(coin,{})
        color={"duino":DUINO_C,"nimiq":NIMIQ_C,"riecoin":RIEC_C}[coin]
        if not data:
            self.content.add_widget(make_label("Fetching pool data...",size=12,color=DIM,halign="center"));return
        if"error"in data:
            self.content.add_widget(make_label(f"API Error: {data['error']}",size=12,color=RED));return
        for k,v in data.items():
            if k=="last_updated":continue
            row=BoxLayout(size_hint_y=None,height=dp(36),padding=[dp(8),dp(4)])
            row.add_widget(make_label(k,size=11,color=DIM,size_hint_x=0.5))
            row.add_widget(make_label(str(v),size=12,color=color,bold=True,size_hint_x=0.5,halign="right"))
            self.content.add_widget(row)
        self.content.add_widget(make_label(f"Updated:{data.get('last_updated','--')}",size=9,color=DIM,halign="center"))
    def _refresh_now(self,*_):Clock.schedule_once(lambda dt:self._switch(self._tab),3)
    def _auto(self,dt):self._switch(self._tab)
    def _back(self,*_):self.manager.transition=SlideTransition(direction="right");self.manager.current="dashboard"

class TriMinerApp(App):
    def __init__(self,**kw):
        super().__init__(**kw)
        self.title="TriMiner";self.config={}
        self.monitor_data={"duino":{},"nimiq":{},"riecoin":{}}
        self.state={"duino":{"running":False,"hashrate":0,"accepted":0,"rejected":0,"earned":0,"new_logs":[]},"nimiq":{"running":False,"hashrate":0,"accepted":0,"rejected":0,"earned":0,"new_logs":[]},"riecoin":{"running":False,"hashrate":0,"accepted":0,"rejected":0,"earned":0,"new_logs":[]}}
        self.miners={};self.pool_monitor=None
    def build(self):
        sm=ScreenManager()
        sm.add_widget(SetupScreen(self,name="setup"))
        sm.add_widget(DashboardScreen(self,name="dashboard"))
        sm.add_widget(MonitorScreen(self,name="monitor"))
        return sm
    def start_all_miners(self):
        for c in["duino","nimiq","riecoin"]:self.start_miner(c)
        self._start_monitor()
    def start_miner(self,coin):
        cfg=self.config;st=self.state[coin]
        def on_status(msg,level):st["new_logs"].append((msg,level))
        def on_share(a,r):st["accepted"]=a;st["rejected"]=r
        def on_hashrate(hr):st["hashrate"]=hr
        if coin=="duino":
            if not cfg.get("duino_user"):return
            m=DuinoMiner(username=cfg["duino_user"],threads=cfg.get("duino_threads",2),on_status=on_status,on_share=on_share,on_hashrate=on_hashrate)
        elif coin=="nimiq":
            if not cfg.get("nimiq_wallet"):return
            h,p=self._hp(cfg["nimiq_pool"],"eu.nimpool.io",8444)
            m=NimiqMiner(wallet_address=cfg["nimiq_wallet"],threads=cfg.get("nimiq_threads",2),pool_host=h,pool_port=p,on_status=on_status,on_share=on_share,on_hashrate=on_hashrate)
        elif coin=="riecoin":
            if not cfg.get("riec_wallet"):return
            h,p=self._hp(cfg["riec_pool"],"ric.riesenprime.de",5000)
            m=RiecoinMiner(wallet_address=cfg["riec_wallet"],threads=cfg.get("riec_threads",2),pool_host=h,pool_port=p,on_status=on_status,on_share=on_share,on_hashrate=on_hashrate)
        self.miners[coin]=m;st["running"]=True;m.start()
    def stop_miner(self,coin):
        if coin in self.miners:self.miners[coin].stop();self.state[coin]["running"]=False;self.state[coin]["hashrate"]=0
    def stop_all_miners(self):
        for c in list(self.miners.keys()):self.stop_miner(c)
        if self.pool_monitor:self.pool_monitor.stop()
    def _start_monitor(self):
        cfg=self.config
        def on_update(coin,data):self.monitor_data[coin]=data
        self.pool_monitor=PoolMonitor(duino_user=cfg.get("duino_user",""),nimiq_wallet=cfg.get("nimiq_wallet",""),riecoin_wallet=cfg.get("riec_wallet",""),on_update=on_update)
        self.pool_monitor.start()
    def _hp(self,s,dh,dp_):
        try:p=s.split(":");return p[0],int(p[1]) if len(p)>1 else dp_
        except:return dh,dp_
    def on_stop(self):self.stop_all_miners()

if __name__=="__main__":TriMinerApp().run()
