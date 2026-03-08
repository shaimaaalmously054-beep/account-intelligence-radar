import requests
from bs4 import BeautifulSoup

def extract_company_data(urls):

    pages = []

    for url in urls:
        try:

            r = requests.get(url, timeout=15)

            soup = BeautifulSoup(r.text, "html.parser")

            text = soup.get_text(" ", strip=True)

            pages.append({
                "url": url,
                "content": text[:3000]
            })

        except Exception as e:

            print("Error scraping:", url)

    return pages