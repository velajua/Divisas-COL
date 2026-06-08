# Fix Punto Dollar Envigado Health Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make scraper health checks pass only for active, valid sources while clearly reporting that Punto Dollar Envigado is currently unavailable upstream.

**Architecture:** Add first-class disabled scraper support in config iteration so temporarily broken upstream sources can be excluded from production scraping without deleting their metadata. Improve health-check diagnostics for empty scraper results so future source removals show a direct "no currencies scraped" failure instead of only a list of missing expected currencies.

**Tech Stack:** Python 3.11, `unittest`, `EnvYAML`, BeautifulSoup/requests scrapers, existing `python main.py health` health-check command.

---

## Investigation Summary

The command `python main.py health` failed on Sunday, June 7, 2026 with one failing scraper:

```text
[FAIL] puntoDollar (colombia | Medellín | https://www.puntodollar.com/tasa-de-cambio-envigado/)
  Missing currencies: ['AmericanDollar', 'AustralianDollar', 'BrasilianReal', 'BritishPound', 'CanadianDollar', 'ChileanPeso', 'Euro', 'MexicanPeso', 'PeruveanNewSun', 'SwissFranc']
```

Direct parser reproduction returned an empty data payload:

```json
{
  "id": "puntoDollarEnvigado",
  "data": {}
}
```

The configured Envigado URL resolves to `https://www.puntodollar.com`, whose page has zero `<table>`, `<tr>`, or `<td>` elements. Punto Dollar's current navigation points "Tasa de cambio en Envigado" to `https://www.puntodollar.com/?page_id=16728`, but that URL also resolves to the home page and has zero rates table rows. The Punto Dollar sitemap lists the other rate pages but does not list an Envigado rate page. This is an upstream page availability issue, not a local parsing difference.

## File Structure

- Modify `helpers.py`: skip scraper specs where `enabled` is exactly `False`.
- Modify `config.yaml`: mark the Punto Dollar Envigado spec as disabled and record the upstream reason.
- Modify `health_check.py`: set an explicit error when a scraper returns a row with empty `data`.
- Modify `tests/test_country_structure.py`: add coverage for disabled scraper configs.
- Create `tests/test_health_check.py`: add focused unit coverage for the empty-data health diagnostic.

---

### Task 1: Add Disabled Scraper Config Support

**Files:**
- Modify: `helpers.py`
- Test: `tests/test_country_structure.py`

- [ ] **Step 1: Write the failing test**

Add this method to `CountryConfigTests` in `tests/test_country_structure.py`:

```python
    def test_iter_scraper_configs_skips_disabled_specs(self):
        conf = {
            "function_dicto": {
                "colombia": {
                    "Medellín": {
                        "https://www.puntodollar.com/tasa-de-cambio-envigado/": {
                            "fn": "puntoDollar",
                            "args": "Envigado",
                            "enabled": False,
                            "disabled_reason": "Upstream page redirects to home page with no rates table.",
                        },
                        "https://euroservicios.com.co/": {
                            "fn": "euroservicios",
                        },
                    }
                }
            }
        }

        configs = list(helpers.iter_scraper_configs(conf))

        self.assertEqual(
            configs,
            [
                (
                    "colombia",
                    "Medellín",
                    "https://euroservicios.com.co/",
                    {"fn": "euroservicios"},
                )
            ],
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bat
python -m unittest tests.test_country_structure.CountryConfigTests.test_iter_scraper_configs_skips_disabled_specs
```

Expected: FAIL because `iter_scraper_configs()` still yields the disabled Punto Dollar Envigado spec.

- [ ] **Step 3: Implement disabled filtering**

Change `helpers.iter_scraper_configs` to:

```python
def iter_scraper_configs(conf=None):
    function_dicto = (conf or CONF).get("function_dicto", {}) or {}

    for country, cities in function_dicto.items():
        for city, city_scrapers in (cities or {}).items():
            for url, spec in (city_scrapers or {}).items():
                if isinstance(spec, dict) and spec.get("enabled") is False:
                    continue
                yield country, city, url, spec
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bat
python -m unittest tests.test_country_structure.CountryConfigTests.test_iter_scraper_configs_skips_disabled_specs
```

Expected: PASS.

- [ ] **Step 5: Run existing country config tests**

Run:

```bat
python -m unittest tests.test_country_structure.CountryConfigTests
```

Expected: PASS.

---

### Task 2: Disable Punto Dollar Envigado in Config

**Files:**
- Modify: `config.yaml`

- [ ] **Step 1: Update the Envigado scraper spec**

Change the Medellín Punto Dollar entry in `config.yaml` from:

```yaml
        "https://www.puntodollar.com/tasa-de-cambio-envigado/": {
            "fn": "puntoDollar",
            "args": "Envigado",
        },
```

to:

