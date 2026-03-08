from dotenv import load_dotenv
load_dotenv()

from serp_search import search_company
from free_extractor import extract_company_data
from analyzer import analyze_company
from report_builder import save_json, save_markdown

company = input("Company name: ")

objective = """
Extract headquarters, business units, products and services,
target industries, key executives and strategic initiatives.
Return structured JSON.
"""

results = search_company(company)

clean_urls = [r["link"] for r in results[:5]]

clean_urls = [u for u in clean_urls if "linkedin.com" not in u]

print("Sources:", clean_urls)

pages = extract_company_data(clean_urls)

structured_data = analyze_company(company, pages, objective)

save_json(structured_data, company)
save_markdown(structured_data, company)

print("Report generated.")