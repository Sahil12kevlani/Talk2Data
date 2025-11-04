from fastapi import APIRouter
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.concurrency import run_in_threadpool
from app.utils.db_selector import select_databases
from app.utils.schema_extractor import get_dynamic_schema_text
from app.utils.semantic_selector import select_databases_by_embedding, build_index
from app.db.multidb_manager import get_db_session, DATABASES
from app.utils.config import settings
from openai import OpenAI
import json
import re
import time

router = APIRouter()
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=settings.groq_api_key)

# Cache per DB
_schema_cache = {}


# -------------------------- SCHEMA CACHE --------------------------
async def get_cached_schema(db_name: str, db: Session, refresh_interval=60):
    now = time.time()
    schema_data = await run_in_threadpool(get_dynamic_schema_text, db)
    schema_hash = schema_data["hash"]

    if (
        db_name in _schema_cache
        and _schema_cache[db_name]["hash"] == schema_hash
        and now - _schema_cache[db_name]["last_updated"] < refresh_interval
    ):
        return _schema_cache[db_name]["data"]

    _schema_cache[db_name] = {
        "data": schema_data,
        "hash": schema_hash,
        "last_updated": now,
    }
    return schema_data


# -------------------------- SCHEMA SUMMARIES --------------------------
async def build_dynamic_db_summaries(max_lines_per_db: int = 50):
    """Generate lightweight schema summaries for all available databases."""
    summaries = {}

    for db_name in DATABASES.keys():
        session_gen = get_db_session(db_name)
        db = next(session_gen)
        try:
            schema_info = await run_in_threadpool(get_dynamic_schema_text, db)
            text_summary = schema_info.get("text", "")
            lines = text_summary.splitlines()[:max_lines_per_db]
            summaries[db_name] = "\n".join(lines)
        except Exception as ex:
            summaries[db_name] = f"(failed to introspect schema: {type(ex).__name__}: {str(ex)})"
        finally:
            db.close()

    print("=== DYNAMIC SUMMARIES ===")
    for name, txt in summaries.items():
        print(f"\n{name.upper()}:\n{txt}\n---")

    return summaries


# -------------------------- MERGE LAYER --------------------------
def merge_results_across_dbs(results: dict):
    """
    Merge results across multiple databases intelligently by matching common keys (DishName, DishCode, etc.)
    """
    if not results or len(results) <= 1:
        return None  # No merging needed if only one DB

    merged = {}
    for db_name, data in results.items():
        for row in data["rows"]:
            # Choose best key to merge by
            key = row.get("DishName") or row.get("DishCode") or row.get("DishID")
            if not key:
                continue

            if key not in merged:
                merged[key] = {"_source_dbs": [db_name]}
            else:
                merged[key]["_source_dbs"].append(db_name)

            # Merge fields (without overwriting existing)
            for k, v in row.items():
                if k not in merged[key] or merged[key][k] in (None, "", "N/A"):
                    merged[key][k] = v

    # Flatten merged data
    return list(merged.values())


