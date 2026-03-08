# Account Intelligence Radar

## Overview

This project builds an automated **company intelligence report generator** using LLMs.

The system collects information about companies from the web and generates structured business intelligence reports.

Pipeline:

Search → Crawl → Extract → LLM Analysis → Structured JSON → Markdown Report

## Technologies Used

* Python
* SerpAPI (Google Search)
* Firecrawl.dev (Web scraping)
* OpenRouter LLM
* JSON structured outputs

## Project Structure

app/

* main.py → main pipeline
* serp_search.py → search company pages
* free_extractor.py → extract web content
* analyzer.py → analyze using LLM
* report_builder.py → generate markdown reports

outputs/

* JSON structured company data
* Markdown intelligence reports

## How to Run

Install dependencies:

pip install -r requirements.txt

Add API keys in `.env`

SERPAPI_KEY=your_key
FIRECRAWL_KEY=your_key
OPENROUTER_API_KEY=your_key

Run:

python app/main.py

## Output

The system generates:

* Structured JSON company profiles
* Markdown intelligence reports

Example companies analyzed:

* Alfanar
* Aramco
* STC
