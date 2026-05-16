# Divisas COL

Live site: https://cedar-setup-376217.web.app / https://www.divisascol.com

A lightweight data pipeline + static site that aggregates daily currency exchange data by country and city, then serves it via Firebase Hosting.

---

## 🚀 Overview

This project:

- Scrapes exchange rates from multiple sources
- Processes and normalizes the data
- Generates a compact `result.json`
- Serves a static frontend that displays:
  - Best buy/sell rates
  - Comparisons across exchange houses
  - Country and city-scoped insights

Deployment is fully automated via GitHub Actions and Firebase Hosting.

---

## 🏗️ Architecture

Scrapers (Python)
↓
Data processing
↓
result.json
↓
Static frontend (html/)
↓
Firebase Hosting

---

## ⚙️ Project structure

```
.
├── html/
│   ├── index.html
│   ├── colombia/
│   │   ├── index.html
│   │   ├── bogota/
│   │   └── assets/
│   ├── aurum-script.js
│   └── result.json
├── exchanges/
│   └── colombia/
├── helpers/
├── config.yaml
├── main.py
├── requirements.txt
└── .github/workflows/
```

---

## 🔄 Data pipeline

1. Scrapers pull data  
2. Data is cleaned and normalized  
3. Sources are merged  
4. Output → `html/result.json` with country-scoped rates under `countries`
5. Frontend renders

The public JSON intentionally avoids duplicate legacy keys. The canonical shape is:

```json
{
  "ok": true,
  "health_passed": 8,
  "health_failed": 0,
  "countries": {
    "colombia": {
      "Bogotá": {
        "puntoDollar": [
          {
            "id": "PuntoDollar Unicentro",
            "url": "https://example.com",
            "rates": {
              "AmericanDollar": {
                "label": "Dólar Estadounidense",
                "buy": "4000",
                "sell": "4100"
              }
            }
          }
        ]
      }
    }
  }
}
```

---

## 🧪 Local testing

Run static site:

cd html
python -m http.server 8000

Open:
http://localhost:8000

Alternatives:
python3 -m http.server 8000
py -m http.server 8000

Stop:
Ctrl + C

---

## ▶️ Run pipeline locally

pip install -r requirements.txt
python main.py

---

## 📣 Generate Instagram cards

Create daily carousel-ready SVG cards from `html/result.json`:

python generate_instagram_cards.py

Output is organized at the repository root by day:

```
instagram_cards/
└── YYYY-MM-DD/
    ├── bogota-01.svg
    ├── public/
    │   ├── bogota-01.jpg
    │   └── publish-manifest.json
    ├── medellin-01.svg
    ├── ...
    └── manifest.json
```

The generator creates city cards showing the best buy and sell places per
currency. If the run date matches an entry in `html/colombia/entries.json`, it also
adds a `newsletter.svg` card with the latest newsletter title and short
description.

Useful options:

python generate_instagram_cards.py --date 2026-04-18
python generate_instagram_cards.py --currencies AmericanDollar Euro BritishPound
python generate_instagram_cards.py --max-rows 5

## 📲 Publish Instagram cards

Instagram publishing uses the Meta API. The Instagram account must be a
professional account connected to the Facebook Page, and `.env` needs:

```
INSTAGRAM_USER_ID=1784...
META_PAGE_ACCESS_TOKEN=EAAB...
META_APP_ACCESS_TOKEN=APP_ID|APP_TOKEN
SITE_BASE_URL=https://divisascol.com
META_GRAPH_VERSION=v24.0
```

Do not use `FB_USER`, `FB_PASS`, `INSTA_USER`, or `INSTA_PASS` for API
publishing. Those are login credentials, not Meta publishing tokens.

python -m playwright install chromium
python generate_instagram_cards.py

Publish today's generated cards. The script starts a temporary HTTPS tunnel,
updates `instagram_cards/YYYY-MM-DD/public/publish-manifest.json` with tunnel
URLs, groups images into carousels by filename prefix, and publishes them:

python instagram_publish.py

Publish a specific date folder:

python instagram_publish.py --date 2026-05-10

Cards named `bogota-01.jpg`, `bogota-02.jpg`, etc. publish as one carousel.
`newsletter.jpg` publishes as its own single-image post.

---

## ☁️ Deployment

Handled via GitHub Actions:
- Daily cron
- Manual trigger

Steps:
1. Run pipeline  
2. Generate result.json  
3. Deploy to Firebase  

---

## 🌍 Hosting

https://cedar-setup-376217.web.app

---

## 🌐 Custom domain

Firebase → Hosting → Add custom domain

DNS:

A     @     199.36.158.100
CNAME www   ghs.googlehosted.com

---

## 💰 AdSense

1. https://www.google.com/adsense/
2. Add domain
3. Add script:

<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
 crossorigin="anonymous"></script>

Deploy:
firebase deploy
