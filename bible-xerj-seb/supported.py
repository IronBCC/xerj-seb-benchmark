"""Same KJV chapter pairs, represented as chapter length measured in verses."""
import importlib.util,json,sqlite3,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("bench",P/"bench.py")
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def load():
    data,n=b.chapters(sys.argv[2]); byid={}
    for d in data:
        subject=f"{b.BOOKS[d['book']-1]} {d['chapter']}"
        summary=f"{subject} has length {d['count']} verses."
        byid[d["id"]]=dict(d,subject=subject,summary=summary,text=summary+"\n"+d["text"])
    return byid,n

def main():
    byid,n=load();cmd=sys.argv[1]
    if cmd=="prepare":
        t=time.perf_counter();db=sqlite3.connect(P/"supported-bm25.sqlite");db.execute("create virtual table chapters using fts5(id UNINDEXED,summary,text)")
        db.executemany("insert into chapters values (?,?,?)",[(v["id"],v["summary"],v["text"]) for v in byid.values()]);db.commit(); index_s=time.perf_counter()-t
        result=[]
        for orig in json.loads((P/"questions.json").read_text()):
            a=byid[orig["left"]];c=byid[orig["right"]];question=f"Is {a['subject']} longer than {c['subject']}?"
            match=" OR ".join("summary:"+chr(34)+d["subject"]+chr(34) for d in (a,c))
            t=time.perf_counter();rows=db.execute("select id,summary from chapters where chapters match ? order by bm25(chapters,0,5,1) limit 5",(match,)).fetchall();elapsed=time.perf_counter()-t
            result.append(dict(question=question,gold=orig["gold"],left=orig["left"],right=orig["right"],hits=[dict(id=x,summary=y) for x,y in rows],bm25_s=elapsed,state="Question: "+question+"\nEvidence:\n"+"\n".join(y for x,y in rows)))
        (P/"supported-questions.json").write_text(json.dumps(result,indent=2));print(json.dumps(dict(verses=n,chapters=len(byid),bm25_index_wall_s=index_s)))
    elif cmd=="index":
        docs=[];facts=[]
        for d in byid.values():
            v=str(d["count"]);start=d["summary"].index(v,d["summary"].index(" length "));docs.append(dict(doc_id=d["id"],version="v1",text=d["text"]));facts.append(dict(fact_id=d["id"],subject=d["subject"],subject_id=d["id"],relation="length",kind="number",value=v,unit="verses",doc_id=d["id"],version="v1",start=start,end=start+len(v),quote=v))
        t=time.perf_counter();response=b.post("/_facts/bible-length/_bulk",dict(documents=docs,facts=facts));print(json.dumps(dict(index_wall_s=time.perf_counter()-t,response=response)))
    elif cmd=="ask":
        for q in json.loads((P/"supported-questions.json").read_text()):
            t=time.perf_counter()
            try: response=b.post("/_facts/bible-length/_ask",{"question":q["question"]})
            except Exception as exc: response={"error":str(exc)}
            print(json.dumps(dict(question=q["question"],gold=q["gold"],elapsed_s=time.perf_counter()-t,response=response)),flush=True)
if __name__=="__main__":main()
