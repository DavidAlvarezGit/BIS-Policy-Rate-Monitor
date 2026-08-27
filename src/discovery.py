from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests

def discover_policy_rates_url(
    page_url: str
) -> str:
    response = requests.get(page_url, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    for link in soup.find_all('a', href=True):
        text = link.get_text(" ", strip=True).casefold()
        if all(term in text for term in ("central bank policy rates", "csv", "flat")):
            return urljoin(page_url, link['href'])
    raise ValueError("Could not find the BIS policy rates CSV download link.")