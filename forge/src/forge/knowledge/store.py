"""SQLite FTS5 knowledge store. Facts survive context resets."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS facts(
  id INTEGER PRIMARY KEY,
  domain TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  source TEXT DEFAULT '',
  version TEXT DEFAULT '0.1.0'
);
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(title, body, content=facts, content_rowid=id);
CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
  INSERT INTO facts_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
  INSERT INTO facts_fts(facts_fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body);
END;
"""


class KnowledgeStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.db = sqlite3.connect(str(path))
        self.db.executescript(SCHEMA)

    def add(self, domain: str, title: str, body: str,
            source: str = "", version: str = "0.1.0") -> int:
        cur = self.db.execute(
            "INSERT INTO facts(domain,title,body,source,version) VALUES(?,?,?,?,?)",
            (domain, title, body, source, version),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def search(self, query: str, domain: str = "", limit: int = 5) -> list[dict]:
        if domain:
            rows = self.db.execute(
                """SELECT f.id,f.domain,f.title,f.body,f.source FROM facts_fts
                   JOIN facts f ON f.id = facts_fts.rowid
                   WHERE facts_fts MATCH ? AND f.domain = ? LIMIT ?""",
                (query, domain, limit),
            ).fetchall()
        else:
            rows = self.db.execute(
                """SELECT f.id,f.domain,f.title,f.body,f.source FROM facts_fts
                   JOIN facts f ON f.id = facts_fts.rowid
                   WHERE facts_fts MATCH ? LIMIT ?""",
                (query, limit),
            ).fetchall()
        return [
            {"id": r[0], "domain": r[1], "title": r[2], "body": r[3], "source": r[4]}
            for r in rows
        ]

    def load_jsonl(self, path: str | Path) -> int:
        n = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                o = json.loads(line)
                self.add(o.get("domain", "general"), o.get("title", ""),
                         o.get("body", ""), o.get("source", ""), o.get("version", "0.1.0"))
                n += 1
        return n

    def count(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM facts").fetchone()[0])

    def get(self, fact_id: int) -> dict | None:
        r = self.db.execute(
            "SELECT id,domain,title,body,source FROM facts WHERE id=?",
            (fact_id,)).fetchone()
        if r is None:
            return None
        return {"id": r[0], "domain": r[1], "title": r[2], "body": r[3],
                "source": r[4]}
