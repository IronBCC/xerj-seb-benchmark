"""Retrieve chapter-length summaries and compare their values without a model."""
import json,re,sqlite3,statistics,time
from pathlib import Path
P=Path(__file__).resolve().parent

def answer(question, hits):
    # shortcut: this parser accepts the benchmark question and summary templates only, use a general parser for open questions.
    match=re.fullmatch(r"Is (.+) longer than (.+)\?",question)
    if not match:
        return "unknown"
    needed=match.groups(); values={}
    for _,text in hits:
        fact=re.fullmatch(r"(.+) has length ([0-9]+) verses\.",text)
        if not fact or fact.group(1) not in needed:
            continue
        name,count=fact.group(1),int(fact.group(2))
        if name in values and values[name]!=count:
            return "unknown"
        values[name]=count
    if any(name not in values for name in needed):
        return "unknown"
    return "yes" if values[needed[0]]>values[needed[1]] else "no"

def main():
    assert answer("Is Job 19 longer than Job 32?",[("a","Job 19 has length 29 verses."),("b","Job 32 has length 22 verses.")])=="yes"
    assert answer("Is Job 19 longer than Job 32?",[("a","Job 19 has length 29 verses.")])=="unknown"
    assert answer("Is Job 19 longer than Job 32?",[("a","Job 19 has length 29 verses."),("a","Job 19 has length 20 verses."),("b","Job 32 has length 22 verses.")])=="unknown"
    db=sqlite3.connect(f"file:{P/'supported-bm25.sqlite'}?mode=ro",uri=True)
    qs=json.loads((P/"supported-questions.json").read_text()); rows=[]
    begin_wall=time.perf_counter_ns();begin_cpu=time.process_time_ns()
    for item in qs:
        start=time.perf_counter_ns();cpu=time.process_time_ns();question=item["question"]
        match=re.fullmatch(r"Is (.+) longer than (.+)\?",question)
        if match:
            query=" OR ".join("summary:"+chr(34)+name+chr(34) for name in match.groups())
            hits=db.execute("select id,summary from chapters where chapters match ? order by bm25(chapters,0,5,1) limit 5",(query,)).fetchall()
        else:
            hits=[]
        result=answer(question,hits)
        rows.append(dict(question=question,gold=item["gold"],answer=result,hits=hits,wall_ns=time.perf_counter_ns()-start,cpu_ns=time.process_time_ns()-cpu))
    cpu_ns=time.process_time_ns()-begin_cpu;wall_ns=time.perf_counter_ns()-begin_wall
    assert len(rows)==160 and all(r["question"]==q["question"] for r,q in zip(rows,qs))
    (P/"bm25-only-results.json").write_text(json.dumps(rows,indent=2))
    print(json.dumps(dict(n=len(rows),correct=sum(r["answer"]==r["gold"] for r in rows),wrong=sum(r["answer"] not in (r["gold"],"unknown") for r in rows),unknown=sum(r["answer"]=="unknown" for r in rows),median_wall_ms=statistics.median(r["wall_ns"] for r in rows)/1e6,total_wall_ms=wall_ns/1e6,total_cpu_ms=cpu_ns/1e6,cpu_cost_per_1000=cpu_ns/1e9/len(rows)*1000/3600*0.03625),indent=2))
if __name__=="__main__":main()
