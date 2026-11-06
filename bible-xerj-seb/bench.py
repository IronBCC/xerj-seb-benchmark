"""Frozen KJV chapter-verse-count comparison, XERJ versus SQLite BM25 + Seb."""
import hashlib, json, random, sqlite3, sys, time, urllib.request
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
BOOKS="Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|1 Samuel|2 Samuel|1 Kings|2 Kings|1 Chronicles|2 Chronicles|Ezra|Nehemiah|Esther|Job|Psalms|Proverbs|Ecclesiastes|Song of Solomon|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|1 Corinthians|2 Corinthians|Galatians|Ephesians|Philippians|Colossians|1 Thessalonians|2 Thessalonians|1 Timothy|2 Timothy|Titus|Philemon|Hebrews|James|1 Peter|2 Peter|1 John|2 John|3 John|Jude|Revelation".split("|")

def chapters(path):
    db=sqlite3.connect(f"file:{path}?mode=ro",uri=True)
    rows=db.execute("select book_id,chapter,number,text from verses order by book_id,chapter,number").fetchall()
    grouped=defaultdict(list)
    for bid,chapter,num,txt in rows: grouped[(bid,chapter)].append((num,txt))
    out=[]
    for (bid,ch),verses in grouped.items():
        name=f"{BOOKS[bid-1]} chapter {ch}"
        count=len(verses); lead=f"{name} has {count} verses."
        out.append(dict(id=f"b{bid}c{ch}", book=bid,chapter=ch,subject=name,count=count,summary=lead,text=lead+"\n"+"\n".join(f"{num}. {txt}" for num,txt in verses)))
    return out,len(rows)

def questions(data):
    bybook=defaultdict(list)
    for row in data: bybook[row["book"]].append(row)
    pairs=[(a,b) for book in bybook.values() for a in book for b in book if a["chapter"]<b["chapter"] and a["count"]!=b["count"]]
    random.Random(20261106).shuffle(pairs)
    out=[]
    for a,b in pairs[:80]:
        for x,y in ((a,b),(b,a)):
            out.append(dict(question="Does {} have more verses than {}?".format(x["subject"],y["subject"]),gold="yes" if x["count"]>y["count"] else "no",left=x["id"],right=y["id"],book=x["book"]))
    assert len(out)==160 and sum(q["gold"]=="yes" for q in out)==80
    return out

def post(path, obj):
    req=urllib.request.Request("http://127.0.0.1:19291"+path,json.dumps(obj).encode(),{"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=120) as r: return json.load(r)

def main():
    data,n=chapters(sys.argv[2]); cmd=sys.argv[1]
    if cmd=="prepare":
        t=time.perf_counter(); db=sqlite3.connect(HERE/"bm25.sqlite"); db.execute("create virtual table chapters using fts5(id UNINDEXED, summary, text)")
        db.executemany("insert into chapters values (?,?,?)",[(d["id"],d["summary"],d["text"]) for d in data]); db.commit()
        print(json.dumps({"bm25_index_s":time.perf_counter()-t,"verses":n,"chapters":len(data)}))
        qs=questions(data)
        for q in qs:
            subjects=q["question"].removeprefix("Does ").removesuffix("?").split(" have more verses than "); match=" OR ".join("summary:"+chr(34)+name+chr(34) for name in subjects)
            t=time.perf_counter(); rows=db.execute("select id,summary from chapters where chapters match ? order by bm25(chapters,0,5,1) limit 5",(match,)).fetchall(); q["bm25_s"]=time.perf_counter()-t
            q["hits"]=[{"id":x,"summary":y} for x,y in rows]; q["state"]="Question: "+q["question"]+"\nEvidence:\n"+"\n".join(y for x,y in rows)
        (HERE/"questions.json").write_text(json.dumps(qs,indent=2))
    elif cmd=="index-xerj":
        docs=[]; facts=[]
        for d in data:
            docs.append(dict(doc_id=d["id"],version="v1",text=d["text"]))
            v=str(d["count"]); start=d["summary"].index(v,d["summary"].index(" has ")+5)
            facts.append(dict(fact_id=d["id"],subject=d["subject"],subject_id=d["id"],relation="verse count",kind="number",value=v,unit="verses",doc_id=d["id"],version="v1",start=start,end=start+len(v),quote=v))
        t=time.perf_counter(); result=post("/_facts/bible/_bulk",dict(documents=docs,facts=facts)); print(json.dumps({"index_wall_s":time.perf_counter()-t,"result":result}))
    elif cmd=="ask-xerj":
        for q in json.loads((HERE/"questions.json").read_text()):
            t=time.perf_counter()
            try: result=post("/_facts/bible/_ask",{"question":q["question"]})
            except Exception as e: result={"error":str(e)}
            print(json.dumps({"question":q["question"],"gold":q["gold"],"elapsed_s":time.perf_counter()-t,"response":result}),flush=True)

if __name__=="__main__": main()
