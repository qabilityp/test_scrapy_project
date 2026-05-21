import time
import scrapy
import re
from bmw_scraper.items import CarItem
from scrapy import signals
from scrapy_playwright.page import PageMethod


class BmwSpider(scrapy.Spider):
    name = 'bmw'

    def handle_error(self, failure):
        request = failure.request
        retry_count = request.meta.get('retry_count', 0)
        self.logger.warning(
            f"Request failed: {request.url} – {failure.value} (attempt {retry_count + 1})"
        )
        if retry_count < 3:  # up to 3 attempts
            new_request = request.copy()
            new_request.meta['retry_count'] = retry_count + 1
            new_request.dont_filter = True
            return new_request
        else:
            self.logger.error(f"All retries exhausted for {request.url}")
            return None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = None
        self.total_cars = 0

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.logger.info(f"⏱ Total time: {elapsed:.1f} sec")
            self.logger.info(f"📊 Total cars scraped: {self.total_cars}")
            if elapsed > 0:
                self.logger.info(f"📊 Speed: {self.total_cars / elapsed:.2f} cars/sec")

    def start_requests(self):
        for page_num in range(1, 6):
            url = f'https://usedcars.bmw.co.uk/result/?payment_type=cash&size=23&source=home&page={page_num}'
            yield scrapy.Request(
                url,
                meta=dict(
                    playwright=True,
                    playwright_include_page=True,
                    playwright_page_methods=[
                        PageMethod('wait_for_selector', 'div.uvl-c-advert-overview', timeout=15000),
                    ],
                ),
                callback=self.parse_listing,
                cb_kwargs=dict(page_num=page_num),
                errback=self.handle_error,
            )

    async def parse_listing(self, response, page_num):
        page = response.meta["playwright_page"]
        # Extract detail page links
        links = await page.eval_on_selector_all(
            'div.uvl-c-advert-overview h3.uvl-c-advert-overview__title a',
            'elements => elements.map(el => el.href)'
        )
        self.logger.info(f"Page {page_num}: found {len(links)} cars")

        for link in links:
            yield scrapy.Request(
                link,
                meta=dict(
                    playwright=True,
                    playwright_include_page=True,
                    playwright_page_methods=[
                        PageMethod('wait_for_selector', 'div.uvl-c-specification-overview__value', timeout=15000),
                    ],
                    retry_count=0,
                ),
                callback=self.parse_car,
                errback=self.handle_error,
            )
        await page.close()

    async def parse_car(self, response):
        page = response.meta["playwright_page"]
        retry_count = response.meta.get("retry_count", 0)

        try:
            title = await page.title()
            car_dict = {
                'model': None, 'name': None, 'mileage_raw': None,
                'registered': None, 'engine': None, 'range': None,
                'exterior': None, 'fuel': None, 'transmission': None,
                'registration': None, 'upholstery': None,
            }

            # Parse title
            parts = title.split('|')[0].strip()
            match = re.match(r'BMW\s+(\w+\s*\d*)\s+(.*)', parts)
            if match:
                car_dict['model'] = f"BMW {match.group(1)}"
                car_dict['name'] = match.group(2).strip()
            else:
                car_dict['model'] = parts

            # Parse specs
            specs = await page.query_selector_all('div.uvl-c-specification-overview__value')
            values = []
            for spec in specs:
                text = (await spec.inner_text()).strip()
                if text:
                    values.append(text)

            def safe(i):
                return values[i] if i < len(values) else None

            car_dict['mileage_raw'] = safe(0)
            car_dict['registered'] = safe(1)
            third = safe(2)
            if third and 'miles' in third.lower():
                car_dict['range'] = third
            else:
                car_dict['engine'] = third
            car_dict['exterior'] = safe(3)
            car_dict['fuel'] = safe(4)
            car_dict['transmission'] = safe(5)
            car_dict['registration'] = safe(6)
            car_dict['upholstery'] = safe(7)

            yield CarItem(**car_dict)
        except Exception as e:
            self.logger.error(f"Parsing error for {response.url}: {e}")
        finally:
            await page.close()