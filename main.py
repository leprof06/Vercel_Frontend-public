# Vercel Proxy API — garde ton architecture, ajoute un fallback robuste sur /ping
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os, httpx, datetime

RENDER_URL = os.getenv("RENDER_URL", "https://render-backend-f36w.onrender.com").rstrip("/")

app = FastAPI(title="Vercel Proxy API")

# CORS (ouvre large pour debug ; restreins en prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- Utilitaires HTTP --------
async def call_render_json(method: str, endpoint: str, **kwargs):
    url = f"{RENDER_URL}{endpoint}"
    try:
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.request(method, url, **kwargs)
            try:
                data = r.json()
            except Exception:
                data = {"non_json": True, "text": (await _safe_text(r))}
            if r.is_success:
                return JSONResponse(data, status_code=r.status_code)
            else:
                return JSONResponse(
                    {"status": "error", "upstream_status": r.status_code, "data": data},
                    status_code=502
                )
    except httpx.RequestError as e:
        return JSONResponse(
            {"status": "error", "message": "Render unreachable", "detail": str(e)},
            status_code=502
        )

async def _safe_text(r: httpx.Response, limit: int = 400):
    try:
        return r.text[:limit]
    except Exception:
        b = await r.aread()
        return b[:limit].decode("utf-8", errors="ignore")

# -------- Routes simples --------
@app.get("/")
async def root():
    return {
        "service": "Vercel gateway to Render",
        "render_url": RENDER_URL,
        "routes": [
            "/ping",
            "/health",
            "/analyse-prononciation",
            "/score",
            "/langues-supportees",
            "/exercice/{langue}",
            "/ajouter-phrase"
        ]
    }

@app.get("/ping")
async def ping():
    """
    Tente /ping Render ; si 404/erreur (p.ex. au réveil),
    bascule sur /health et renvoie 200 JSON (utile pour cron-job.org).
    """
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # 1) /ping direct
        try:
            r = await client.get(f"{RENDER_URL}/ping", headers={"accept": "application/json"})
            if r.status_code == 200:
                try:
                    return JSONResponse(r.json(), status_code=200)
                except Exception:
                    return JSONResponse({"status": "ok", "note": "non-json upstream on /ping"}, status_code=200)
        except Exception:
            pass

        # 2) Fallback /health
        try:
            r2 = await client.get(f"{RENDER_URL}/health", headers={"accept": "application/json"})
            payload = {}
            try:
                payload = r2.json()
            except Exception:
                payload = {"note": "non-json upstream on /health"}
            return JSONResponse({
                "status": payload.get("status", "ok"),
                "service": "Render Prononciation API (via /health)",
                "time": datetime.datetime.utcnow().isoformat() + "Z"
            }, status_code=200)
        except Exception as e:
            return JSONResponse(
                {"status": "error", "message": "Upstream unreachable", "detail": str(e)},
                status_code=502
            )

@app.get("/health")
async def health():
    return {"status": "ok", "gateway": "vercel", "render_url": RENDER_URL}

@app.get("/langues-supportees")
async def langues_supportees():
    return await call_render_json("GET", "/langues-supportees")

@app.get("/exercice/{langue}")
async def exercice(langue: str):
    return await call_render_json("GET", f"/exercice/{langue}")

@app.post("/ajouter-phrase")
async def ajouter_phrase(langue: str = Form(...), phrase: str = Form(...)):
    data = {"langue": langue, "phrase": phrase}
    return await call_render_json("POST", "/ajouter-phrase", data=data)

# -------- Proxy multipart audio --------
@app.post("/analyse-prononciation")
async def analyse_prononciation(
    fichier: UploadFile = File(...),
    texte_cible: str = Form(...),
    langue_cible: str = Form(None),
    accent: str = Form(None)
):
    file_bytes = await fichier.read()
    files = {
        "fichier": (fichier.filename or "audio.bin",
                    file_bytes,
                    fichier.content_type or "application/octet-stream")
    }
    data = {"texte_cible": texte_cible}
    if langue_cible:
        data["langue_cible"] = langue_cible
    if accent:
        data["accent"] = accent
    return await call_render_json("POST", "/analyse-prononciation", files=files, data=data)

@app.post("/score")
async def score(fichier: UploadFile = File(...), texte_cible: str = Form(...)):
    file_bytes = await fichier.read()
    files = {
        "fichier": (fichier.filename or "audio.bin",
                    file_bytes,
                    fichier.content_type or "application/octet-stream")
    }
    data = {"texte_cible": texte_cible}  # <- correction de la typo
    return await call_render_json("POST", "/score", files=files, data=data)
