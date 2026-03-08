from openai import OpenAI
import os
import json
import re
from dotenv import load_dotenv

load_dotenv() 

def analyze_company(company, pages, objective):
    combined_text = ""

    for p in pages:
        combined_text += f"\nSOURCE: {p['url']}\n{p['content']}\n"

    prompt = f"""
You are a research analyst.

Company: {company}

Objective:
{objective}

Return ONLY valid JSON. No explanations, no markdown, no code blocks, no ```json.

Output **pure JSON only**. Start directly with {{ and end with }}.

Schema (follow exactly):

{{
  "company_name": "",
  "headquarters": "",
  "business_units": [],
  "products_services": [],
  "target_industries": [],
  "executives": [{{"name": "","title": ""}}],
  "strategic_initiatives": [],
  "sources": []
}}

Sources:
{combined_text}
""".strip()
    
    client = OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )

    try:
        response = client.chat.completions.create(
            model="openrouter/free",  # ← نموذج مجاني قوي، غيّره حسب الحاجة
            # أو جرب: "qwen/qwen3-coder:free" أو "google/gemma-3-27b-it:free"
            # أو "openrouter/free" لاختيار تلقائي

            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"},  
            extra_headers={
                "HTTP-Referer": "https://your-app.com",           
                "X-Title": "Company Analysis Tool"               
            }
        )

        content = response.choices[0].message.content.strip()

        return json.loads(content)

    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        print("Invalid JSON received:\n", content)
        return {"error": "Invalid JSON", "raw": content}

    except Exception as e:
        print("OpenRouter API error:", str(e))
        return {"error": str(e)}