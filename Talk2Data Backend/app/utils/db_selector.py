from openai import OpenAI
from app.utils.config import settings

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.groq_api_key
)

# A lightweight prompt for database selection
def select_databases(query: str, database_summaries: dict):
    system_prompt = (
        "You are a database selector. Given a user query and a list of databases with their purposes, "
        "decide which databases are relevant to answer the question. "
        "Return a JSON array of database names only."
    )

    db_summary_text = "\n".join([
    f"- {name}: {desc[:2000]}"  # truncate to 2K chars per DB to avoid prompt overflow
    for name, desc in database_summaries.items()
    ])


    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Databases:\n{db_summary_text}\n\nQuery: {query}"}
        ],
        temperature=0
    )

    import json
    try:
        selected = json.loads(completion.choices[0].message.content)
        return [db for db in selected if db in database_summaries]
    except Exception:
        return []
