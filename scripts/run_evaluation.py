from pathlib import Path
import json, statistics, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import create_app
from app.db import get_db

app=create_app({"TESTING":True,"DATABASE":str(ROOT/"evaluation.db"),"RATE_LIMIT_MAX":5})
with app.app_context():
    db=get_db();db.execute("UPDATE cards SET active=1");db.execute("DELETE FROM failed_attempts");db.commit()

def avg_ms(client,path,method="get",data=None,n=20):
    vals=[]
    for _ in range(n):
        t=time.perf_counter()
        client.post(path,data=data or {}) if method=="post" else client.get(path)
        vals.append((time.perf_counter()-t)*1000)
    return round(statistics.mean(vals),3)

with app.test_client() as c:
    baseline=c.get("/baseline/demo-card")
    public=c.get("/tap/demo-token-001")
    wrong=c.post("/tap/demo-token-001",data={"pin":"0000"})
    correct=c.post("/tap/demo-token-001",data={"pin":"2468"})
    with app.app_context():
        db=get_db();db.execute("UPDATE cards SET active=0");db.commit()
    revoked=c.get("/tap/demo-token-001")
    with app.app_context():
        db=get_db();db.execute("UPDATE cards SET active=1");db.execute("DELETE FROM failed_attempts");db.commit()
    statuses=[c.post("/tap/demo-token-001",data={"pin":"9999"}).status_code for _ in range(6)]
    results={
      "authorized_access_success": correct.status_code==200 and b"Synthetic Contact" in correct.data,
      "unauthorized_protected_access_blocked": b"Synthetic Contact" not in wrong.data,
      "revoked_card_blocked": revoked.status_code==403,
      "rate_limit_triggered": 429 in statuses,
      "baseline_exposes_protected_data": b"Synthetic Contact" in baseline.data,
      "defended_public_hides_protected_data": b"Synthetic Contact" not in public.data,
      "average_latency_ms":{
        "baseline_get":avg_ms(c,"/baseline/demo-card"),
        "defended_public_get":avg_ms(c,"/tap/demo-token-001"),
        "authorized_post":avg_ms(c,"/tap/demo-token-001","post",{"pin":"2468"})
      }
    }
out=ROOT/"evidence/test-results/evaluation_results.json"
out.write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
