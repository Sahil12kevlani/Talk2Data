from fastapi import APIRouter, Depends
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.concurrency import run_in_threadpool
from app.db.database import get_db
from app.utils.config import settings
from app.utils.schema_extractor import get_dynamic_schema_text
import time

router = APIRouter()

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.groq_api_key
)

_cached_schema = {"data": None, "hash": None, "last_updated": 0}

async def get_cached_schema(db: Session, refresh_interval=60):
    """Fetch and cache schema, refresh if changed or expired."""
    now = time.time()

    # Get fresh schema and hash
    schema_data = await run_in_threadpool(get_dynamic_schema_text, db)
    schema_hash = schema_data["hash"]

    # Refresh cache only if hash changed or expired
    if (
        _cached_schema["data"]
        and _cached_schema["hash"] == schema_hash
        and now - _cached_schema["last_updated"] < refresh_interval
    ):
        return _cached_schema["data"]

    _cached_schema.update({
        "data": schema_data,
        "hash": schema_hash,
        "last_updated": now
    })

    return schema_data


@router.post("/test-sql")
async def test_sql(query: str, db: Session = Depends(get_db)):
    try:
        # 1️⃣ Fetch schema (cached intelligently)
        schema_info = await get_cached_schema(db)

        # 2️⃣ Generate SQL using Groq
        completion = await run_in_threadpool(
            lambda: client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": f"{schema_info['text']} (schema version: {schema_info['hash'][:8]})"},
                    {"role": "user", "content": f"Convert this to SQL: {query}"}
                ],
                temperature=0.2
            )
        )

        sql_query = completion.choices[0].message.content.strip()
        sql_query = (
            sql_query.replace("```sql", "")
                    .replace("```", "")
                    .replace("\n", " ")
                    .strip()
        )

        # 3️⃣ Execute SQL safely
        def execute_query():
            result = db.execute(text(sql_query))
            return result.fetchall()

        rows = await run_in_threadpool(execute_query)
        formatted = [dict(row._mapping) for row in rows]

        return {
            "status": "success",
            "query_analysis": {
                "input": query,
                "generated_sql": sql_query
            },
            "data": formatted,
            "meta": {
                "rows_returned": len(rows),
                "schema_version": schema_info["hash"][:8]
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "query_analysis": {"input": query},
            "error_details": {"message": str(e), "type": type(e).__name__}
        }
