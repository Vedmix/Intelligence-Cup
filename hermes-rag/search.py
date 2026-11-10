import argparse
import json
import re
from pathlib import Path

DEFAULT_TICKETS = Path(__file__).resolve().parents[1] / "data" / "tickets"

def cards(root):
    for path in sorted(root.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        text = path.read_text(encoding="utf-8-sig").strip()
        if text:
            yield {"path": path.relative_to(root).as_posix(),
                   "title": text.splitlines()[0].lstrip("# "), "text": text}

def tokens(text):
    return re.findall(r"[\w]+(?:[-#.][\w]+)*|-\d+", text.lower())

def main():
    from rank_bm25 import BM25Okapi
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--tickets", type=Path, default=DEFAULT_TICKETS)
    args = parser.parse_args()
    docs = list(cards(args.tickets))
    if not docs:
        parser.error("No ticket cards found")
    query = tokens(args.query)
    corpus = [tokens(doc["text"]) for doc in docs]
    scores = BM25Okapi(corpus).get_scores(query)
    ranked = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)
    matches = [dict(docs[i], score=float(scores[i])) for i in ranked
               if set(query).intersection(corpus[i])]
    print(json.dumps(matches[:max(0, args.limit)], ensure_ascii=False))

if __name__ == "__main__":
    main()
