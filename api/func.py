import re


def get_domain(url: str) -> str | None:
    if not url:
        return None
    if result := re.search(r"http[s]://(.*?)/", url):
        return result.group(1)
    return None
