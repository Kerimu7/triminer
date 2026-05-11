import socket,json,threading,time,requests
from datetime import datetime
try:
    from argon2.low_level import hash_secret_raw,Type
    ARGON2=True
except:ARGON2=False

POOL_HOST="eu.nimpool.io"
POOL_PORT=8444
MINER_VER="TriMiner/1.0"

class NimiqMiner:
    def __init__(self,wallet_address,threads=2,pool_host=POOL_HOST,pool_port=POOL_PORT,on_status=None,on_share=None,on_hashrate=None):
        self.wallet=wallet_address;self.threads=threads
        self.pool_host=pool_host;self.pool_port=pool_port
        self.on_status=on_status;self.on_share=on_share;self.on_hashrate=on_hashrate
        self.running=False;self.accepted=0;self.rejected=0
        self._job=None;self._job_lock=threading.Lock()
        self._sock=None;self._msg_id=1
        self._hashrates={};self._hr_lock=threading.Lock()

    def start(self):
        if not ARGON2:
            self._emit("argon2-cffi not installed","err");return
        self.running=True
        threading.Thread(target=self._net,daemon=True).start()
        threading.Thread(target=self._agg,daemon=True).start()
        self._emit("Connecting to Nimiq pool...","info")

    def stop(self):
        self.running=False
        if self._sock:
            try:self._sock.close()
            except:pass
        self._emit("Miner stopped.","warn")

    def get_stats(self):
        try:return requests.get(f"https://nimpool.io/api/miner/{self.wallet}",timeout=8).json()
        except:return{}

    def get_pool_stats(self):
        try:return requests.get("https://nimpool.io/api/pool",timeout=8).json()
        except:return{}

    def _net(self):
        while self.running:
            try:
                self._sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                self._sock.settimeout(60)
                self._sock.connect((self.pool_host,self.pool_port))
                self._emit(f"Connected to {self.pool_host}","info")
                self._send({"method":"mining.subscribe","params":[MINER_VER],"id":self._nid()})
                self._send({"method":"mining.authorize","params":[self.wallet,"x"],"id":self._nid()})
                buf=""
                while self.running:
                    data=self._sock.recv(4096).decode(errors="ignore")
                    if not data:break
                    buf+=data
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
                self._job={"job_id":p[0],"prev_hash":p[1],"body":p[2],
                           "nonce":int(p[3],16) if len(p)>3 else 0,
                           "target":p[4] if len(p)>4 else "f"*64}
            self._emit(f"New job {p[0][:10]}...","info")
            for i in range(self.threads):
                threading.Thread(target=self._mine,args=(i,),daemon=True).start()
        elif"result"in msg:
            if msg.get("result") is True:
                self.accepted+=1
                self._emit(f"Share accepted [{self.accepted}]","ok")
            elif msg.get("result") is False:
                self.rejected+=1
                self._emit("Share rejected","warn")
            if self.on_share:self.on_share(self.accepted,self.rejected)

    def _mine(self,wid):
        import struct
        with self._job_lock:job=dict(self._job) if self._job else None
        if not job:return
        nonce=job["nonce"]+wid*100000
        t0=time.time();hashes=0
        tb=bytes.fromhex(job["target"].ljust(64,"0"))[:8]
        while self.running:
            with self._job_lock:
                if self._job and self._job["job_id"]!=job["job_id"]:break
            bh=bytes.fromhex(job["prev_hash"])+bytes.fromhex(job["body"][:64].ljust(64,"0"))+struct.pack("<I",nonce)
            d=hash_secret_raw(secret=bh,salt=bh[:16],time_cost=1,memory_cost=512,parallelism=1,hash_len=32,type=Type.D)
            hashes+=1
            el=time.time()-t0
            if el>=2:
                with self._hr_lock:self._hashrates[wid]=hashes/el
                hashes=0;t0=time.time()
            if d[:8]<=tb:
                self._send({"method":"mining.submit","params":[self.wallet,job["job_id"],hex(nonce)],"id":self._nid()})
                break
            nonce+=1

    def _send(self,obj):
        try:self._sock.send((json.dumps(obj)+"\n").encode())
        except Exception as e:self._emit(f"Send error:{e}","err")

    def _nid(self):
        self._msg_id+=1;return self._msg_id

    def _agg(self):
        while self.running:
            time.sleep(2)
            with self._hr_lock:total=sum(self._hashrates.values())
            if self.on_hashrate:self.on_hashrate(total)

    def _emit(self,msg,level="info"):
        ts=datetime.now().strftime("%H:%M:%S")
        if self.on_status:self.on_status(f"[{ts}] {msg}",level)
