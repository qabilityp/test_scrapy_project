import json
import re
import time
import asyncio
from playwright.async_api import async_playwright

PAGES = 5
MAX_CONCURRENT_DETAIL = 5
TIMEOUT_LISTING = 30000
TIMEOUT_DETAIL = 25000
WAIT_SELECTOR_TIMEOUT = 20000
JSON_NAME = 'cars.json'

async def get_all_links(browser):
    all_links = []
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    for page_num in range(1, PAGES + 1):
        page = await context.new_page()
        await page.route("**/*", lambda route: route.abort()
                         if route.request.resource_type in ("image", "font", "media")
                         else route.continue_())
        url = f'https://usedcars.bmw.co.uk/result/?payment_type=cash&size=23&source=home&page={page_num}'
        print(f"Loading listing page {page_num}...")
        await page.goto(url, wait_until='domcontentloaded', timeout=TIMEOUT_LISTING)
        await page.wait_for_selector('div.uvl-c-advert-overview', timeout=WAIT_SELECTOR_TIMEOUT)
        links = await page.eval_on_selector_all(
            'div.uvl-c-advert-overview h3.uvl-c-advert-overview__title a',
            'elements => elements.map(el => el.href)'
        )
        all_links.extend(links)
        print(f"Listing page {page_num}: found {len(links)} cars")
        await page.close()
    await context.close()
    return all_links

async def scrape_car(context, link, semaphore, retries=2):
    async with semaphore:
        for attempt in range(retries + 1):
            page = None
            try:
                page = await context.new_page()
                await page.route("**/*", lambda route: route.abort()
                                 if route.request.resource_type in ("image", "font", "media")
                                 else route.continue_())
                await page.goto(link, wait_until='domcontentloaded', timeout=TIMEOUT_DETAIL)
                await page.wait_for_selector('div.uvl-c-specification-overview__value', timeout=WAIT_SELECTOR_TIMEOUT)

                car = {
                    'model': None, 'name': None, 'mileage_raw': None,
                    'registered': None, 'engine': None, 'range': None,
                    'exterior': None, 'fuel': None, 'transmission': None,
                    'registration': None, 'upholstery': None,
                }

                title = await page.title()
                if title:
                    parts = title.split('|')[0].strip()
                    match = re.match(r'BMW\s+(\w+\s*\d*)\s+(.*)', parts)
                    if match:
                        car['model'] = f"BMW {match.group(1)}"
                        car['name'] = match.group(2).strip()
                    else:
                        car['model'] = parts

                specs = await page.query_selector_all('div.uvl-c-specification-overview__value')
                values = []
                for s in specs:
                    text = await s.inner_text()
                    text = text.strip()
                    if text:
                        values.append(text)

                def safe(i):
                    return values[i] if i < len(values) else None

                car['mileage_raw'] = safe(0)
                car['registered'] = safe(1)
                third = safe(2)
                if third and 'miles' in third.lower():
                    car['range'] = third
                else:
                    car['engine'] = third
                car['exterior'] = safe(3)
                car['fuel'] = safe(4)
                car['transmission'] = safe(5)
                car['registration'] = safe(6)
                car['upholstery'] = safe(7)

                return car

            except Exception as e:
                if attempt < retries:
                    print(f"Attempt {attempt+1} failed for {link}, retrying in 2 sec...")
                    await asyncio.sleep(2)
                else:
                    print(f"Failed after {retries+1} attempts on {link}: {e}")
                    return None
            finally:
                if page is not None:
                    await page.close()

    return None

def validate_and_clean(car):
    if not car.get('model') or not car.get('name') or not car.get('registration'):
        return None
    mileage = car.get('mileage_raw')
    if mileage:
        try:
            car['mileage_raw'] = int(mileage.replace(',', ''))
        except ValueError:
            car['mileage_raw'] = None
    if car.get('fuel'):
        car['fuel'] = car['fuel'].lower()
    return car

async def main():
    start_time = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Собираем все ссылки (последовательно, это быстро)
        all_links = await get_all_links(browser)
        print(f"🚀 Total detail links collected: {len(all_links)}")

        # 2. Параллельная обработка детальных страниц (один контекст, много вкладок)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_DETAIL)
        tasks = [scrape_car(context, link, semaphore) for link in all_links]
        results = await asyncio.gather(*tasks)

        await context.close()
        await browser.close()

    # Фильтруем None (ошибки)
    all_cars = [car for car in results if car is not None]
    print(f"✅ Collected {len(all_cars)} cars before validation")

    # Валидация и очистка
    valid_cars = []
    for car in all_cars:
        cleaned = validate_and_clean(car)
        if cleaned:
            valid_cars.append(cleaned)
    print(f"✅ After validation: {len(valid_cars)} cars remain")

    # Сохраняем в JSON
    with open(JSON_NAME, 'w', encoding='utf-8') as f:
        json.dump(valid_cars, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved to {JSON_NAME}")

    elapsed = time.time() - start_time
    print(f"⏱ Total time: {elapsed:.1f} seconds")

if __name__ == '__main__':
    asyncio.run(main())