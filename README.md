# Account Intelligence Radar

## Overview

Account Intelligence Radar is an automated **company intelligence analysis tool** that collects public information from the web and generates structured business reports using Large Language Models (LLMs).

The system searches for company information, extracts content from relevant web pages, analyzes it using an LLM, and generates structured outputs including JSON data and Markdown reports.

This project demonstrates a full **LLM-powered data pipeline**.

---

## System Architecture

The pipeline follows these steps:

1. **Search (SerpAPI)**
   Retrieves relevant company pages from Google search results.

2. **Extraction (Firecrawl / Web Scraping)**
   Extracts structured text from the discovered web pages.

3. **LLM Analysis (OpenRouter API)**
   The extracted content is analyzed using an LLM to identify key company information.

4. **Structured Data Generation**
   The LLM outputs structured data in JSON format.

5. **Report Generation**
   The JSON data is converted into a readable Markdown intelligence report.

---

## Pipeline Flow

Search → Extract → Analyze → JSON → Markdown Report

---

## Project Structure

```
account-intelligence-radar
│
├── app
│   ├── main.py                # Main pipeline controller
│   ├── serp_search.py         # Search company information
│   ├── free_extractor.py      # Extract content from web pages
│   ├── analyzer.py            # LLM analysis module
│   └── report_builder.py      # Generate Markdown reports
│
├── outputs                    # Generated reports
│   ├── alfanar.json
│   ├── alfanar.md
│   ├── Aramco.json
│   ├── Aramco.md
│   ├── stc.json
│   └── stc.md
│
├── .env.example               # Example environment variables
├── requirements.txt           # Project dependencies
└── README.md
```

---

## Technologies Used

* **Python**
* **SerpAPI** – Google Search API
* **Firecrawl / Web scraping**
* **OpenRouter API**
* **Large Language Models (LLMs)**
* **JSON structured outputs**

---

## Installation

Clone the repository:

```
git clone https://github.com/shaimaaalmously054-beep/account-intelligence-radar.git
cd account-intelligence-radar
```

Install dependencies:

```
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file and add your API keys:

```
SERPAPI_KEY=your_serpapi_key
FIRECRAWL_KEY=your_firecrawl_key
OPENROUTER_API_KEY=your_openrouter_key
```

---

## Running the Project

Run the main pipeline:

```
python app/main.py
```

The system will:

1. Search for company information
2. Extract content from web pages
3. Analyze the information using an LLM
4. Generate structured outputs

---

## Output

The project generates two types of outputs:

### JSON Output

Structured company intelligence data.

Example:

```
{
  "company_name": "Alfanar",
  "headquarters": "Riyadh, Saudi Arabia",
  "business_units": [...],
  "products_services": [...],
  "executives": [...],
  "strategic_initiatives": [...]
}
```

### Markdown Report

Human-readable company intelligence reports.

Example:

```
# Alfanar

## Headquarters
Riyadh, Saudi Arabia

## Business Units
- Construction
- Energy
- Electrical Manufacturing

## Products and Services
- Electrical systems
- Renewable energy solutions

## Strategic Initiatives
- Renewable energy expansion
```

---

## Example Companies Analyzed

* Alfanar
* Saudi Aramco
* STC (Saudi Telecom Company)

---

## Learning Objectives

This project demonstrates:

* Building an **LLM-powered information extraction pipeline**
* Using **web search APIs**
* Automating **company intelligence analysis**
* Generating **structured AI outputs**
* Integrating multiple APIs into a single workflow

---

## Future Improvements

Possible improvements for the system:

* Add vector database (RAG architecture)
* Improve source ranking and filtering
* Add automated company comparison
* Build a simple web interface

---

## License

This project is for educational purposes.
