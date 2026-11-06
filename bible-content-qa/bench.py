"""Exploratory Bible knowledge graph lookup; no test-question answers injected."""
import collections,hashlib,json,os,random,sqlite3,sys,time,urllib.request
from pathlib import Path
P=Path(__file__).resolve().parent
DATA=Path(os.environ.get("BENCH_DATA_DIR", P.parent / "data"))
FIELDS={"father":("father", "Who was {name}'s father?", "{name}'s father was {value}."),"mother":("mother", "Who was {name}'s mother?", "{name}'s mother was {value}."),"birth_place":("birth place", "Where was {name} born?", "{name} was born in {value}."),"death_place":("death place", "Where did {name} die?", "{name} died in {value}.")}

def source():
 people=json.loads((DATA/"people.json").read_text());places=json.loads((DATA/"places.json").read_text());counts=collections.Counter(v.get("name","").casefold() for v in people.values());facts=[]
 for ident,obj in sorted(people.items()):
  name=obj.get("name","");
  if not name or counts[name.casefold()]!=1:continue
  for field,(relation,template,sentence) in FIELDS.items():
   key=obj.get(field); pool=people if field in ("father","mother") else places
   if not isinstance(key,str) or key not in pool or not pool[key].get("name"):continue
   value=pool[key]["name"];text=sentence.format(name=name,value=value);start=text.rindex(value)
   facts.append(dict(id=f"{ident}-{field}",subject=name,subject_id=ident,field=field,relation=relation,value=value,text=text,start=start,end=start+len(value)))
 return facts

def post(path,obj):
 req=urllib.request.Request("http://127.0.0.1:19291"+path,json.dumps(obj).encode(),{"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)

def main():
 cmd=sys.argv[1];facts=source()
 if cmd=="prepare":
  db=sqlite3.connect(P/"facts.sqlite");db.execute("create virtual table facts using fts5(id UNINDEXED, subject, text)");t=time.perf_counter();db.executemany("insert into facts values (?,?,?)",[(f["id"],f["subject"],f["text"]) for f in facts]);db.commit();index=time.perf_counter()-t
  rng=random.Random(20261106);cases=[]
  for field,count in [("father",76),("mother",40),("birth_place",29),("death_place",15)]:
   candidates=[f for f in facts if f["field"]==field]; assert len(candidates)>=count
   for f in rng.sample(candidates,count):
    # Distractors are other values in the same relation, drawn without replacement.
    others=sorted({x["value"] for x in candidates if x["value"].casefold()!=f["value"].casefold()});options=rng.sample(others,3)+[f["value"]];rng.shuffle(options)
    question=FIELDS[field][1].format(name=f["subject"]);match="subject:"+chr(34)+f["subject"].replace(chr(34),chr(34)*2)+chr(34)
    start=time.perf_counter();hits=db.execute("select id,text from facts where facts match ? order by bm25(facts,0,3,1) limit 5",(match,)).fetchall();duration=time.perf_counter()-start
    labels="ABCD"; option_lines="\n".join(f"{labels[i]}: {v}" for i,v in enumerate(options))
    cases.append(dict(question=question,field=field,gold=f["value"],correct_option=labels[options.index(f["value"])],options=options,hits=hits,bm25_s=duration,state="Question: "+question+"\nOptions:\n"+option_lines+"\nEvidence:\n"+"\n".join(t for _,t in hits)))
  rng.shuffle(cases);assert len(cases)==160
  (P/"questions.json").write_text(json.dumps(cases,indent=2));print(json.dumps(dict(facts=len(facts),bm25_index_wall_s=index,questions=len(cases))))
 elif cmd=="index":
  docs=[];out=[]
  for f in facts:
   docs.append(dict(doc_id=f["id"],version="v1",text=f["text"]));out.append(dict(fact_id=f["id"],subject=f["subject"],subject_id=f["subject_id"],relation=f["relation"],kind="text",value=f["value"],doc_id=f["id"],version="v1",start=f["start"],end=f["end"],quote=f["value"]))
  t=time.perf_counter();result=post("/_facts/kg/_bulk",dict(documents=docs,facts=out));print(json.dumps(dict(index_wall_s=time.perf_counter()-t,result=result)))
 elif cmd=="ask":
  for c in json.loads((P/"questions.json").read_text()):
   t=time.perf_counter()
   try:response=post("/_facts/kg/_ask",{"question":c["question"]})
   except Exception as e:response={"error":str(e)}
   print(json.dumps(dict(question=c["question"],gold=c["gold"],elapsed_s=time.perf_counter()-t,response=response)),flush=True)
if __name__=="__main__":main()
