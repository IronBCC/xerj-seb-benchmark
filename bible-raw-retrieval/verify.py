"""Validate raw retrieval, frozen ordering, reranking, errors, and metering."""
import json,statistics
from pathlib import Path
P=Path(__file__).resolve().parent
q=json.loads((P/"questions.json").read_text());x=[json.loads(l) for l in (P/"xerj-results.jsonl").read_text().splitlines()];f=[json.loads(l) for l in (P/"facts-results.jsonl").read_text().splitlines()];s=[]
for i in range(8):
 batch=json.loads((P/f"seb-{i}.json").read_text())["results"]
 assert [r["index"] for r in batch]==list(range(len(batch)))
 assert all("answers" in r and "usage" in r for r in batch)
 s+=batch
assert len(q)==len(x)==len(f)==160 and sum(len(a["hits"]) for a in q)==len(s)==800
assert all(a["question"]==b["question"] and a["gold_id"]==b["gold_id"] for a,b in zip(q,x))
assert all(a["question"]==b["question"] for a,b in zip(q,f))
reranked=[];offset=0
for a in q:
 scores=[s[offset+j]["answers"]["relevance"]["noul"] for j in range(len(a["hits"]))];offset+=len(scores)
 order=sorted(range(len(scores)),key=lambda j:-scores[j]);reranked.append([a["hits"][j]["id"] for j in order])
def recall(rows,k):return sum(any(h["id"]==a["gold_id"] for h in a["hits"][:k]) for a in rows)
nanos=sum(a["usage"]["cost_nanos"] for a in s)
print(json.dumps({"n":160,"sqlite_bm25":{"recall_at_1":recall(q,1),"recall_at_5":recall(q,5),"median_ms":statistics.median(a["bm25_s"] for a in q)*1000},"xerj_raw_search":{"recall_at_1":recall(x,1),"recall_at_5":recall(x,5),"median_ms":statistics.median(a["elapsed_s"] for a in x)*1000},"bm25_seb_rerank":{"recall_at_1":sum(ids[0]==a["gold_id"] for ids,a in zip(reranked,q)),"recall_at_5":sum(a["gold_id"] in ids for ids,a in zip(reranked,q)),"calls":len(s),"tokens":sum(a["usage"]["input_tokens"] for a in s),"cost_nanos":nanos,"cost_per_1000_questions":nanos/160/1e6,"median_per_item_api_ms":statistics.median(a["latency_ms"] for a in s)},"xerj_query1_without_extraction":{"unknown":sum(a["response"].get("final_status")=="UNKNOWN" for a in f)}},indent=2))
