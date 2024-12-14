from models.listing import Listing
from reid.database import get_db
from models.property import Property
from models.rawdata import RawData
from models.error import Error
from models.report import Report
from scrapy.exceptions import DropItem
from datetime import datetime


class RawDataPipeline:
    def __init__(self):
        self.source = None
        self.scraped_at = None

    def process_item(self, item, spider):
        self.source = item["source"]
        self.scraped_at = item["scraped_at"]
        # store raw data
        db = next(get_db())
        raw_data_item = dict(
            url=item["url"],
            html=item.get("html", ""),
            json=item.get("json", ""),
        )
        raw_data = RawData(**raw_data_item)
        db.add(raw_data)
        db.commit()
        item = dict(item)
        item["raw_data_id"] = raw_data.id
        return item

    def close_spider(self, spider):
        # get spider stats
        stats = spider.crawler.stats.get_stats()
        # create spider report
        start_time = stats.get("start_time", 0)
        elapsed_time = datetime.now(start_time.tzinfo) - start_time
        spider_stats = dict(
            source=self.source,
            scraped_at=self.scraped_at,
            item_scraped_count=stats.get("item_scraped_count", 0),
            item_dropped_count=stats.get("item_dropped_count", 0),
            response_error_count=stats.get("log_count/ERROR", 0),
            elapsed_time_seconds=elapsed_time.total_seconds(),
        )
        # with open("spider_stats.txt", "w") as f:
        #     f.write(str(spider_stats))
        report = Report(**spider_stats)
        db = next(get_db())
        db.add(report)
        db.commit()


class PropertyPipeline:
    def process_item(self, item, spider):
        # remove unnecessary fields after raw data
        item.pop("html", None)
        item.pop("json", None)
        # modify item to match property model
        if item.get("availability_label"):
            item["availability"] = item.pop("availability_label")
            item["is_available"] = item["availability"] == "Available"

        try:
            db = next(get_db())
            property = Property(**item)
            property.check_off_plan()
            property.define_land_zoning()  # this will applied to Land property type only
            db.add(property)
            db.commit()
            db.refresh(property)
            property.identify_issues()
            item["land_zoning"] = property.land_zoning
        except Exception as e:
            db.rollback()
            # record error
            error = Error(
                url=item.get("url"),
                error_message=str(e),
            )
            db.add(error)
            db.commit()
            # delete raw data
            raw_data_id = item.get("raw_data_id", None)
            if raw_data_id:
                raw_data = db.query(RawData).filter(RawData.id == raw_data_id).first()
                if raw_data:
                    db.delete(raw_data)
                    db.commit()
            # drop the item
            raise DropItem(f"Error on PropertyPipeline insertion: {e}")
        item.pop("id", None)
        return item


class ListingPipeline:
    def process_item(self, item, spider):
        # remove raw_data_id
        item.pop("raw_data_id", None)
        # add listing to db
        db = next(get_db())
        listing = Listing(**item)
        listing.classify_tab()
        listing.reid_id_generator(db)
        try:
            db.add(listing)
            db.commit()
            # remove error related to the listing if exists
            db.query(Error).filter(Error.url == item.get("url")).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            # on constraint conflict do update
            url = item.get("url")
            item["updated_at"] = datetime.now()
            existing_listing = db.query(Listing).filter(Listing.url == url).first()
            any_changes = existing_listing.compare(item)
            if any_changes:
                existing_listing.classify_tab()
                db.commit()
        return item
