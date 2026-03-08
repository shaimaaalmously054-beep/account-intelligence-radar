import json
import os

def save_json(data, company):

    os.makedirs("outputs", exist_ok=True)

    with open(f"outputs/{company}.json","w") as f:

        json.dump(data,f,indent=2)


def save_markdown(data, company):

    content = f"# {data.get('company_name')}\n\n"

    content += f"## Headquarters\n{data.get('headquarters')}\n\n"

    content += "## Business Units\n"

    for b in data.get("business_units",[]):
        content += f"- {b}\n"

    content += "\n## Products and Services\n"

    for p in data.get("products_services",[]):
        content += f"- {p}\n"

    content += "\n## Executives\n"

    for e in data.get("executives",[]):
        content += f"- {e['name']} — {e['title']}\n"

    content += "\n## Strategic Initiatives\n"

    for s in data.get("strategic_initiatives",[]):
        content += f"- {s}\n"

    content += "\n## Sources\n"

    for s in data.get("sources",[]):
        content += f"- {s}\n"

    with open(f"outputs/{company}.md","w",encoding="utf-8") as f:
        f.write(content)