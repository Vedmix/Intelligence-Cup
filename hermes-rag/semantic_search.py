import argparse
import json
from pathlib import Path

import numpy as np

from search import DEFAULT_TICKETS, cards

MODEL = "intfloat/multilingual-e5-small"

def chunks(text):
    for start in range(0, len(text), 750):
        yield text[start:start + 900]
        if start + 900 >= len(text):
            break

def main():
    from sentence_transformers import SentenceTransformer

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["index", "search"])
    parser.add_argument("query", nargs="?")
    parser.add_argument("--tickets", type=Path, default=DEFAULT_TICKETS)
    parser.add_argument("--index-dir", type=Path, default=Path(__file__).parent / "index")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    vectors_path = args.index_dir / "embeddings.npy"
    metadata_path = args.index_dir / "metadata.json"
    if args.command == "search" and not (args.query and args.query.strip()):
        parser.error("search requires a query")
    model = SentenceTransformer(MODEL, device="cpu")
    if args.command == "index":
        metadata = [dict(doc, text=chunk) for doc in cards(args.tickets)
                    for chunk in chunks(doc["text"])]
        if not metadata:
            parser.error("No ticket cards found")
        passages = ["passage: " + row["title"] + "\n" + row["text"] for row in metadata]
        vectors = model.encode(passages, normalize_embeddings=True).astype(np.float32)
        args.index_dir.mkdir(parents=True, exist_ok=True)
        np.save(vectors_path, vectors, allow_pickle=False)
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        print(f"Indexed {len(set(row['path'] for row in metadata))} tickets in {len(metadata)} chunks")
        return

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    vectors = np.load(vectors_path, allow_pickle=False)
    if vectors.shape != (len(metadata), 384):
        parser.error("Index shape does not match metadata. Rebuild the index.")
    query = model.encode("query: " + args.query, normalize_embeddings=True)
    scores = vectors @ query
    seen = set()
    results = []
    for i in np.argsort(-scores, kind="stable"):
        if len(results) >= args.limit:
            break
        row = metadata[i]
        if row["path"] in seen:
            continue
        seen.add(row["path"])
        results.append({"title": row["title"], "path": row["path"],
                        "excerpt": row["text"], "similarity": float(scores[i])})
    print(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()
