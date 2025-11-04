from sqlalchemy import inspect
import hashlib, json

def get_dynamic_schema_text(db):
    """Reflect current schema from SQL Server and return summarized description + hash."""
    inspector = inspect(db.bind)
    schema_info = {}
    relations = []

    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)

        schema_info[table_name] = {
            "columns": [col["name"] for col in columns],
            "foreign_keys": [
                {
                    "column": fk["constrained_columns"],
                    "references": fk["referred_table"],
                    "ref_column": fk["referred_columns"],
                }
                for fk in foreign_keys
            ],
        }

        for fk in foreign_keys:
            relations.append(
                f"{table_name}.{fk['constrained_columns'][0]} → {fk['referred_table']}.{fk['referred_columns'][0]}"
            )

    # Build schema text for LLM
    schema_text = "You are a SQL generator for a Microsoft SQL Server database.\n\n"
    schema_text += "Here is the current live schema:\n\n"

    for table, details in schema_info.items():
        schema_text += f"Table: {table}\n"
        schema_text += f"Columns: {', '.join(details['columns'])}\n"
        if details["foreign_keys"]:
            schema_text += "Foreign Keys: " + ", ".join(
                [f"{fk['column'][0]} → {fk['references']}.{fk['ref_column'][0]}" for fk in details["foreign_keys"]]
            ) + "\n"
        schema_text += "\n"

    if relations:
        schema_text += "Relationships between tables:\n"
        for rel in relations:
            schema_text += f"- {rel}\n"

    schema_text += "\nAlways output **only** the SQL query text without explanation or markdown."

    schema_hash = hashlib.sha256(json.dumps(schema_info, sort_keys=True).encode()).hexdigest()

    return {"text": schema_text, "hash": schema_hash}