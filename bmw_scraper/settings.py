BOT_NAME = "bmw_scraper"
SPIDER_MODULES = ["bmw_scraper.spiders"]
NEWSPIDER_MODULE = "bmw_scraper.spiders"

ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 6
DOWNLOAD_DELAY = 0
PLAYWRIGHT_MAX_CONTEXTS = 8

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True}

DOWNLOADER_MIDDLEWARES = {
    'bmw_scraper.middlewares.RandomUserAgentMiddleware': 543,
}
PLAYWRIGHT_ABORT_REQUEST = lambda req: req.resource_type in ("image", "font", "media")


ITEM_PIPELINES = {
    'bmw_scraper.pipelines.CleaningPipeline': 100,
    'bmw_scraper.pipelines.SQLitePipeline': 200,
}

LOG_LEVEL = 'INFO'
# LOG_LEVEL = 'DEBUG' IF ITS NEEDED OR JUST REMOVE LOG_LEVEL


#FEED_FORMAT = 'json'
#FEED_URI = 'sync_cars.json'
FEED_EXPORT_ENCODING = 'utf-8'