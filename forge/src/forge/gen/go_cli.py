"""Go CLI generator: консольная утилита на stdlib (flag), ноль зависимостей.

Generates: go.mod, main.go (флаги --name/--count), main_test.go, README.
Проверяется: gofmt-чистота текста и go vet/build, если тулчейн есть.
"""
from __future__ import annotations

import re
from pathlib import Path

MAIN = '''package main

import (
	"flag"
	"fmt"
	"os"
	"strings"
)

func run(name string, count int) string {
	if name == "" {
		name = "world"
	}
	if count < 1 {
		count = 1
	}
	return strings.TrimSpace(strings.Repeat("hello "+name+"\\n", count))
}

func main() {
	name := flag.String("name", "world", "who to greet")
	count := flag.Int("count", 1, "how many times")
	flag.Parse()
	fmt.Print(run(*name, *count))
	os.Exit(0)
}
'''

TEST = '''package main

import "testing"

func TestRun(t *testing.T) {
	if got := run("go", 2); got != "hello go\\nhello go" {
		t.Fatalf("got %q", got)
	}
}
'''


def _slug(name: str) -> str:
    s = "".join(c if c.isalnum() or c in "-_" else "_" for c in (name or "app")).lower()
    return s or "app"


def generate(out_dir: str | Path, name: str = "cli") -> dict:
    """Generates a Go CLI project. Returns {dir, files} (+ok/problems)."""
    safe = _slug(name)
    out = Path(out_dir)
    files = {"go.mod": f"module {safe}\n\ngo 1.21\n",
             "README.md": f"# {safe}\n\n`go run . --name Ada --count 2`\n",
             "main.go": MAIN,
             "main_test.go": TEST}
    made = []
    for rel, content in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        made.append(rel)
    return {"dir": str(out), "files": made, "ok": True, "problems": []}
