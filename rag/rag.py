#!/usr/bin/env python3
"""Tiny local RAG: index a folder into Chroma with Ollama embeddings; query it.
Usage: rag.py index DIR | rag.py query "question" [-k N]"""
import glob
import os
import sys

import chromadb
import requests

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
CHROMA = os.environ.get("CHROMA_URL", "http://127.0.0.1:8000")
EMBED = os.environ["EMBED_MODEL"]


def embed(texts):
    r = requests.post(f"{OLLAMA}/api/embed", json={"model": EMBED, "input": texts}, timeout=300)
    r.raise_for_status()
    return r.json()["embeddings"]


def coll():
    host, port = CHROMA.split("://")[1].split(":")
    c = chromadb.HttpClient(host=host, port=int(port))
    return c.get_or_create_collection("docs")


def chunks(text, n=800):
    return [text[i:i + n] for i in range(0, len(text), n)] or [""]


def index(d):
    c = coll()
    for p in sorted(glob.glob(os.path.join(d, "**", "*"), recursive=True)):
        if not os.path.isfile(p) or not p.endswith((".md", ".txt")):
            continue
        with open(p, encoding="utf-8", errors="ignore") as f:
            cs = chunks(f.read())
        c.upsert(ids=[f"{p}:{i}" for i in range(len(cs))], documents=cs,
                 embeddings=embed(cs), metadatas=[{"source": p}] * len(cs))
        print("indexed", p, len(cs))


def query(q, k=3):
    r = coll().query(query_embeddings=embed([q]), n_results=k)
    for doc, m in zip(r["documents"][0], r["metadatas"][0]):
        print(f"--- {m['source']}\n{doc}\n")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    if sys.argv[1] == "index":
        index(sys.argv[2])
    elif sys.argv[1] == "query":
        query(sys.argv[2], int(sys.argv[4]) if len(sys.argv) > 4 else 3)
    else:
        sys.exit(__doc__)
