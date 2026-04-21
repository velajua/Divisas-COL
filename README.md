# 💱 Divisas Bogotá

Live site: https://cedar-setup-376217.web.app / https://www.divisascol.com

A lightweight data pipeline + static site that aggregates daily currency exchange data in Bogotá and serves it via Firebase Hosting.

---

## 🚀 Overview

This project:

- Scrapes exchange rates from multiple sources
- Processes and normalizes the data
- Generates a `result.json`
- Serves a static frontend that displays:
  - Best buy/sell rates
  - Comparisons across exchange houses
  - City-scoped insights

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
│   ├── app.js
│   └── result.json
├── exchanges/
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
4. Output → html/result.json  
5. Frontend renders  

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
    ├── medellin-01.svg
    ├── ...
    └── manifest.json
```

The generator creates city cards showing the best buy and sell places per
currency. If the run date matches an entry in `html/entries.json`, it also
adds a `newsletter.svg` card with the latest newsletter title and short
description.

Useful options:

python generate_instagram_cards.py --date 2026-04-18
python generate_instagram_cards.py --currencies AmericanDollar Euro BritishPound
python generate_instagram_cards.py --max-rows 5

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
