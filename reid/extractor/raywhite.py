from reid.database import get_db
from sqlalchemy import text
from models.property import Property
from scrapy.loader import ItemLoader
from reid.func import identify_currency
from reid.items import PropertyItem
from itemloaders.processors import MapCompose
from scrapy.selector import Selector
import jmespath
import json


class RayWhiteExtractor:
    name = "raywhite"
    source = "Ray White Indonesia"

    def __init__(self):
        self.db = next(get_db())

    def extract(self):
        properties = (
            self.db.query(Property)
            .filter(Property.source == self.source)
            .filter(Property.created_at >= "2025-03-01")
            .filter(Property.price < 1000)
            .all()
        )
        for property in properties:
            response = Selector(text=property.rawdata.html)
            loader = ItemLoader(item=PropertyItem(), selector=response)
            script = response.css("script[type='application/ld+json']::text").get()
            loader.add_css("currency", "#price", MapCompose(identify_currency))
            if script:
                d = json.loads(script)
                loader.add_value("price", jmespath.search("offers.price", d))
            prices = loader.get_collected_values("price")
            currencies = loader.get_collected_values("currency")
            if len(prices) > 0 and len(currencies) > 0:
                price = prices[0]
                if price < 1000:
                    loader.replace_css("price", "#price")
            item = loader.load_item()
            ## update listing and property
            property.price = item.get("price")
            property.currency = item.get("currency", "IDR")
            self.db.commit()
            self.db.refresh(property)
            listing_item = {
                "url": property.url,
                "price": item.get("price"),
                "currency": item.get("currency", "IDR"),
            }
            query = text(
                """
                UPDATE listing
                SET price = :price, currency = :currency
                WHERE url = :url
            """
            )
            self.db.execute(query, listing_item)
            self.db.commit()


if __name__ == "__main__":
    extractor = RayWhiteExtractor()
    extractor.extract()
