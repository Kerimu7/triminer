import socket,json,threading,time,hashlib,struct,requests
from datetime import datetime
POOL_HOST="ric.riesenprime.de"
POOL_PORT=5000
MINER_VER="TriMiner/1.0"
OFFSETS=[0,4,6,10,12,16]

def is_prime(n):
    if n<2:return False
    if n==2:return True
    if n%2==0:return False
    sp=[2,3,5,7,11,13,17,19,23,29,31,37]
    if n in sp:return True
    d,r=n-1,0
    while d%2==0:d//=2;r+=1
    for a in sp:
        if a>=n:continue
        x=pow(a,d,n)
        if x==1 or x==n-1:continue
        for _ in range(r-1):
            x=pow(x,2,n)
            if x==n-1:break
        else:return False
    return True

def is_constellation(p):
    return all(is_prime(p+o) for o in OFFSETS)

class RiecoinMiner:
    def __init__(self,wallet_address,threads=2,pool_host=POOL_HOST,pool_port=POOL_PORT,on_status=None,on_share=None,on_hashrate=None):
        self.wallet=wallet_address;self.threads=threads
        self.pool_host=pool_host;self.pool_port=pool_port
        self.on_status=on_status;self.on_share=on_share;self.on_hashrate=on_hashrate
        self.running=False;self.accepted=0;self.rejected=0
        self._job=None;self._job_lock=threading.Lock()
        self._sock=None;self._msg_id=1
        self._hashrates={};self._hr_lock=threading.Lock()
        self._en1="";self._en2_size=4

    def start(self):
        self.running=True
        threading.Thread(target=self._net,daemon=True).start()
        threading.Thread(target=self._agg,daemon=True).start()
        self._emit("Connecting to Riecoin pool...","info")

    def stop(self):
        self.running=False
        if self._sock:
            try:self._sock.close()
            except:pass
        self._emit("Miner stopped.","warn")

    def get_stats(self):
        try:return requests.get(f"https://ric.riesenprime.de/api/miner/{self.wallet}",timeout=8).json()
        except:return{}

    def get_pool_stats(self):
        try:return requests.get("https://ric.riesenprime.de/api/pool",timeout=8).json()
        except:return{}

    def _net(self):
        while self.running:
            try:
                self._sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                self._sock.settimeout(60)
                self._sock.connect((self.pool_host,self.pool_port))
                self._emit(f"Connected to {self.pool_host}","info")
                self._send({"id":self._nid(),"method":"mining.subscribe","params":[MINER_VER]})
                self._send({"id":self._nid(),"method":"mining.authorize","params":[self.wallet,"x"]})
                buf=""
                while self.running:
                    chunk=self._sock.recv(4096).decode(errors="ignore")
                    if not chunk:break
                    buf+=chunk
                    while"\n"in buf:
                        line,buf=buf.split("\n",1)
                        if line.strip():self._handle(json.loads(line.strip()))
            except Exception as e:
                self._emit(f"Error:{e} reconnecting...","err");time.sleep(5)

    def _handle(self,msg):
        m=msg.get("method","")
        if m=="mining.notify":
            p=msg["params"]
            with self._job_lock:
                self._job={"job_id":p[0],"prevhash":p[1],"coinb1":p[2],
                           "coinb2":p[3],"merkle_branch":p[4],"version":p[5],
                           "nbits":p[6],"ntime":p[7],"clean":p[8]}
            self._emit(f"New job {p[0][:10]}...","info")
            for i in range(self.threads):
                threading.Thread(target=self._mine,args=(i,),daemon=True).start()
        elif msg.get("id") and"result"in msg:
            res=msg["result"]
            if isinstance(res,list) and len(res)>=3:
                self._en1=res[1] or"";self._en2_size=res[2] or 4
            elif res is True:
                self.accepted+=1
                self._emit(f"Share accepted [{self.accepted}]","ok")
                if self.on_share:self.on_share(self.accepted,self.rejected)
            elif res is False:
                self.rejected+=1
                self._emit("Share rejected","warn")
                if self.on_share:self.on_share(self.accepted,self.rejected)

    def _mine(self,wid):
        with self._job_lock:job=dict(self._job) if self._job else None
        if not job:return
        nonce=wid*1000000;t0=time.time()
        while self.running:
            with self._job_lock:
                if self._job and self._job["job_id"]!=job["job_id"]:break
            en2=struct.pack("<I",nonce).hex().zfill(self._en2_size*2)
            cb=bytes.fromhex(job["coinb1"]+self._en1+en2+job["coinb2"])
            cbh=hashlib.sha256(hashlib.sha256(cb).digest()).digest()
            merkle=cbh
            for b in job["merkle_branch"]:
                merkle=hashlib.sha256(hashlib.sha256(merkle+bytes.fromhex(b)).digest()).digest()
            hdr=(bytes.fromhex(job["version"])+bytes.fromhex(job["prevhash"])+merkle+
                 bytes.fromhex(job["ntime"])+bytes.fromhex(job["nbits"])+struct.pack("<I",nonce))
            hh=int.from_bytes(hashlib.sha256(hashlib.sha256(hdr).digest()).digest(),"little")
            if is_constellation(hh|1):
                self._send({"id":self._nid(),"method":"mining.submit",
                            "params":[self.wallet,job["job_id"],en2,job["ntime"],struct.pack("<I",nonce).hex()]})
            nonce+=1
            el=time.time()-t0
            if el>=3:
                with self._hr_lock:self._hashrates[wid]=nonce/el/1000
                nonce=wid*1000000;t0=time.time()

    def _send(self,obj):
        try:self._sock.send((json.dumps(obj)+"\n").encode())
        except Exception as e:self._emit(f"Send error:{e}","err")

    def _nid(self):
        self._msg_id+=1;return self._msg_id

    def _agg(self):
        while self.running:
            time.sleep(3)
            with self._hr_lock:total=sum(self._hashrates.values())
            if self.on_hashrate:self.on_hashrate(total)

    def _emit(self,msg,level="info"):
        ts=datetime.now().strftime("%H:%M:%S")
        if self.on_status:self.on_status(f"[{ts}] {msg}",level)
