from fastapi import APIRouter, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.concurrency import run_in_threadpool
from app.utils.db_selector import select_databases
from app.utils.schema_extractor import get_dynamic_schema_text
from app.utils.semantic_selector import select_databases_by_embedding, build_index
from app.db.multidb_manager import get_db_session, DATABASES
from app.utils.config import settings
from openai import OpenAI
from datetime import datetime, date
from decimal import Decimal
import json, time, uuid, re

router = APIRouter()
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=settings.groq_api_key)

# -------------------- GLOBAL CACHES --------------------
_schema_cache = {}
_sessions = {}  # {session_id: {"history": [{"role":..., "content":...}, ...]}}

# -------------------- SESSION UTILS --------------------
def get_or_create_session(session_id: str | None):
    """Return session dict; create if needed."""
    if not session_id:
        session_id = str(uuid.uuid4())
    if session_id not in _sessions:
        _sessions[session_id] = {"history": []}
    return session_id, _sessions[session_id]


# ✅ --- CHANGED SECTION 1: REDUCED CHAT HISTORY ---
def add_message(session_id: str, role: str, content: str):
    """Append message to a session with trimming."""
    sess = _sessions.setdefault(session_id, {"history": []})
    sess["history"].append({"role": role, "content": content})
    # Limit memory to 3 user/AI pairs (6 messages) instead of 10
    sess["history"] = sess["history"][-6:]


# -------------------- SCHEMA CACHE --------------------
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


# -------------------- MERGE LAYER --------------------
def merge_results_across_dbs(results: dict):
    if not results or len(results) <= 1:
        return None
    db_columns = [set(row.keys()) for res in results.values() if res["rows"] for row in res["rows"][:1]]
    common_cols = set.intersection(*db_columns) if db_columns else set()
    possible_keys = ["DishName", "DishCode", "DishID", "SupplierName", "ArticleNumber", "CuisineName", "ProductName"]
    key = next((k for k in possible_keys if k in common_cols), None)
    if not key and db_columns:
        key = list(next(iter(db_columns)))[0]
    if not key:
        return None
    merged = {}
    for db_name, data in results.items():
        for row in data["rows"]:
            mk = row.get(key)
            if not mk:
                continue
            if mk not in merged:
                merged[mk] = {"_source_dbs": {db_name}, **row}
            else:
                merged[mk]["_source_dbs"].add(db_name)
                for k, v in row.items():
                    if k not in merged[mk] or merged[mk][k] in (None, "", "N/A"):
                        merged[mk][k] = v
    flat = []
    for val in merged.values():
        val["_source_dbs"] = list(val["_source_dbs"])
        flat.append(val)
    return flat


# ✅ --- CHANGED SECTION 2: STRICTER SYSTEM PROMPT ---
# This new prompt forbids SELECT * and bad UNIONs to fix your SQL error
SYSTEM_PROMPT = """
You are an intelligent SQL and data analysis assistant for MS SQL Server.

You must:
- Focus strictly on questions related to available data, databases, or analytics.
- Politely refuse irrelevant or personal questions (e.g., “Who is Sahil?”, “What is a chatbot?”)
  by saying: "I'm here to help you analyze and query data. Please ask a data-related question."
- If a query depends on prior ones, infer logical continuation from context.
- When data context is unclear, briefly ask what detail the user meant before generating SQL.

**CRITICAL SQL RULES:**
1.  **NEVER use `SELECT *`**. Always specify the exact column names you need.
2.  **NEVER use `UNION` or `UNION ALL` unless all `SELECT` statements have the *exact same number and type* of columns.** The error you saw ("must have an equal number of expressions") is a direct violation of this.
3.  **Always use safe JOINs**:
    • If data types differ (e.g., numeric ID vs string 'S001'), use CAST or TRY_CAST safely.
    • Example: `CAST(int_field AS VARCHAR) = string_field` OR `TRY_CAST(string_field AS INT) = int_field`.
    • Never allow implicit conversion errors.
4.  Use only valid SQL based on the provided schema.
**RESPONSE FORMAT:**
- Be friendly and natural when responding — like a professional analyst explaining insights.
- Start answers conversationally (“Here’s what I found”, “Looks like…”, “From the data…”).
- Avoid long or robotic sentences.
"""

