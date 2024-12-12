# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

# import sqlite3
# from datetime import datetime

from scrapy.exceptions import DropItem
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from decouple import config
import uuid

from reid.models import RawData, PropertyData, PropertyRecord

engine = create_engine(config("DB_URL"), echo=True)
Session = sessionmaker(bind=engine)

session = Session()


class PropertyDataPipelines:

    def __init__(self):
        self.create_enumeration_if_not_exists()
        self.create_table_if_not_exist()

    def db_execute(self, query):
        try:
            session.execute(text(query))
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            print(f"An error occurred: {str(e)}")

    def create_enumeration_if_not_exists(self):
        q = "CREATE TYPE currency AS ENUM ('IDR','USD');"
        self.db_execute(q)

    def create_table_if_not_exist(self):
        q = """
        CREATE TABLE IF NOT EXISTS properties (
            url TEXT PRIMARY KEY,
            scraped_at TIMESTAMP,
            sold_at TIMESTAMP,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            source TEXT,
            property_id TEXT,
            listed_date TEXT,
            title TEXT,
            region TEXT,
            location TEXT,
            contract_type TEXT, -- TODO: add enumeration to this too
            property_type TEXT,
            leasehold_years DECIMAL(10,1),
            bedrooms INTEGER,
            bathrooms INTEGER,
            land_size INTEGER,
            build_size INTEGER,
            price INTEGER,
            currency currency DEFAULT 'USD',
            image_url TEXT,
            is_available BOOLEAN,
            availability_label TEXT,
            description TEXT,
            is_off_plan BOOLEAN
        );
        """
        self.db_execute(q)

    def process_item(self, item, spider):
        url = item["url"]
        record = session.query(PropertyData).get(url)
        if not record:
            item.pop("id")
            # create new record if not exists
            new_record = PropertyData(**item)
            session.add(new_record)
        else:
            # update record if exists
            new_record_availability = item.get("availability_label")
            if new_record_availability == "Available":
                # update property price
                new_record_price = item.get("price", 0)
                if new_record_price > 0 and new_record_price != record.price:
                    record.price = new_record_price
                # update property type
                record.property_type = item.get("property_type", "")
                # update the availability status and label
                record.availability_label = new_record_availability
                record.is_available = 1
                record.sold_at = None
            else:
                # update the availability status and label
                record.is_available = 0
                record.availability_label = new_record_availability
                record.sold_at = item["scraped_at"]

        # commit the process
        try:
            session.commit()
        except SQLAlchemyError as e:
            DropItem(f"{item['url']} already exist")
            session.rollback()
            print(f"An error occurred: {str(e)}")
        return item


class PropertyRecordPipelines:

    def __init__(self):
        self.create_enumeration_if_not_exists()
        self.create_table_if_not_exist()

    def db_execute(self, query):
        try:
            session.execute(text(query))
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            print(f"An error occurred: {str(e)}")

    def create_enumeration_if_not_exists(self):
        q = "CREATE TYPE currency AS ENUM ('IDR','USD');"
        self.db_execute(q)

    def create_table_if_not_exist(self):
        q = """
        CREATE TABLE IF NOT EXISTS records (
            id UUID PRIMARY KEY,
            url TEXT,
            scraped_at TIMESTAMP,
            sold_at TIMESTAMP,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            source TEXT,
            property_id TEXT,
            listed_date TEXT,
            title TEXT,
            region TEXT,
            location TEXT,
            contract_type TEXT, -- TODO: add enumeration to this too
            property_type TEXT,
            leasehold_years DECIMAL(10,1),
            bedrooms INTEGER,
            bathrooms INTEGER,
            land_size INTEGER,
            build_size INTEGER,
            price INTEGER,
            currency currency DEFAULT 'USD',
            image_url TEXT,
            is_available BOOLEAN,
            availability_label TEXT,
            description TEXT,
            is_off_plan BOOLEAN,
            raw_data_id UUID NOT NULL REFERENCES raw_data(id) ON DELETE CASCADE
        );
        """
        self.db_execute(q)

    def process_item(self, item, spider):
        availability = item.get("availability_label", "Available")
        new_record = PropertyRecord(
            id=uuid.uuid4(),
            raw_data_id=item["id"],
            url=item["url"],
            source=item["source"],
            scraped_at=item.get("scraped_at", None),
            property_id=item.get("property_id", None),
            listed_date=item.get("listed_date", None),
            title=item.get("title", None),
            region=item.get("region", None),
            location=item.get("location", None),
            contract_type=item.get("contract_type", None),
            property_type=item.get("property_type", None),
            leasehold_years=item.get("leasehold_years", None),
            bedrooms=item.get("bedrooms", None),
            bathrooms=item.get("bathrooms", None),
            land_size=item.get("land_size", None),
            build_size=item.get("build_size", None),
            price=item.get("price", 0),
            currency=item.get("currency", "USD"),
            image_url=item.get("image_url", None),
            is_available=availability == "Available",
            availability_label=availability,
            description=item.get("description", None),
            is_off_plan=item.get("is_off_plan", False),
        )
        session.add(new_record)
        try:
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            print(f"An error occurred: {str(e)}")
        return item


class RawDataPipelines:

    def __init__(self):
        self.create_table_if_not_exist()

    def create_table_if_not_exist(self):
        q = """
        CREATE TABLE IF NOT EXISTS raw_data (
            created_at TIMESTAMP,
            id UUID PRIMARY KEY,
            url TEXT NOT NULL,
            html TEXT,
            json TEXT
        );
        """
        # execute create tables above
        try:
            session.execute(text(q))
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            print(f"An error occurred: {str(e)}")

    def process_item(self, item, spider):
        record_id = uuid.uuid4()
        new_record = RawData(
            id=record_id,
            url=item.get("url"),
            html=item.get("html"),
            json=item.get("json"),
        )
        session.add(new_record)
        try:
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            print(f"An error occurred: {str(e)}")
        item.pop("html")
        item["id"] = record_id
        return item
