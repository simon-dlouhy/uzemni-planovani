# app/main.py
import os, uuid, concurrent.futures
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from dotenv import load_dotenv

from langchain_agent import run_langchain_agent

load_dotenv()
os.environ["DISABLE_EMAIL"] = "1"

GOOGLE_CRED_JSON = os.getenv("GOOGLE_CRED_JSON")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "google_credentials.json")
if GOOGLE_CRED_JSON and not os.path.exists(GOOGLE_CREDENTIALS_PATH):
    with open(GOOGLE_CREDENTIALS_PATH, "w", encoding="utf-8") as f:
        f.write(GOOGLE_CRED_JSON)

app = FastAPI()
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
JOBS: dict[str, dict] = {}

HTML_FORM = """
<!doctype html><meta charset="utf-8"><title>Analýza územního plánu</title>
<meta name="viewport" content="width=device-width,initial-scale=1" />
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:680px;margin:40px auto;padding:0 16px}
.card{border:1px solid #e5e7eb;border-radius:12px;padding:20px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
label{display:block;margin:14px 0 6px;font-weight:600}
input,textarea,button{width:100%;padding:12px;border:1px solid #e5e7eb;border-radius:10px;font-size:16px}
button{cursor:pointer;background:#111;color:#fff;border-color:#111;margin-top:16px}
.hint{color:#6b7280;font-size:14px;margin-top:8px}
</style>
<div class="card">
  <h1>🏙️ Územní analýza</h1>
  <form method="post" action="/jobs">
    <label>Obec</label>
    <input name="city" placeholder="Např. Příbram" required />
    <label>Úkol (volitelný)</label>
    <textarea name="task" rows="3" placeholder="Např. Proveď kompletní analýzu a veškeré kroky pro obec Dubno."></textarea>
    <button>Spustit</button>
    <p class="hint">Po odeslání budete přesměrován/a na stránku se stavem a odkazem ke stažení ZIP.</p>
  </form>
</div>
"""

@app.get("/", response_class=HTMLResponse)
def form():
    return HTML_FORM

def _do_work(job_id: str, city: str, task: str):
    try:
        JOBS[job_id] = {"state": "RUNNING"}
        instruction = (
            f"Proveď kompletní pipeline pro obec '{city}'. "
            f"Po dokončení ZASTAV se u kroku e-mailu (je vypnutý). "
            f"Postup: stáhni PDF, analyzuj 5 problémů a 5 trendů, "
            f"vytvoř shrnutí (.txt), aktualizuj BigQuery, zazipuj výstupy. "
            + (f"Doplňující požadavky: {task}" if task else "")
        )
        run_langchain_agent(instruction)

        JOBS[job_id] = {
            "state": "SUCCESS",
            "data": {"city": city, "download_url": f"/download/{city}"},
        }
    except Exception as e:
        JOBS[job_id] = {"state": "ERROR", "error": str(e)}

@app.post("/jobs")
def create_job(city: str = Form(...), task: str = Form("")):
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"state": "PENDING"}
    executor.submit(_do_work, job_id, city.strip(), task.strip())
    return RedirectResponse(url=f"/status/{job_id}", status_code=303)

@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    info = JOBS.get(job_id)
    if not info:
        return JSONResponse({"error": "Unknown job_id"}, status_code=404)
    if info.get("state") == "SUCCESS":
        city = info["data"]["city"]
        dl = info["data"]["download_url"]
        info["download_html"] = f'<a class="button" href="{dl}">⬇️ Stáhnout ZIP ({city})</a>'
    return info

@app.get("/status/{job_id}", response_class=HTMLResponse)
def status_page(job_id: str):
    return f"""
<!doctype html><meta charset="utf-8"><title>Stav úlohy</title>
<meta name="viewport" content="width=device-width,initial-scale=1" />
<style>
body{{font-family:system-ui;max-width:680px;margin:40px auto;padding:0 16px}}
.card{{border:1px solid #e5e7eb;border-radius:12px;padding:20px;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.status{{margin-top:10px;color:#6b7280}}
a.button{{display:inline-block;padding:10px 16px;background:#2563eb;color:#fff;text-decoration:none;border-radius:8px;margin-top:12px}}
pre{{white-space:pre-wrap;background:#f9fafb;padding:8px;border-radius:8px}}
</style>
<div class="card">
  <h1>🔄 Zpracování</h1>
  <p class="status" id="status">Probíhá…</p>
  <div id="result"></div>
  <p><a href="/" style="text-decoration:none">← Zpět na formulář</a></p>
</div>
<script>
const statusUrl = "/jobs/{job_id}";
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
async function poll(){{
  try {{
    const r = await fetch(statusUrl);
    const j = await r.json();
    if (j.state === "SUCCESS") {{
      statusEl.textContent = "Hotovo ✅";
      const link = j.download_url || (j.data && j.data.download_url);
      if (link) {{
        resultEl.innerHTML = `<a class="button" href="${{link}}">⬇️ Stáhnout ZIP</a>`;
      }} else {{
        resultEl.innerHTML = "<pre>" + JSON.stringify(j, null, 2) + "</pre>";
      }}
    }} else if (j.state === "ERROR") {{
      statusEl.textContent = "Chyba ❌";
      resultEl.innerHTML = "<pre>" + (j.error || JSON.stringify(j, null, 2)) + "</pre>";
    }} else {{
      statusEl.textContent = j.state || "Čekám…";
      setTimeout(poll, 1200);
    }}
  }} catch (e) {{
    statusEl.textContent = "Chyba při načítání stavu";
    resultEl.textContent = String(e);
  }}
}}
poll();
</script>
"""

@app.get("/download/{city}")
def download_zip(city: str):
    p = Path("municipalities_data") / f"{city}.zip"
    if p.exists():
        return FileResponse(p, filename=p.name)
    return {"error": f"ZIP not found at {p}"}
