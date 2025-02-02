from scrapy.loader import ItemLoader
from reid.customs.balipropertiesforsale import to_mmddyy
from reid.items import PropertyItem
from itemloaders.processors import MapCompose
from reid.spiders.base import BaseSpider
from reid.func import (
    dimension_remover,
    find_lease_years,
)
from models.error import Error
from reid.database import get_db
import traceback
import re
import html2text
import urllib.parse
from math import ceil
import scrapy

md_converter = html2text.HTML2Text()

PARAMS = {
    "page": 1,
    "posts_per_page": 12,
    "search_by_id": True,
    "sortby": "a_price",
    "status[0]": "leasehold",
    "touched": False,
    "type[0]": "Villa",
}


class BaliPropertiesForSaleSpider(BaseSpider):
    name = "balipropertiesforsale"
    allowed_domains = ["balipropertiesforsale.com"]
    start_urls = ["https://balipropertiesforsale.com/wp-json/properties/v1/list/"]
    visited = []

    def start_requests(self):
        query_string = urllib.parse.urlencode(PARAMS)
        url = self.start_urls[0] + "?" + query_string
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        try:
            data = response.json()
            items = data.get("results", [])

            for item in items:
                url = f"https://balipropertiesforsale.com/property/{item['post']['post_name']}/"
                yield scrapy.Request(
                    url, callback=self.parse_detail, meta={"json_data": item}
                )

            # Pagination
            count = data.get("count", 1)
            max_page = ceil(count / 12)
            for i in range(2, max_page + 1):
                PARAMS["page"] = i
                query_string = urllib.parse.urlencode(PARAMS)
                next_url = self.start_urls[0] + "?" + query_string
                if next_url not in self.visited:
                    self.visited.append(next_url)
                    yield scrapy.Request(next_url, callback=self.parse)

        except Exception as err:
            error = Error(
                url=response.url,
                source="Spider",
                error_message=str(err),
            )
            tb = traceback.format_exc()
            error.error_message += f"\nTraceback:\n{tb}"
            db = next(get_db())
            db.add(error)
            db.commit()

    def parse_detail(self, response):
        try:
            loader = ItemLoader(item=PropertyItem(), selector=response)
            loader.add_value("source", "Bali Properties for Sale")
            loader.add_value("scraped_at", self.scraped_at)
            loader.add_value("url", response.url)
            loader.add_value("html", response.text)

            json_data = response.meta.get("json_data", {})
            if json_data:
                i = json_data

                # Basic info
                loader.add_value("title", i["post"]["post_title"])
                loader.add_value("property_id", i["overlay"]["property_id"])

                # Prices
                if "IDR" in i["overlay"]["prices"]:
                    loader.add_value("price", i["overlay"]["prices"]["IDR"]["price"])
                    loader.add_value("currency", "IDR")
                if "USD" in i["overlay"]["prices"]:
                    loader.add_value("price", i["overlay"]["prices"]["USD"]["price"])
                    loader.add_value("currency", "USD")

                # Images
                if i["overlay"]["images"]:
                    loader.add_value(
                        "image_url",
                        i["overlay"]["images"][0],
                        MapCompose(dimension_remover),
                    )

                # List date
                loader.add_value(
                    "list_date",
                    i["post"]["post_date"],
                    MapCompose(to_mmddyy),
                )

                # Location and sizes
                loader.add_value("location", i["overlay"]["area"])
                loader.add_value(
                    "land_size",
                    i["overlay"]["area_size"],
                    MapCompose(lambda value: value.replace(",", ".")),
                )
                loader.add_value(
                    "build_size",
                    i["overlay"]["building_size"],
                    MapCompose(lambda value: value.replace(",", ".")),
                )

                # Rooms
                loader.add_value("bedrooms", i["overlay"]["bedrooms"])
                loader.add_value(
                    "bathrooms",
                    i["overlay"]["bathrooms"],
                    MapCompose(lambda value: value.replace(",", ".")),
                )

                # Availability
                availability = "Sold" if i["overlay"]["is_sold"] else "Available"
                loader.add_value("availability_label", availability)

                # Contract and property type
                contract_type = i["overlay"]["property_status"]
                property_type = (
                    i.get("overlay", {}).get("property_type", "").split(",")[0]
                )
                loader.add_value("contract_type", contract_type)
                loader.add_value("property_type", property_type)

                # Description
                desc = md_converter.handle(i["post"]["post_content"])
                loader.add_value("description", desc)

                # Leasehold years
                if "Leasehold" in contract_type:
                    loader.add_value("leasehold_years", i["overlay"]["expiration"])

            item = loader.load_item()

            # Additional processing
            if not item.get("location"):
                if result := re.search(
                    r"in (?P<location>[A-Za-z ]+)", item.get("title", "")
                ):
                    item["location"] = result.group("location")

            if not item.get("leasehold_years") and "Leasehold" in item.get(
                "contract_type", ""
            ):
                item["leasehold_years"] = find_lease_years(item.get("description", ""))

            yield item

        except Exception as err:
            error = Error(
                url=response.url,
                source="Spider",
                error_message=str(err),
            )
            tb = traceback.format_exc()
            error.error_message += f"\nTraceback:\n{tb}"
            db = next(get_db())
            db.add(error)
            db.commit()
