# Scrapy settings for reid project
import scrapy
from decouple import config

# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

# from selenium.webdriver import Chrome
# import chromedriver_binary

BOT_NAME = "reid"

SPIDER_MODULES = ["reid.spiders"]
NEWSPIDER_MODULE = "reid.spiders"

# Selenium Configuration
# SELENIUM_DRIVER_NAME = "chrome"
# SELENIUM_DRIVER_EXECUTABLE_PATH = Chrome
# SELENIUM_DRIVER_ARGUMENTS = ["--headless"]
# source: https://github.com/clemfromspace/scrapy-selenium

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = "reid (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
# CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN = 16
# CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#     "reid.middlewares.PropsSpiderMiddleware": 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    # "props.middlewares.PropertiesDownloaderMiddleware": 543,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 90,
    "scrapy_proxies.RandomProxy": 100,
    "scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware": 110,
}
# See scrapy-proxies docs https://github.com/aivarsk/scrapy-proxies
# PROXY_LIST = "new-proxy.txt"

PROXY_MODE = 2
CUSTOM_PROXY = config("PROXY_URL")

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    "reid.pipelines.property.PropertyPipeline": 200,
    "reid.pipelines.property.ListingPipeline": 300,
    # "reid.pipelines.local.CheckMissingFieldsPipeline": 300,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
# AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = "httpcache"
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

# REID Websites and their codes
REID_CODE = {
    "Bali Properties for Sale": "BOFS",
    "Teal Estate": "TEST",
    "Bali Property Direct": "BPOD",
    "Bali Real Estate Consultants": "BREC",
    "Bali Realty": "BREL",
    "Bali Select": "BSEL",
    "Bali Treasure Properties": "BTPR",
    "Heritage Bali": "HRTB",
    "Unreal Bali": "URLB",
    "Exotiq Property": "EXCP",
    "Kibarer": "KIBR",
    "Paradise Property Group": "PPGB",
    "Lazudi": "LAZD",
    "Suasa Real Estate": "SURE",
    "Svaha Property": "SVHP",
    "Luxindo Property": "LUXP",
    "Raja Villa Property": "RJVP",
    "GD&ASSOCIATES": "GDAC",
    "Bali Home Immo": "BHIM",
    "Propertia": "PROP",
    "Bali Exception": "BEXC",
    "Villas of Bali": "VOFB",
    "Dot Property": "DOTP",
    "Bali Coconut Living": "BCLV",
    "Ray White Indonesia": "RWID",
    "Bali Moves": "BLMV",
    "Ubud Property": "UBPR",
}

ZONING_COLORS = {
    "yellow": "Residential",
    "red": "Commercial",
    "pink": "Tourism",
    "green": "Agricultural",
    "dark green": "Green",
    "orange": "Sacred",
    "grey": "Industrial",
    "blue": "Special",
}

ZONING_CATEGORIES = {
    "residential": "Residential",
    "commercial": "Commercial",
    "tourism": "Tourism",
}

# Logging configuration
# LOG_LEVEL = "INFO"
# LOG_FILE = "scrapy.log"
# LOG_SETTINGS = "logging.conf"
