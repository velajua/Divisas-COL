# Divisas COL

## Overview

This project scrapes currency exchange rates from multiple providers across Colombia and publishes a static website that displays the results.

The system is composed of two main parts:

1. **Data Pipeline (Python)**
   - Runs scrapers for multiple exchange providers (Bogotá, Medellín, Cali, etc.)
   - Performs health checks on each scraper
   - Aggregates results into a single JSON output
   - Writes the final file to:
     html/result.json

2. **Frontend (Static Site)**
   - Located in the `html/` directory
   - Uses HTML, CSS, and JavaScript
   - Fetches `/result.json` on page load
   - Renders exchange rate data dynamically

---

## Deployment Architecture

This project uses a **serverless deployment model**:

- **Firebase Hosting**
  - Serves the static site (`html/`)
  - URL:  
    https://cedar-setup-376217.web.app

- **GitHub Actions**
  - Runs daily via cron
  - Executes:
    python main.py save
  - Updates `html/result.json`
  - Deploys the updated site to Firebase Hosting

---

## Repository Structure

.
├── html/
│   ├── index.html
│   ├── templatemo-aurum-script.js
│   ├── templatemo-aurum-gold.css
│   └── result.json
├── exchanges/
├── helpers.py
├── health_check.py
├── main.py
├── requirements.txt
├── .github/
│   └── workflows/
│       └── daily-update.yml
├── firebase.json
└── README.md

---

## Data Flow

1. GitHub Actions runs daily
2. `main.py save` executes
3. Output written to html/result.json
4. GitHub commits updated JSON
5. Firebase deploys updated site
6. Frontend fetches latest data

---

## Health Check Behavior

Summary example:

SUMMARY: ALL PASSED
Passed: 10/10
Failed: 0/10

If any failure occurs:
- deployment still happens
- workflow fails at the end
- notification is triggered

---

## Local Development

Run:

python main.py save

Preview:

firebase serve --only hosting

---

## Firebase Hosting

Check deployments:
https://console.firebase.google.com/project/cedar-setup-376217/hosting

---

## Notes

- No backend server required
- Fully static deployment
- JSON regenerated daily
