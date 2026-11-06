"""Validate the supported chapter-length run against saved gold and usage."""
import collections,json,statistics
from pathlib import Path
p=Path(__file__).resolve().parent
q=json.loads((p/"supported-questions.json").read_text())
x=[json.loads(line) for line in (p/"supported-xerj.jsonl").read_text().splitlines()]
s=[]
for name,n in (("supported-seb-0.json",100),("supported-seb-1.json",60)):
    batch=json.loads((p/name).read_text())["results"]
    assert [r["index"] for r in batch]==list(range(n))
    assert all("answers" in r and "usage" in r for r in batch)
    s.extend(batch)
assert len(q)==len(x)==len(s)==160
assert all(a["question"]==b["question"] and a["gold"]==b["gold"] for a,b in zip(q,x))
assert all({a["left"],a["right"]}<={r["id"] for r in a["hits"]} for a in q)
assert sum(a["gold"]=="yes" for a in q)==80
states=collections.Counter(a["response"].get("final_status","ERROR") for a in x)
xc=sum(a["response"].get("final_status")=="ANSWER" and str(a["response"].get("final_answer")).lower()==a["gold"] for a in x)
xw=sum(a["response"].get("final_status")=="ANSWER" and str(a["response"].get("final_answer")).lower()!=a["gold"] for a in x)
sc=sum(a["answers"]["answer"]["choice"]==b["gold"] for a,b in zip(s,q))
su=sum(a["answers"]["answer"]["choice"]=="unknown" for a in s)
nanos=sum(a["usage"]["cost_nanos"] for a in s)
print(json.dumps({"n":len(q),"xerj":{"correct":xc,"wrong":xw,"statuses":states,"median_wall_ms":statistics.median(a["elapsed_s"] for a in x)*1000,"total_wall_s":sum(a["elapsed_s"] for a in x)},"seb":{"correct":sc,"wrong":len(s)-sc-su,"unknown":su,"input_tokens":sum(a["usage"]["input_tokens"] for a in s),"cost_nanos":nanos,"cost_per_1000":nanos/len(s)/1e6,"median_api_ms":statistics.median(a["latency_ms"] for a in s)},"bm25_median_ms":statistics.median(a["bm25_s"] for a in q)*1000},indent=2))
