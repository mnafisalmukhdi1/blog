#!/usr/bin/env python3
"""Detect Arabic script occurrences in _posts and report lines not already marked with lang="ar".

Usage:
  ./scripts/find_unwrapped_arabic.py [--format json|csv] [--min-length N] [--only-line-only]

Outputs JSON (default) with entries: {file, line_no, snippet, kind}
kind: "line-only" (conservative, safe to wrap) or "inline" (mixed with Latin/other text)
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from typing import List, Dict, Any

ARABIC_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+')
LATIN_RE = re.compile(r'[A-Za-z]')

POSTS_DIR = "_posts"


def analyze_file(path: str, min_len: int = 3) -> List[Dict[str, Any]]:
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for i, raw in enumerate(f, start=1):
            line = raw.rstrip('\n')
            if ARABIC_RE.search(line):
                # Skip lines already wrapped explicitly with lang="ar"
                if 'lang="ar"' in line or "lang='ar'" in line:
                    continue
                # Determine kind: line-only vs inline
                arabic_count = len(ARABIC_RE.findall(line))
                latin_count = len(LATIN_RE.findall(line))
                # heuristics: if there are latin letters, treat as inline
                if arabic_count >= min_len and latin_count == 0 and not line.strip().startswith('<'):
                    kind = "line-only"
                else:
                    kind = "inline"
                snippet = line.strip()
                results.append({"file": path, "line": i, "snippet": snippet, "kind": kind})
    return results


def walk_posts(min_len: int = 3, only_line_only: bool = False) -> List[Dict[str, Any]]:
    out = []
    for root, _, files in os.walk(POSTS_DIR):
        for fn in sorted(files):
            if not fn.endswith('.md'):
                continue
            path = os.path.join(root, fn)
            out.extend(analyze_file(path, min_len=min_len))
    if only_line_only:
        out = [r for r in out if r['kind'] == 'line-only']
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--format', choices=['json', 'csv'], default='json')
    parser.add_argument('--min-length', type=int, default=3)
    parser.add_argument('--only-line-only', action='store_true')
    parser.add_argument('--output', type=str, default='-')
    args = parser.parse_args()

    matches = walk_posts(min_len=args.min_length, only_line_only=args.only_line_only)

    if args.format == 'json':
        out = json.dumps(matches, ensure_ascii=False, indent=2)
    else:
        # simple CSV
        lines = ["file,line,snippet,kind"]
        for m in matches:
            snippet = m['snippet'].replace('"', '""')
            lines.append(f"{m['file']},{m['line']},\"{snippet}\",{m['kind']}")
        out = "\n".join(lines)

    if args.output == '-':
        # Avoid UnicodeEncodeError on Windows consoles by writing bytes
        sys.stdout.buffer.write((out + "\n").encode('utf-8'))
    else:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(out + "\n")

    # exit code == number of matches (capped) to allow CI to detect >0
    if len(matches) > 0:
        # cap exit code to 125 to be safe
        sys.exit(min(len(matches), 125))


if __name__ == '__main__':
    main()
