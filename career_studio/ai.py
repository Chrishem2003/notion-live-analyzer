import os,urllib.request,json
def configured():return all(os.getenv(k) for k in ("CAREER_AI_ENDPOINT","CAREER_AI_MODEL","CAREER_AI_API_KEY"))
def ask(system,user):
 if not configured():raise RuntimeError("AI is not configured.")
 payload={"model":os.environ["CAREER_AI_MODEL"],"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":0.3}
 req=urllib.request.Request(os.environ["CAREER_AI_ENDPOINT"],data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+os.environ["CAREER_AI_API_KEY"],"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=60) as r:data=json.loads(r.read().decode())
 return data["choices"][0]["message"]["content"]