# -------------------------- MAIN ROUTE --------------------------
@router.post("/multi-db-query")
async def multi_db_query(query: str):
    try:
        # 🧠 Ensure vector index is built before using it
        build_index(force=True)

        # 1️⃣ Select relevant databases using semantic similarity
        selected_dbs = select_databases_by_embedding(query)
        if not selected_dbs:
            return {"status": "error", "message": "No relevant database found."}

        results = {}

        # 2️⃣ Generate SQL for each relevant DB
        for db_name in selected_dbs:
            session_gen = get_db_session(db_name)
            db = next(session_gen)

            schema_info = await get_cached_schema(db_name, db)
            schema_text = schema_info["text"]

            # 💡 Better prompting for Groq model
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are a highly skilled SQL generator. You are working with the database '{db_name}'.\n\n"
                        "Below is the **live schema** of the database (Microsoft SQL Server syntax):\n"
                        f"{schema_text}\n\n"
                        "Your task: write an accurate SQL SELECT query that answers the user's request.\n"
                        "⚙️ RULES:\n"
                        "- Only use columns and tables that are present in the schema above.\n"
                        "- Always double-check column names and relationships before using them.\n"
                        "- Prefer JOINs where foreign keys exist.\n"
                        "- Do NOT invent or assume column names.\n"
                        "- If you cannot find the necessary columns, output exactly: SELECT 1 AS no_data;"
                    ),
                },
                {
                    "role": "user",
                    "content": f"User request: {query}\nGenerate the most appropriate SQL query using tables in '{db_name}'.",
                },
            ]

            # Call Groq model
            completion = await run_in_threadpool(lambda: client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # ✅ more accurate Groq model
                messages=messages,
                temperature=0.3,
            ))

            sql_query = (
                completion.choices[0].message.content
                .replace("```sql", "")
                .replace("```", "")
                .strip()
            )

            sql_query = " ".join(sql_query.replace("\n", " ").replace("\r", " ").replace("\t", " ").split())

            # 3️⃣ Execute query safely
            def execute_query():
                if not sql_query.strip().lower().startswith("select"):
                    raise ValueError(f"Invalid SQL generated for {db_name}: {sql_query}")

                def fix_sql_syntax_for_mssql(sql: str) -> str:
                    """
                    Automatically fix known SQL generation errors such as subquery type mismatches
                    and schema prefix issues.
                    """
                    # 🩹 1. Fix varchar-int mismatch (DishCode vs DishID)
                    sql = re.sub(
                        r"dm\.DishCode\s*=\s*\(SELECT\s+DishID\s+FROM\s+dishes\s+WHERE\s+DishName\s*=\s*dm\.DishName\)",
                        "dm.DishCode = d.DishCode",
                        sql,
                        flags=re.IGNORECASE,
                    )

                    # 🩹 2. Also handle alias form (SELECT d.DishID FROM dishes d)
                    sql = re.sub(
                        r"dm\.DishCode\s*=\s*\(SELECT\s+d\.DishID\s+FROM\s+dishes\s+d\s+WHERE\s+d\.DishName\s*=\s*dm\.DishName\)",
                        "dm.DishCode = d.DishCode",
                        sql,
                        flags=re.IGNORECASE,
                    )

                    # 🩹 3. Fix for accidental DishCode-to-DishID joins (common AI mistake)
                    sql = re.sub(
                        r"ON\s+dm\.DishCode\s*=\s*ni\.DishID",
                        "ON d.DishID = ni.DishID",
                        sql,
                        flags=re.IGNORECASE,
                    )

                    # 🩹 4. Add schema prefixes for cross-database queries
                    sql = sql.replace("talk2data.", "talk2data.dbo.")
                    sql = sql.replace("fooddb.", "fooddb.dbo.")

                    # 🩹 5. Cleanup double spaces / formatting
                    sql = " ".join(sql.split())

                    return sql


                fixed_sql = fix_sql_syntax_for_mssql(sql_query)
                result = db.execute(text(fixed_sql))
                if result.returns_rows:
                    return result.fetchall()
                return []

            rows = await run_in_threadpool(execute_query)
            formatted = [dict(row._mapping) for row in rows]

            results[db_name] = {
                "generated_sql": sql_query,
                "rows": formatted,
                "rows_returned": len(formatted),
                "schema_version": schema_info["hash"][:8],
            }

            db.close()

        # 4️⃣ Merge data across DBs intelligently
        merged_output = merge_results_across_dbs(results)

        if all(len(v["rows"]) == 0 for v in results.values()):
         return {
        "status": "success",
        "input": query,
        "selected_databases": selected_dbs,
        "results": results,
        "merged_results": [],
        "merge_reasoning": "No matching records found in any selected databases."
    }

        # 5️⃣ Optional: attempt a second-pass reasoning for multi-DB merge
        if merged_output is None or len(merged_output) == 0:
            try:
                cross_prompt = f"""
                You are an AI SQL analyst. The following results came from multiple databases:
                {json.dumps({db: res['generated_sql'] for db, res in results.items()}, indent=2)}
                User query: {query}
                Suggest how to logically merge the data (for example, by DishName, SupplierID, or FacultyID).
                Return only a conceptual merge description (not SQL).
                """
                merge_reasoning = await run_in_threadpool(lambda: client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": cross_prompt}],
                    temperature=0.2,
                ))
                merged_suggestion = merge_reasoning.choices[0].message.content.strip()
            except Exception as merge_ex:
                merged_suggestion = f"(merge reasoning failed: {merge_ex})"
        else:
            merged_suggestion = "(auto-merged successfully)"

        # ✅ 6️⃣ Return response
        return {
            "status": "success",
            "input": query,
            "selected_databases": selected_dbs,
            "results": results,
            "merged_results": merged_output or [],
            "merge_reasoning": merged_suggestion,
        }

    except Exception as e:
        return {"status": "error", "message": str(e), "type": type(e).__name__}
