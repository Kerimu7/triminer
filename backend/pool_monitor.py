import requests,threading,time
from datetime import datetime

class PoolMonitor:
    def __init__(self,duino_user="",nimiq_wallet="",riecoin_wallet="",on_update=None):
        self.duino_user=duino_user
        self.nimiq_wallet=nimiq_wallet
        self.riecoin_wallet=riecoin_wallet
        self.on_update=on_update
        self.running=False

    def start(self):
        self.running=True
        threading.Thread(target=self._loop,daemon=True).start()

    def stop(self):
        self.running=False

    def _loop(self):
        while self.running:
            if self.duino_user:self._duino()
            if self.nimiq_wallet:self._nimiq()
            if self.riecoin_wallet:self._riecoin()
            time.sleep(30)

    def _duino(self):
        try:
            r=requests.get(f"https://server.duinocoin.com/v4/users/{self.duino_user}",timeout=10).json()
            ps=requests.get("https://server.duinocoin.com/v4/statistics",timeout=10).json()
            bal=r.get("result",{}).get("balance",{})
            pool=ps.get("result",{})
            data={"balance":round(float(bal.get("balance",0)),6),
                  "hashrate":bal.get("hashrate","0"),
                  "workers":bal.get("workers",0),
                  "pool_hashrate":pool.get("Pool hashrate","N/A"),
                  "active_miners":pool.get("Active miners","N/A"),
                  "difficulty":pool.get("Current difficulty","N/A"),
                  "price_usd":pool.get("Duco price","N/A"),
                  "blocks_found":pool.get("Blocks found","N/A"),
                  "last_updated":datetime.now().strftime("%H:%M:%S")}
            if self.on_update:self.on_update("duino",data)
        except Exception as e:
            if self.on_update:self.on_update("duino",{"error":str(e)})

    def _nimiq(self):
        try:
            md=requests.get(f"https://nimpool.io/api/miner/{self.nimiq_wallet}",timeout=10).json()
            ps=requests.get("https://nimpool.io/api/pool",timeout=10).json()
            data={"balance":md.get("balance",0),
                  "hashrate":md.get("hashrate",0),
                  "shares_valid":md.get("validShares",0),
                  "shares_invalid":md.get("invalidShares",0),
                  "last_share":md.get("lastShare","N/A"),
                  "pool_hashrate":ps.get("hashrate","N/A"),
                  "pool_miners":ps.get("minersTotal","N/A"),
                  "pool_fee":ps.get("poolFee","N/A"),
                  "nim_price_usd":ps.get("price","N/A"),
                  "last_updated":datetime.now().strftime("%H:%M:%S")}
            if self.on_update:self.on_update("nimiq",data)
        except Exception as e:
            if self.on_update:self.on_update("nimiq",{"error":str(e)})

    def _riecoin(self):
        try:
            md=requests.get(f"https://ric.riesenprime.de/api/miner/{self.riecoin_wallet}",timeout=10).json()
            ps=requests.get("https://ric.riesenprime.de/api/pool",timeout=10).json()
            data={"balance":md.get("balance",0),
                  "hashrate":md.get("hashrate",0),
                  "shares_valid":md.get("validShares",0),
                  "shares_stale":md.get("staleShares",0),
                  "tuple_type":md.get("tupleType","6-tuple"),
                  "pool_hashrate":ps.get("hashrate","N/A"),
                  "pool_miners":ps.get("miners","N/A"),
                  "pool_fee":ps.get("fee","N/A"),
                  "ric_price_usd":ps.get("price","N/A"),
                  "last_block":ps.get("lastBlock","N/A"),
                  "last_updated":datetime.now().strftime("%H:%M:%S")}
            if self.on_update:self.on_update("riecoin",data)
        except Exception as e:
            if self.on_update:self.on_update("riecoin",{"error":str(e)})
