import scrapy
from urllib.parse import urljoin
from scrapy.loader import ItemLoader
from datetime import datetime
from reid.items import PropertyItem
from itemloaders.processors import MapCompose
import re

from reid.func import (
    define_property_type,
    find_build_size,
    find_idr,
    find_land_size,
    find_usd,
)

from reid.customs.ubudproperty import (
    find_code,
    extract_publish_date,
    find_leasehold_years,
)


class UbudpropertySpider(scrapy.Spider):
    name = "ubudproperty"
    allowed_domains = ["ubudproperty.com"]
    start_urls = [
        "https://ubudproperty.com/listing-villaforsale",
        # "https://ubudproperty.com/listing-landforsale",
    ]
    visited = []

    def parse(self, response):
        # collect urls
        codes = response.css("a:contains(Detail)::attr(href)").getall()
        urls = list(map(lambda x: urljoin(response.url, x), codes))
        yield scrapy.Request(urls[0], callback=self.parse_detail)
        # for url in urls:
        #     yield scrapy.Request(url, callback=self.parse_detail)
        # do pagination
        # last_page = response.css("ul.pagination li:contains(Last) a::attr(href)").get()
        # if last_page:
        #     max_page = last_page.split("=")[-1]
        #     max_page = int(max_page)
        #     for i in range(2, max_page + 1):
        #         # example: https://ubudproperty.com/listing-villaforsale=2
        #         next_page = response.url + "=" + str(i)
        #         footprint = response.url.split("/")[-1].split("=")[0].split("-")[-1]
        #         footprint += "=" + str(i)
        #         if footprint not in self.visited:
        #             self.visited.append(footprint)
        #             yield scrapy.Request(next_page, callback=self.parse)

    def parse_detail(self, response):
        now = datetime.now().strftime("%m/01/%y")
        loader = ItemLoader(item=PropertyItem(), selector=response)
        # collect raw data
        loader.add_value("source", "Ubud Property")
        loader.add_value("scraped_at", now)
        loader.add_value("url", response.url)
        loader.add_value("html", response.text)
        # pre processed data
        alt_title = (
            response.css("h2.title::Text").get().strip()
        )  # price also exists in here
        ## finding lisiting listed/publish date
        sources = response.css("img[src]::attr(src)").getall()
        publish_dates = list(map(extract_publish_date, sources))
        publish_dates = list(filter(lambda d: d, publish_dates))
        pdate = max(publish_dates)
        ## finding leasehold years
        leasehold_years_text = response.css("h5 ::Text").get()
        # template selector
        template_css = "div.table-fut table tr:contains({}) td:last-child::Text"
        # collect property data
        loader.add_value("property_id", alt_title, MapCompose(find_code))
        # loader.add_css('is_off_plan', '')
        if pdate:
            loader.add_value("listed_date", pdate.strftime(r"%Y-%m-%d"))
        loader.add_css("title", "div#ENG p span::Text,div#ENG p strong::Text")
        loader.add_value("location", "Ubud")
        loader.add_css("contract_type", template_css.format("TITLE"))
        loader.add_css(
            "property_type",
            "div#ENG p span::Text,div#ENG p strong::Text",
            MapCompose(lambda w: w.split(" ")[0].title()),
        )
        loader.add_value(
            "leasehold_years", leasehold_years_text, MapCompose(find_leasehold_years)
        )
        loader.add_css("bedrooms", template_css.format("BEDROOM"))
        loader.add_css("bathrooms", template_css.format("BATHROOM"))
        loader.add_css(
            "land_size",
            template_css.format("LAND"),
            MapCompose(find_land_size),
        )
        loader.add_css(
            "build_size",
            template_css.format("BUILDING"),
            MapCompose(find_build_size),
        )
        # loader.add_css('price', '')
        # loader.add_css('currency', '')
        loader.add_css("image_url", "div.thumbDetail img::attr(src)")
        loader.add_value("availability_label", "Available")
        loader.add_css("description", "div#ENG ::Text")
        # redefine value based on collected value
        item = loader.load_item()
        ## replace title with alt_title if not exist
        title = item.get("title", None)
        if not title or title == ".":
            item["title"] = alt_title
        ## define property type
        bedrooms = item.get("bedrooms", 0)
        property_type = item.get("property_type", "")
        if property_type not in ["Villa", "Land", "House"]:
            result = re.search(
                r"(land|hotel|villa)", title, re.IGNORECASE
            )  # find land,hotel,and villa keyword in title
            if result:
                property_type = result.group().title()
                property_type = define_property_type(property_type)
                item["property_type"] = property_type
            else:
                item["property_type"] = "Villa" if bedrooms > 0 else "Land"
        ## remove title text from the description
        desc = item.get("description", "")
        if item.get("title", "") in desc:
            item["description"] = desc.replace(title, "")
        ## find leasehold years in the table ##
        contract_type = item.get("contract_type")
        leasehold_years = item.get("years")
        alt_years = response.css(
            "table tr:contains(LEASING) td:last-child ::Text"
        ).get()
        if "Leasehold" in contract_type and not leasehold_years and alt_years:
            item["years"] = find_leasehold_years(alt_years)
        ## make sure the leasehold_years is empty on freehold ##
        if "Freehold" in contract_type:
            item["years"] = None
        yield item
