from reid.database import get_db
from models.property import Property
from scrapy.loader import ItemLoader
from reid.items import PropertyItem
from itemloaders.processors import MapCompose
from scrapy.selector import Selector


class UbudPropertyExtractor:
    name = "ubudproperty"
    source = "Ubud Property"

    def __init__(self):
        self.db = next(get_db())

    def extract(self):
        properties = (
            self.db.query(Property)
            .filter(Property.source == self.source)
            .filter(Property.tags.any())
            .all()
        )
        for property in properties:
            response = Selector(text=property.rawdata.html)
            loader = ItemLoader(item=PropertyItem(), selector=response)
            loader.add_css("description", "div#ENG ::Text,div.sideDetail table ::Text")
            item = loader.load_item()
            if item.get("description"):
                property.description = item.get("description")
                property.define_land_zoning()
                property.identify_issues()
                self.db.commit()
                self.db.refresh(property)
        return properties
