"""Raw KJV passage retrieval against BibleQA reference verses."""
import collections,json,os,random,re,resource,sqlite3,sys,time,unicodedata,urllib.request
from pathlib import Path
P=Path(__file__).resolve().parent
DATA=Path(os.environ.get("BENCH_DATA_DIR", P.parent / "data"))
STOP=set("a an and are as at be been but by did do does for from had has have he her him his how i in into is it its of on or she that the their them then there these they this to was were what when where which who whom whose why with would you".split())
def norm(s):return " ".join(re.findall(r"[a-z0-9]+",unicodedata.normalize("NFKD",s).lower()))
def request(path,data=None,method=None,ctype="application/json"):
 data=None if data is None else (data if isinstance(data,bytes) else json.dumps(data).encode());req=urllib.request.Request("http://127.0.0.1:19291"+path,data,{"Content-Type":ctype},method=method)
 with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)
def main():
 cmd=sys.argv[1];source=sqlite3.connect(f"file:{DATA / 'kjv.sqlite'}?mode=ro",uri=True);verses=source.execute("select id,book_id,chapter,number,text from verses order by id").fetchall()
 if cmd=="prepare":
  t=time.perf_counter();cpu=time.process_time();db=sqlite3.connect(P/"bible.sqlite");db.execute("create virtual table verses using fts5(id UNINDEXED, text)");db.executemany("insert into verses values (?,?)",[(r[0],r[4]) for r in verses]);db.commit();index_wall=time.perf_counter()-t;index_cpu=time.process_time()-cpu
  lookup=collections.defaultdict(list)
  for id,_,_,_,text in verses:lookup[norm(text)].append(id)
  candidates=[]
  for a in json.loads((DATA/"bibleqa.json").read_text()):
   question=a["question"][0];reference=a["answers"][0][a["labels"].index(1)];matches=lookup.get(norm(reference),[])
   if len(matches)!=1 or chr(34) in question or re.search(r"\b\d+\s*:\s*\d+",question):continue
   terms=list(dict.fromkeys(w for w in norm(question).split() if w not in STOP and len(w)>1))
   if terms:candidates.append(dict(question=question,gold_id=matches[0],query_terms=terms))
  random.Random(20261106).shuffle(candidates); cases=candidates[:160];assert len(cases)==160
  for c in cases:
   query=" OR ".join(chr(34)+x+chr(34) for x in c["query_terms"]);t=time.perf_counter();hits=db.execute("select id,text from verses where verses match ? order by bm25(verses) limit 5",(query,)).fetchall();c["bm25_s"]=time.perf_counter()-t;c["hits"]=[dict(id=int(i),text=text) for i,text in hits]
  (P/"questions.json").write_text(json.dumps(cases,indent=2));print(json.dumps(dict(corpus_verses=len(verses),eligible_questions=len(candidates),selected=160,index_wall_s=index_wall,index_cpu_s=index_cpu)))
 elif cmd=="xerj-index":
  request("/rawbible",{"mappings":{"properties":{"text":{"type":"text"}}}},"PUT"); t=time.perf_counter()
  for i in range(0,len(verses),500):
   lines=[]
   for id,book,ch,num,text in verses[i:i+500]:lines.extend([json.dumps({"index":{"_index":"rawbible","_id":str(id)}}),json.dumps(dict(text=text,book_id=book,chapter=ch,number=num))])
   response=request("/_bulk",("\n".join(lines)+"\n").encode(),ctype="application/x-ndjson")
   if response.get("errors"):raise RuntimeError(str(response)[:1000])
  request("/rawbible/_refresh",{},"POST");print(json.dumps(dict(verses=len(verses),index_wall_s=time.perf_counter()-t)))
 elif cmd=="facts-raw-index":
  t=time.perf_counter()
  for i in range(0,len(verses),1000):
   docs=[dict(doc_id=f"v{id}",version="v1",text=text) for id,book,ch,num,text in verses[i:i+1000]]
   result=request("/_facts/rawonly/_bulk",dict(documents=docs))
  print(json.dumps(dict(documents=len(verses),index_wall_s=time.perf_counter()-t,commit=result.get("committed"))))
 elif cmd=="facts-raw-ask":
  for c in json.loads((P/"questions.json").read_text()):
   t=time.perf_counter();r=request("/_facts/rawonly/_ask",dict(question=c["question"]));print(json.dumps(dict(question=c["question"],elapsed_s=time.perf_counter()-t,response=r)),flush=True)
 elif cmd=="xerj-ask":
  for c in json.loads((P/"questions.json").read_text()):
   t=time.perf_counter();r=request("/rawbible/_search",{"size":5,"_source":["text"],"query":{"match":{"text":{"query":" ".join(c["query_terms"]),"operator":"or"}}}});hits=[dict(id=int(x["_id"]),text=x["_source"]["text"]) for x in r["hits"]["hits"]];print(json.dumps(dict(question=c["question"],gold_id=c["gold_id"],hits=hits,elapsed_s=time.perf_counter()-t)),flush=True)
if __name__=="__main__":main()
