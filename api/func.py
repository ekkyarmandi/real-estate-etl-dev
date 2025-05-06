import re
from datetime import datetime as dt


def get_domain(url: str) -> str | None:
    if not url:
        return None
    if result := re.search(r"http[s]://(.*?)/", url):
        return result.group(1)
    return None


def convert_dates_in_item(item):
    """
    Converts date fields in item to '%b/%y' format.
    Handles int (timestamp in seconds or ms) and datetime objects.
    """
    date_keys = [
        "Sold Date",
        "List Date",
        "Scrape Date",
    ]
    for key in date_keys:
        date_value = item.get(key)
        if date_value:
            if isinstance(date_value, int):
                try:
                    new_date = dt.fromtimestamp(date_value)
                    item[key] = new_date.strftime("%b/%y")
                except ValueError:
                    new_date = dt.fromtimestamp(date_value / 1000)
                    item[key] = new_date.strftime("%b/%y")
            elif isinstance(date_value, dt):
                item[key] = date_value.strftime("%b/%y")
    return item
