import socket,hashlib,threading,time,requests
from datetime import datetime
POOL_HOST="server.duinocoin.com"
POOL_PORT=2813
MINER_VER="TriMiner/1.0"

class DuinoMiner:
    def __init__(self,username,password="",threads=2,on_status=None,on_share=None,on_hashrate=None):
        self.username=username;self.password=password;self.threads=threads
        self.on_status=on_status;self.on_share=on_share;self.on_hashrate=on_hashrate
        self.running=False;self.accepted=0;self.rejected=0
        self._workers=[];self._hashrates={};self._lock=threading.Lock()

    def start(self):
        self.running=True
        self._emit("Connecting to Duino-Coin pool...","info")
        for i in range(self.threads):
            t=threading.Thread(target=self._worker,args=(i,),daemon=True)
            t.start();self._workers.append(t)
        threading.Thread(target=self._agg,daemon=True).start()

    def stop(self):
        self.running=False;self._emit("Miner stopped.","warn")

    def get_balance(self):
        try:
            r=requests.get(f"https://server.duinocoin.com/v4/users/{self.username}",timeout=8)
            d=r.json()
            if d.get("result"):
                return round(float(d["result"].get("balance",{}).get("balance",0)),6)
        except:pass
        return None

    def get_pool_stats(self):
        try:return requests.get("https://server.duinocoin.com/v4/statistics",timeout=8).json()
        except:return{}

    def _worker(self,wid):
        sock=None
        while self.running:
            try:
                sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                sock.settimeout(30);sock.connect((POOL_HOST,POOL_PORT))
                ver=sock.recv(100).decode().strip()
                self._emit(f"[W{wid}] Server v{ver}","info")
                while self.running:
                    sock.send(f"JOB,{self.username},LOW\n".encode())
                    job=sock.recv(256).decode().strip().split(",")
                    if len(job)<3:continue
                    lh,eh,diff=job[0],job[1],int(job[2])
                    self._emit(f"[W{wid}] Job diff={diff}","info")
                    res,hc,el=self._solve(lh,eh,diff)
                    hr=int(hc/el) if el>0 else 0
                    with self._lock:self._hashrates[wid]=hr
                    sock.send(f"{res},{hr},{MINER_VER},MEDIUM\n".encode())
                    fb=sock.recv(64).decode().strip()
                    if fb.upper().startswith("GOOD"):
                        self.accepted+=1
                        self._emit(f"[W{wid}] Share accepted [{self.accepted}]","ok")
                    elif fb.upper().startswith("BAD"):
                        self.rejected+=1
                        self._emit(f"[W{wid}] Share rejected","warn")
                    if self.on_share:self.on_share(self.accepted,self.rejected)
            except Exception as e:
                self._emit(f"[W{wid}] Error:{e} retrying...","err");time.sleep(5)
            finally:
                if sock:
                    try:sock.close()
                    except:pass

    def _solve(self,lh,eh,diff):
        start=time.time();hc=0
        for n in range(diff*100+1):
            if not self.running:break
            if hashlib.sha1(f"{lh}{n}".encode()).hexdigest()==eh:
                el=time.time()-start
                return n,hc,max(el,0.001)
            hc+=1
        el=time.time()-start
        return 0,hc,max(el,0.001)

    def _agg(self):
        while self.running:
            time.sleep(2)
            with self._lock:total=sum(self._hashrates.values())
            if self.on_hashrate:self.on_hashrate(total)

    def _emit(self,msg,level="info"):
        ts=datetime.now().strftime("%H:%M:%S")
        if self.on_status:self.on_status(f"[{ts}] {msg}",level)
