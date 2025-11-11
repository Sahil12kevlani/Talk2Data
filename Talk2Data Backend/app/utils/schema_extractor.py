from sqlalchemy import inspect
import hashlib, json

def get_dynamic_schema_text(db):
    """Reflect current schema from SQL Server and return summarized description + hash."""
    inspector = inspect(db.bind)
    schema_info = {}
    relations = []

    # --- THIS SECTION IS UNCHANGED ---
    # We still need to inspect everything to build the hash correctly for caching
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        pk = inspector.get_pk_constraint(table_name).get("constrained_columns", [])

        schema_info[table_name] = {
            "columns": [
                {"name": col["name"], "type": str(col.get("type")), "nullable": col.get("nullable", True)}
                for col in columns
            ],
            "primary_key": pk,
            "foreign_keys": [
                {
                    "column": fk["constrained_columns"],
                    "references": fk["referred_table"],
                    "ref_column": fk["referred_columns"],
                }
                for fk in foreign_keys
            ],
        }

        # This list of relations is perfect, we'll keep it
        for fk in foreign_keys:
            relations.append(
                f"{table_name}.{fk['constrained_columns'][0]} → {fk['referred_table']}.{fk['referred_columns'][0]}"
            )

    # --- MODIFIED SECTION ---
    # Build the new lightweight schema text for the LLM
    
    schema_text = "You are a SQL generator for a Microsoft SQL Server database.\n\n"
    schema_text += "Here is the lightweight schema. Only use columns listed.\n\n"

    # Create the compact "Table: name (Columns: col1, col2)" format
    for table, details in schema_info.items():
        column_names = [c["name"] for c in details["columns"]]
        schema_text += f"Table: {table} (Columns: {', '.join(column_names)})\n"

    # Add the relationships, which are critical for JOINs
    if relations:
        schema_text += "\nRelationships for JOINs:\n"
        for rel in relations:
            schema_text += f"- {rel}\n"

    schema_text += "\nAlways output `only` the SQL query text without explanation or markdown. Do NOT use columns that are not listed above."
    # --- END MODIFIED SECTION ---


    # The hash logic remains the same, so caching still works
    schema_hash = hashlib.sha256(json.dumps(schema_info, sort_keys=True).encode()).hexdigest()

    return {"text": schema_text, "hash": schema_hash}