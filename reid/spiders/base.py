import scrapy
import traceback
from models.error import Error
from reid.database import get_db


class BaseSpider(scrapy.Spider):
    scraped_at = None
    existing_urls = []
    visited = []

    def handle_error(self, failure):
        if failure.value.response.status == 302:
            print(failure.value.response.url)
            return
        if 400 <= failure.value.response.status < 500:
            self.logger.error(f"Request failed: {failure.request.url}")
            error = Error(
                url=failure.request.url,
                error_message=str(failure.value),
            )
            # Capture the traceback and add it to the error message
            tb = traceback.format_exc()
            error.error_message += f"\nTraceback:\n{tb}"
            db = next(get_db())
            db.add(error)
            db.commit()
