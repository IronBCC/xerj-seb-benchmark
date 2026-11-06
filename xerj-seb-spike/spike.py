"""Small synthetic retrieval comparison; not the XERJ article benchmark."""
import json, sqlite3, sys, time, urllib.request

PEOPLE = [("Ana Bel", 170), ("Ben Cor", 182), ("Cora Lin", 161), ("Dara Sol", 175), ("Evan Fox", 188), ("Faye Kim", 164), ("Gina Ray", 180), ("Hugo Tan", 172), ("Iris Vale", 167), ("Jules Wen", 185), ("Kira Yun", 178), ("Luca Zee", 160)]
PAIRS = [(0,1),(1,0),(2,3),(3,2),(4,5),(5,4),(6,7),(7,6),(8,9),(9,8),(10,11),(11,10),(0,12),(12,1)]
NAMES = PEOPLE + [("Mira Oak", None)]

def post(path, body):
    req = urllib.request.Request("http://127.0.0.1:19291" + path, json.dumps(body).encode(), {"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)

def build():
    db=sqlite3.connect(":memory:")
    db.execute("create virtual table docs using fts5(text)")
    documents=[]; facts=[]
    for i,(name,height) in enumerate(PEOPLE):
        sentence=f"{name} is {height} cm tall."
        db.execute("insert into docs(text) values (?)", (sentence,))
        value=str(height); start=sentence.index(value)
        documents.append(dict(doc_id=f"d{i}", version="v1", text=sentence))
        facts.append(dict(fact_id=f"f{i}",subject=name,subject_id=f"p{i}",relation="height",kind="number",value=value,unit="cm",doc_id=f"d{i}",version="v1",start=start,end=start+len(value),quote=value))
    cases=[]
    for a,b in PAIRS:
        na,va=NAMES[a]; nb,vb=NAMES[b]
        question=f"Is {na} taller than {nb}?"
        query=" OR ".join("\""+x+"\"" for x in (na.split()+nb.split()+["height","tall"]))
        docs=[r[0] for r in db.execute("select text from docs where docs match ? order by bm25(docs) limit 5",(query,))]
        gold="unknown" if va is None or vb is None else ("yes" if va>vb else "no")
        cases.append(dict(question=question,gold=gold,retrieved=docs,state="Question: "+question+"\nEvidence:\n"+"\n".join(docs)))
    return documents,facts,cases

if __name__ == "__main__":
    documents,facts,cases=build()
    assert cases[0]["gold"] == "no" and cases[1]["gold"] == "yes" and cases[-1]["gold"] == "unknown"
    assert all(len(c["retrieved"]) <= 5 for c in cases)
    if sys.argv[1] == "prepare":
        print(json.dumps(cases,indent=2))
    elif sys.argv[1] == "xerj":
        print(json.dumps({"commit":post("/_facts/spike/_bulk",dict(documents=documents,facts=facts))}))
        for c in cases:
            start=time.perf_counter(); result=post("/_facts/spike/_ask", {"question":c["question"]}); elapsed=time.perf_counter()-start
            print(json.dumps({"question":c["question"],"gold":c["gold"],"elapsed_s":elapsed,"response":result}),flush=True)
