import collections,json,statistics,unicodedata
from pathlib import Path
p=Path(__file__).resolve().parent
q=json.loads((p/"questions.json").read_text());x=[json.loads(l) for l in (p/"xerj-results.jsonl").read_text().splitlines()];s=[]
for name,n in (("seb-0.json",100),("seb-1.json",60)):
 batch=json.loads((p/name).read_text())["results"];assert [a["index"] for a in batch]==list(range(n));assert all("usage" in a and "answers" in a for a in batch);s.extend(batch)
assert len(q)==len(x)==len(s)==160
assert all(a["question"]==b["question"] and a["gold"]==b["gold"] for a,b in zip(q,x))
assert all(a["options"]["ABCD".index(a["correct_option"])]==a["gold"] for a in q)
n=lambda z:unicodedata.normalize("NFKC",str(z)).strip().casefold().rstrip(".")
states=collections.Counter(a["response"].get("final_status","ERROR") for a in x)
xc=sum(a["response"].get("final_status")=="ANSWER" and n(a["response"].get("final_answer"))==n(a["gold"]) for a in x)
xw=sum(a["response"].get("final_status")=="ANSWER" and n(a["response"].get("final_answer"))!=n(a["gold"]) for a in x)
sc=sum(a["answers"]["answer"]["choice"]==b["correct_option"] for a,b in zip(s,q));su=sum(a["answers"]["answer"]["choice"]=="unknown" for a in s);nanos=sum(a["usage"]["cost_nanos"] for a in s)
print(json.dumps({"n":160,"families":collections.Counter(a["field"] for a in q),"xerj":{"correct":xc,"wrong":xw,"statuses":states,"median_wall_ms":statistics.median(a["elapsed_s"] for a in x)*1000},"seb":{"correct":sc,"wrong":160-sc-su,"unknown":su,"input_tokens":sum(a["usage"]["input_tokens"] for a in s),"cost_nanos":nanos,"cost_per_1000":nanos/160/1e6,"median_api_ms":statistics.median(a["latency_ms"] for a in s)},"bm25_median_ms":statistics.median(a["bm25_s"] for a in q)*1000},indent=2))
