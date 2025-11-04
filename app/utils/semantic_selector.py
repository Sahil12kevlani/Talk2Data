import time
import threading
import warnings
from typing import List
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from sqlalchemy import exc as sa_exc
from app.db.multidb_manager import get_db_session, DATABASES
from app.utils.schema_extractor import get_dynamic_schema_text

# -------------------------------------------------------------------
# SILENCE SQLALCHEMY WARNINGS
# -------------------------------------------------------------------
warnings.filterwarnings("ignore", category=sa_exc.SAWarning)

# -------------------------------------------------------------------
# GLOBAL SETTINGS
# -------------------------------------------------------------------
_VECTOR_INDEX = []
_INDEX_LOCK = threading.Lock()
_LAST_INDEX_BUILD = 0
_INDEX_TTL = 60 * 5  # 5 minutes cache

# -------------------------------------------------------------------
# EMBEDDING MODEL
# -------------------------------------------------------------------
# all-MiniLM-L6-v2 is lightweight and accurate for schema-level semantics
_model = SentenceTransformer("all-MiniLM-L6-v2")

def _to_np(vec_list):
    """Convert list of vectors to NumPy array."""
    return np.array(vec_list, dtype=np.float32)

def _embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of text strings."""
    return _model.encode(texts, normalize_embeddings=True).tolist()

# -------------------------------------------------------------------
# INDEX BUILDER
# -------------------------------------------------------------------
def build_index(force: bool = False):
    """
    Builds or refreshes an in-memory vector index from all database schemas.
    Each DB and table is represented as a semantic vector.
    """
    global _VECTOR_INDEX, _LAST_INDEX_BUILD

    with _INDEX_LOCK:
        if not force and (time.time() - _LAST_INDEX_BUILD) < _INDEX_TTL and _VECTOR_INDEX:
            return

        print("\n[🔄] Building semantic index for all databases...")
        texts_to_embed, metas = [], []

        for db_name in DATABASES.keys():
            session_gen = get_db_session(db_name)
            db = next(session_gen)
            try:
                schema_info = get_dynamic_schema_text(db)
                text = schema_info.get("text", "").strip()
                if not text:
                    continue

                # Split schema into table-level blocks
                blocks = text.split("\n\n")

                # Database-level summary
                related_tables = [
                    b.split(":")[1].split("\n")[0].strip()
                    for b in blocks if b.lower().startswith("table:")
                ]
                db_summary = (
                    f"Database: {db_name}. Contains tables related to: "
                    + ", ".join(related_tables[:5])
                )

                texts_to_embed.append(db_summary)
                metas.append({"db": db_name, "table": None, "text": db_summary})

                # Add table-level snippets
                for block in blocks:
                    if not block.strip():
                        continue

                    short_block = "\n".join(block.splitlines()[:8])
                    first_line = block.splitlines()[0].lower()
                    table_name = None
                    if first_line.startswith("table:"):
                        table_name = block.split(":")[1].split("\n")[0].strip()

                    contextual_block = f"Database: {db_name}. {short_block}"
                    texts_to_embed.append(contextual_block)
                    metas.append({"db": db_name, "table": table_name, "text": contextual_block})

            finally:
                db.close()

        if not texts_to_embed:
            _VECTOR_INDEX = []
            _LAST_INDEX_BUILD = time.time()
            print("[⚠️] No schema text found for indexing.")
            return

        embeddings = _embed_texts(texts_to_embed)
        _VECTOR_INDEX = [
            {"embedding": emb, "meta": metas[i]}
            for i, emb in enumerate(embeddings)
        ]
        _LAST_INDEX_BUILD = time.time()
        print(f"[✅] Semantic index built for {len(DATABASES)} databases ({len(_VECTOR_INDEX)} entries).")

# -------------------------------------------------------------------
# SELECTOR
# -------------------------------------------------------------------
def select_databases_by_embedding(query: str, top_k: int = 10, score_threshold: float = 0.70) -> List[str]:
    """
    Returns a ranked list of database names relevant to the given query
    using semantic similarity between the query and schema embeddings.
    """
    if (time.time() - _LAST_INDEX_BUILD) > _INDEX_TTL or not _VECTOR_INDEX:
        build_index(force=True)

    q_emb = _embed_texts([query])[0]
    if not _VECTOR_INDEX:
        print("[⚠️] No vector index available.")
        return []

    vectors = [entry["embedding"] for entry in _VECTOR_INDEX]
    arr = _to_np(vectors)
    q = np.array(q_emb).reshape(1, -1).astype(np.float32)

    sims = cosine_similarity(q, arr)[0]
    scored = [(sims[i], _VECTOR_INDEX[i]["meta"]) for i in range(len(sims))]
    scored.sort(key=lambda x: x[0], reverse=True)

    db_scores = {}
    for score, meta in scored[:top_k]:
        db = meta.get("db")
        if db not in db_scores or score > db_scores[db]:
            db_scores[db] = score

    selected = [
        db for db, sc in sorted(db_scores.items(), key=lambda t: t[1], reverse=True)
        if sc >= score_threshold
    ]

    if not selected:
        selected = [
            db for db, _ in sorted(db_scores.items(), key=lambda t: t[1], reverse=True)
        ][:2]

    print(f"[🧠] Query: {query}\n[🎯] Selected DBs: {selected}")
    return selected