```yaml
        "https://www.puntodollar.com/tasa-de-cambio-envigado/": {
            "fn": "puntoDollar",
            "args": "Envigado",
            "enabled": False,
            "disabled_reason": "Upstream page redirects to the Punto Dollar home page and currently exposes no rates table.",
        },
```

- [ ] **Step 2: Run the health check**

Run:

```bat
python main.py health
```

Expected: PASS for all active scrapers; the Punto Dollar Envigado row should not appear in the report.

---

### Task 3: Make Empty Scraper Results Diagnosable

**Files:**
- Modify: `health_check.py`
- Create: `tests/test_health_check.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_health_check.py`:

```python
import unittest
from unittest.mock import patch

import health_check


class HealthCheckTests(unittest.TestCase):
    def test_empty_scraper_data_reports_no_currencies_scraped(self):
        conf = {
            "function_dicto": {
                "colombia": {
                    "Medellín": {
                        "https://example.com/envigado": {
                            "fn": "puntoDollar",
                            "args": "Envigado",
                        }
                    }
                }
            },
            "expected_currencies": {
                "puntoDollar": {
                    "AmericanDollar": True,
                    "Euro": True,
                }
            },
        }

        def fake_punto_dollar(url, total_data, local):
            total_data.append({"id": f"puntoDollar{local}", "data": {}})
            return total_data

        with patch.object(health_check, "CONF", conf), patch.object(
            health_check, "_resolve_fn", return_value=fake_punto_dollar
        ):
            result = health_check.run_health_check()[0]

        self.assertFalse(result.success)
        self.assertEqual(result.currency_count, 0)
        self.assertEqual(result.error, "No currencies scraped")
        self.assertEqual(result.missing_currencies, ["AmericanDollar", "Euro"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bat
python -m unittest tests.test_health_check.HealthCheckTests.test_empty_scraper_data_reports_no_currencies_scraped
```

Expected: FAIL because `result.error` is currently `None` for an empty `data` dict.

- [ ] **Step 3: Implement explicit empty-data error**

In `health_check.run_health_check`, after:

```python
            result.currency_count = len(entry.get("data", {}))
```

add:

```python
            if result.currency_count == 0:
                result.error = "No currencies scraped"
```

Keep the existing missing-currency and invalid-value checks after this assignment so the report still shows which expected IDs were absent.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bat
python -m unittest tests.test_health_check.HealthCheckTests.test_empty_scraper_data_reports_no_currencies_scraped
```

Expected: PASS.

- [ ] **Step 5: Run focused regression tests**

Run:

```bat
python -m unittest tests.test_health_check tests.test_country_structure.CountryConfigTests
```

Expected: PASS.

---

### Task 4: Verify End-to-End Scraper Health

**Files:**
- Verify: `health_check.py`
- Verify: `helpers.py`
- Verify: `config.yaml`

- [ ] **Step 1: Run the full health command**

Run:

```bat
python main.py health
```

Expected:

```text
SUMMARY: ALL PASSED
```

The output should include the remaining active scrapers:

```text
puntoDollar Unicentro
puntoDollar Salitre
cambiosVancouver
cambiosKapital
bancounion
eurodolar
amerikanCash Retiro
amerikanCash Calle122
euroservicios
puntoDollar Cali
puntoDollar Barranquilla
puntoDollar Cartagena
```

The output should not include:

```text
https://www.puntodollar.com/tasa-de-cambio-envigado/
```

- [ ] **Step 2: Run the full Python unit test suite**

Run:

```bat
python -m unittest
```

Expected: PASS.

- [ ] **Step 3: Check working tree scope**

Run:

```bat
git status --short
```

Expected changed files from this plan:

```text
 M config.yaml
 M health_check.py
 M helpers.py
 M tests/test_country_structure.py
?? tests/test_health_check.py
```

Existing unrelated dirty files may also appear; do not stage or overwrite those files.

---

## Re-enable Procedure for Envigado

When Punto Dollar restores a valid Envigado rate page:

1. Confirm the page has table rows:

```bat
python -c "import requests; from bs4 import BeautifulSoup; u='REPLACE_WITH_RESTORED_ENVIGADO_URL'; s=BeautifulSoup(requests.get(u,timeout=30).text,'lxml'); print(len(s.find_all('tr')), [[td.get_text(' ',strip=True) for td in tr.find_all('td')] for tr in s.find_all('tr')[:3]])"
```

Expected: at least 11 `<tr>` rows and first row labels like `País`, `Compra`, `Venta`.

2. Update the Envigado key in `config.yaml` to the restored URL if it changed.

3. Change `"enabled": False` to `"enabled": True` or remove the `enabled` key.

4. Run:

```bat
python main.py health
```

Expected: Punto Dollar Envigado appears again and `SUMMARY: ALL PASSED`.