# -------------------- SAFE JSON SERIALIZER --------------------
def safe_jsonify(obj):
    """Recursively convert datetime, date, Decimal to serializable formats."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: safe_jsonify(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_jsonify(i) for i in obj]
    else:
        return obj


# -------------------- SQL TYPE MISMATCH FIXER --------------------
def fix_sql_type_mismatches(sql: str) -> str:
    """Detects common join errors (varchar=int) and applies safe casting for SQL Server."""
    if re.search(r"\bSupplierID\b", sql, re.IGNORECASE):
        sql = re.sub(
            r"ON\s+(\w+\.)?SupplierID\s*=\s*(\w+\.)?SupplierID",
            "ON TRY_CAST(REPLACE(\\1SupplierID, 'S', '') AS INT) = TRY_CAST(\\2SupplierID AS INT)",
            sql,
            flags=re.IGNORECASE
        )
    return sql


# ✅ --- CHANGED SECTION 3: TOKEN-EFFICIENT HUMAN RESPONSE ---
async def generate_human_response(query, merged_results, session_id=None):
    """Generate a natural, conversational response summarizing the query result."""
    if not merged_results:
        return ("I couldn’t find matching records for that query. Would you like to refine it?", 0)

    # OLD way sent 5 full rows of JSON, which was very token-heavy
    # sample = json.dumps(safe_jsonify(merged_results[:5]), indent=2)

    # NEW: Send only headers and the first row for lightweight context
    sample_data = safe_jsonify(merged_results)
    headers = list(sample_data[0].keys()) if sample_data else []
    first_row = list(sample_data[0].values()) if sample_data else []
    
    sample = f"Columns: {', '.join(headers)}\nFirst Row Example: {', '.join(map(str, first_row))}"

    context = ""
    if session_id and len(_sessions.get(session_id, {}).get("history", [])) > 2:
        context = "Continue the discussion naturally based on our earlier conversation.\n"

    prompt = f"""
    You are a friendly data analyst assistant.
    {context}
    The user asked: "{query}"
    
    Here are the columns and one example row from the result:
    {sample}

    Write a short, conversational summary (2–4 sentences) highlighting interesting insights or patterns.
    Avoid being repetitive or robotic. Mention trends or key data points when relevant.
    Example:
    - "Looks like FreshFarm Foods and RiceWorld Traders have the highest ratings this month."
    - "Here’s a quick look at supplier ratings by city — Mumbai and Nagpur are leading!"
    """

    try:
        completion = await run_in_threadpool(lambda: client.chat.completions.create(
            # ✅ CHANGED to a smaller, faster model for summarization
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.65,
        ))
        #return completion.choices[0].message.content.strip()
        text = completion.choices[0].message.content.strip()
        tokens = completion.usage.total_tokens if completion.usage else 0
        return (text, tokens)
    except Exception:
        return ("Here's your data summary.", 0)


@router.post("/multi-db-query")
async def multi_db_query(payload: dict = Body(...), request: Request = None):
    try:
        query = payload.get("query", "").strip()
        session_id = payload.get("session_id")
        session_id, session = get_or_create_session(session_id)

        # Dictionary to store token counts
        total_token_usage = {
           "sql_generation": 0,
           "human_response": 0
        }

        # 🧠 Step 1: Block irrelevant / non-data questions
        irrelevant_keywords = [
            "who are you", "who is", "what is your name", "what is a chatbot",
            "tell me about yourself", "how are you", "who made you", "what can you do"
        ]
        if any(k in query.lower() for k in irrelevant_keywords):
            return {
                "status": "info",
                "message": (
                    "Hey! 😊 I’m your data assistant — I can’t really answer personal or non-data questions, "
                    "but I’d love to help you analyze something from your database instead!"
                ),
                "session_id": session_id
            }

        # ✅ CHANGED to use the 5-minute cache, removed force=True
        build_index()
        selected_dbs = select_databases_by_embedding(query)
        if not selected_dbs:
            return {"status": "error", "message": "No relevant database found.", "session_id": session_id}

        results = {}

        # 🧩 Step 2: Process each relevant database
        for db_name in selected_dbs:
            session_gen = get_db_session(db_name)
            db = next(session_gen)
            schema_info = await get_cached_schema(db_name, db)
            schema_text = schema_info["text"]

            # 🧠 Step 3: Combine history with new query for contextual reasoning
            history = session["history"]
            previous_context = "\n".join([f"{m['role']}: {m['content']}" for m in history])

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "assistant", "content": f"Previous context:\n{previous_context}"},
                {"role": "user", "content": f"Database: {db_name}\nSchema:\n{schema_text}\n\nUser: {query}"}
            ]

            # 🧩 Step 4: Generate SQL query
            completion = await run_in_threadpool(lambda: client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.3,
            ))
            
            # Capture SQL generation tokens
            if completion.usage:
                total_token_usage["sql_generation"] += completion.usage.total_tokens

            sql_query = (
                completion.choices[0].message.content
                .replace("```sql", "").replace("```", "").strip()
            )
            sql_query = " ".join(sql_query.split())

            # 🧩 Step 5: Execute SQL safely
            def execute_query():
                if "I'm here to help" in sql_query or not sql_query.lower().startswith("select"):
                    raise ValueError(sql_query)

                def fix_sql(sql):
                    sql = sql.replace("talk2data.", "talk2data.dbo.").replace("fooddb.", "fooddb.dbo.")
                    sql = sql.replace("ordersdb.", "ordersdb.dbo.")
                    sql = fix_sql_type_mismatches(sql)
                    return sql
                
                fixed_sql = fix_sql(sql_query)
                result = db.execute(text(fixed_sql))
                return (result.fetchall() if result.returns_rows else []), fixed_sql

            # Handle clarification questions
            try:
                rows, executed_sql = await run_in_threadpool(execute_query)
            except ValueError as ve:
                if "I'm here to help" in str(ve) or "Which data" in str(ve):
                    clarification_msg = str(ve)
                    add_message(session_id, "user", query)
                    add_message(session_id, "assistant", clarification_msg)
                    return {
                        "status": "info",
                        "message": clarification_msg,
                        "session_id": session_id
                    }
                else:
                    raise ve

            formatted = [safe_jsonify(dict(row._mapping)) for row in rows]
            
            # 🧠 Summarize for memory
            summary = "Data retrieved successfully."
            add_message(session_id, "user", query)
            add_message(session_id, "assistant", summary)

            results[db_name] = {
                "generated_sql": executed_sql,
                "rows": formatted,
                "rows_returned": len(formatted),
                "schema_version": schema_info["hash"][:8],
            }
            db.close()

        merged_output = merge_results_across_dbs(results)
        
        if all(len(v["rows"]) == 0 for v in results.values()):
            
            # ✅ PRINT to terminal here
            print(f"[📊 TOKEN USAGE] SQL: {total_token_usage['sql_generation']}, Response: 0, Total: {total_token_usage['sql_generation']}")
            
            return {
                "status": "success",
                "input": query,
                "selected_databases": selected_dbs,
                "results": results,
                "merged_results": [],
                "merge_reasoning": "No matching records.",
                "session_id": session_id,
                "human_response": "I couldn’t find any matching records for that request. Maybe try a different filter or column?",
                # ❌ "token_usage" key is REMOVED
            }

        # 💬 Generate conversational response
        human_response, response_tokens = await generate_human_response(query, merged_output, session_id)
        total_token_usage["human_response"] = response_tokens

        # ✅ PRINT to terminal here
        total = total_token_usage['sql_generation'] + total_token_usage['human_response']
        print(f"[📊 TOKEN USAGE] SQL: {total_token_usage['sql_generation']}, Response: {total_token_usage['human_response']}, Total: {total}")

        return {
            "status": "success",
            "input": query,
            "selected_databases": selected_dbs,
            "results": results,
            "merged_results": merged_output or [],
            "merge_reasoning": "(auto-merged successfully)",
            "session_id": session_id,
            "human_response": human_response,
            # ❌ "token_usage" key is REMOVED
        }

    except Exception as e:
        return {"status": "error", "message": str(e), "type": type(e).__name__, "session_id": locals().get("session_id")}