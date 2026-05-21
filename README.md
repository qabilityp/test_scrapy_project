# BMW Used Cars Scraper

Scrapes used BMW listings from [usedcars.bmw.co.uk](https://usedcars.bmw.co.uk/) and saves them to SQLite.

## Stack

- Python 3.10+, Scrapy 2.11, scrapy-playwright 0.0.43, SQLite3

## Installation

```bash
git clone https://github.com/qabilityp/test_scrapy_porject.git && cd <project-folder>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Usage

**Main (Scrapy + Playwright):**
```bash
scrapy crawl bmw
```
Scrapes 5 pages (~115 cars), saves to `bmw_cars.db`.

**Alternative (pure asyncio, faster):**
```bash
python run_async.py
```
Same data, saves to `cars.json`. ~30% faster, no Scrapy pipeline.

## What's collected

`model`, `name`, `mileage` (int), `registered`, `engine`, `range`, `exterior`, `fuel` (lowercase), `transmission`, `registration`, `upholstery`

Electric cars have `range` instead of `engine`. Missing fields are `NULL`.

## Bonus tasks

- **User-Agent middleware** — rotates 5+ UA strings, logs at DEBUG level (`middlewares.py`)
- **Cleaning pipeline** — validates required fields, cleans mileage, lowercases fuel (`pipelines.py`)
- **SQLite pipeline** — `UNIQUE` on registration plate, no duplicates on re-run

## Why Playwright?

The site is fully JS-rendered — standard Scrapy HTTP requests return empty pages. `scrapy-playwright` integrates async Playwright directly into Scrapy's engine.
