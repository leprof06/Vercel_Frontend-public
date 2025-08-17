🌐 Vercel Proxy API → Render (FastAPI)

Passerelle Vercel (Serverless Python) qui relaie les requêtes du front vers ton backend Render (API prononciation). Elle gère aussi un fallback /ping → /health pour réveiller Render proprement.

Attribution : merci de mentionner que la partie serveur d’analyse a été créée par leprof06.

✨ Ce que fait ce proxy

Expose des routes identiques à ton backend (Render) : /analyse-prononciation, /score, /exercice/{langue}, etc.

Relaye vers RENDER_URL (variable d’environnement) avec timeouts raisonnables.

/ping tente d’abord RENDER_URL/ping, sinon bascule sur RENDER_URL/health et renvoie 200 pour les cron/keep‑alive.

CORS ouvert par défaut (à restreindre en prod).

Aucune clé API n’est utilisée ici. Le proxy ne stocke ni ne journalise d’infos sensibles côté Vercel.

🧩 Architecture

Frontend (Vercel) ──▶ Vercel Proxy API ──▶ Backend Render
                        (ce repo)            (prononciation)

Le front appelle le proxy (même domaine Vercel), qui forward vers Render.

Avantage : CORS simplifié, wake‑up Render maîtrisé, URL unique côté front.

⚙️ Prérequis

Compte Vercel

Ce repo contenant : main.py, requirements.txt, vercel.json

requirements.txt

fastapi
uvicorn
python-multipart
httpx
langdetect

vercel.json

{
  "version": 2,
  "env": {
    "RENDER_URL": "https://render-backend-xxxxx.onrender.com"
  },
  "builds": [{ "src": "main.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/(.*)", "dest": "main.py" }]
}

Remplace la valeur par l’URL réelle de ton backend Render ou définis RENDER_URL dans l’UI Vercel (Projects → Settings → Environment Variables).

🚀 Déploiement sur Vercel (recommandé)

Importer le repo dans Vercel (New Project → GitHub → ce dépôt).

Dans Settings → Environment Variables, ajouter :

RENDER_URL = https://<ton-service>.onrender.com

Deploy. Vercel va servir main.py en Python serverless.

Si tu changes RENDER_URL plus tard, redeploie (ou utilise les Préviews).

🔌 Endpoints exposés par le proxy

GET / → info service & routes

GET /ping → tente RENDER_URL/ping puis fallback RENDER_URL/health en 200 (idéal pour cron)

GET /health → {"status":"ok","gateway":"vercel","render_url":"..."}

GET /langues-supportees

GET /exercice/{langue}

POST /ajouter-phrase (form-data : langue, phrase)

POST /analyse-prononciation (multipart : fichier, texte_cible, langue_cible?, accent?)

POST /score (multipart : fichier, texte_cible)

Exemple curl

# Health direct (Vercel)
curl -sS https://<ton-proxy-vercel>.vercel.app/health | jq .

# Analyse prononciation via proxy
echo "fake" > test.wav  # (remplace par un vrai wav)
curl -sS https://<ton-proxy-vercel>.vercel.app/analyse-prononciation \
  -F "fichier=@test.wav" \
  -F "texte_cible=Bonjour, je m'appelle Marie." | jq .

🔐 Sécurité & CORS

Par défaut : allow_origins=["*"] (debug). En production, restreins aux domaines de ton front.

RENDER_URL est une URL publique, aucun secret.

Ce proxy ne traite que des fichiers temporaires en mémoire et forwarde vers Render.

🛠️ Utilisation côté Front

Configure l’URL de l’API côté front pour pointer vers le proxy :

NEXT_PUBLIC_TEXT_ANALYSE_URL=https://<ton-proxy-vercel>.vercel.app/analyse-prononciation

Ensuite, requête standard fetch :

const form = new FormData();
form.append("fichier", file);
form.append("texte_cible", "Bonjour, je m'appelle Marie.");
const r = await fetch("https://<ton-proxy-vercel>.vercel.app/analyse-prononciation", { method: "POST", body: form });
const data = await r.json();

🧪 Tests rapides

GET /health → OK.

GET /ping → OK (même si Render dormait, le retour reste 200).

POST /analyse-prononciation avec un petit audio → réponse JSON du backend Render.

📄 Licence & attribution

Licence : à définir (MIT conseillé).

Merci de mentionner leprof06 si vous réutilisez la partie serveur d’analyse.

