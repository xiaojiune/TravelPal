"""CA vs VNS — suggest 1次 + deep 1次（n_days=3）"""
import json
import sys
import urllib.request

sys.path.insert(0, '/home/changzi/TravelPal')

BASE = "http://localhost:8000/api"
def api(path, data):
    req = urllib.request.Request(f"{BASE}{path}", data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())

names = [
    "悦朵酒店·精选 (广州北京路步行街西门口地铁站店)",
    "广州市白云山风景名胜区", "越秀公园", "陈家祠广场", "沙面岛",
    "广州长隆旅游度假区", "广州塔", "中山纪念堂", "岭南印象园",
]
poi = api("/poi-lookup", {"city": "广州", "names": names})
its = poi["items"]

TW = {1:(0,1440),2:(0,1440),3:(510,1050),4:(0,1440),5:(0,1440),6:(570,1350),7:(480,1020),8:(570,1290)}
spots = [
    {"name":its[i]["name"],"lon":its[i]["lon"],"lat":its[i]["lat"],
     "tw_start":TW[i][0],"tw_end":TW[i][1],"stay":stay,
     "expected_arrival": exp}
    for i,(stay,exp) in enumerate(
        [(180,480),(120,960),(150,None),(60,None),
         (300,480),(60,None),(120,None),(120,None)], 1,
    )
]

req = {
    "city": "广州",
    "hotel_name": its[0]["name"],
    "hotel_lon": its[0]["lon"], "hotel_lat": its[0]["lat"],
    "hotel_tw_start": 0, "hotel_tw_end": 1440,
    "day_start": 360,
    "spots": spots,
    "penalty_weight": 100, "early_wait_weight": 0.1, "late_return_weight": 50,
}

print("=== Suggest (CA, 自动天数) ===")
sug = api("/suggest", {**req, "n_days": None, "mode": "fast"})
print(f"总建议数: {len(sug.get('suggestions',[]))}")
for s in sug.get("suggestions", []):
    if s["n_days"] == 3:
        print(f"  n_days=3  {s['method']:>30s}  cost={s['cost']:>10.1f}")

cm, dm = sug.get("cost_matrix"), sug.get("dist_matrix")
print(f"\n复用 matrix: {len(cm)}x{len(cm[0]) if cm else 0}")

print("\n=== Plan fast (CA, n_days=3) ===")
r = api("/plan", {**req, "n_days": 3, "mode": "fast", "cost_matrix": cm, "dist_matrix": dm})
s = r.get("solution", r)
ca_cost, ca_dist, ca_wait, ca_late = s["total_cost"], s["total_dist"], s["wait"], s["late"]
print(f"CA:   cost={ca_cost:>10.1f}  dist={ca_dist:>8.1f}  wait={ca_wait:>6.1f}  late={ca_late:>6.1f}")

print("\n=== Plan deep (VNS, n_days=3) ===")
r = api("/plan", {**req, "n_days": 3, "mode": "deep", "cost_matrix": cm, "dist_matrix": dm})
s = r.get("solution", r)
vns_cost, vns_dist, vns_wait, vns_late = s["total_cost"], s["total_dist"], s["wait"], s["late"]
print(f"VNS:  cost={vns_cost:>10.1f}  dist={vns_dist:>8.1f}  wait={vns_wait:>6.1f}  late={vns_late:>6.1f}")
