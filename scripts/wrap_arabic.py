#!/usr/bin/env python3
"""Safe auto-fixer that wraps line-only Arabic snippets with <p lang="ar" dir="rtl">…</p>.

Usage:
  ./scripts/wrap_arabic.py [--dry-run] [--apply] [--commit]

By default it runs in dry-run mode and prints what it would change.
Use --apply to modify files in place. Use --commit to create a branch and commit changes
(with git available).
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from typing import Dict, List

SCRIPT_DIR = os.path.dirname(__file__)
FIND_SCRIPT = os.path.join(SCRIPT_DIR, 'find_unwrapped_arabic.py')


def run_finder(only_line_only=True):
    cmd = [sys.executable, FIND_SCRIPT, '--format', 'json']
    if only_line_only:
        cmd.append('--only-line-only')
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)
    if p.returncode not in (0,):
        # still may have printed JSON, parse if possible
        pass
    try:
        data = json.loads(p.stdout)
    except Exception as e:
        print('Failed to parse finder output:', e)
        print('STDOUT:', p.stdout)
        print('STDERR:', p.stderr)
        raise
    grouped: Dict[str, List[int]] = defaultdict(list)
    for item in data:
        grouped[item['file']].append(item['line'])
    return grouped


def backup_file(path: str):
    bak = path + '.bak'
    shutil.copy2(path, bak)
    return bak


def wrap_line_content(line: str) -> str:
    # preserve leading indentation
    m = re.match(r'^(\s*)(.*?)(\s*)$', line)
    if not m:
        return line
    indent, core, trailing = m.groups()
    # If line already contains markup (starts with <), skip
    if core.strip().startswith('<'):
        return line
    return f"{indent}<p lang=\"ar\" dir=\"rtl\">{core.strip()}</p>{trailing}"


def apply_changes(grouped: Dict[str, List[int]], apply: bool = False) -> Dict[str, List[str]]:
    changes = {}
    for path, lines in grouped.items():
        with open(path, 'r', encoding='utf-8') as f:
            orig_lines = f.readlines()
        new_lines = list(orig_lines)
        touched = []
        for ln in sorted(lines):
            idx = ln - 1
            if idx < 0 or idx >= len(orig_lines):
                continue
            original = orig_lines[idx].rstrip('\n')
            wrapped = wrap_line_content(original)
            if original == wrapped:
                continue
            new_lines[idx] = wrapped + '\n'
            touched.append(f"{ln}: {original.strip()} -> {wrapped.strip()}")
        if touched:
            changes[path] = touched
            if apply:
                backup_file(path)
                with open(path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
    return changes


def git_commit_changes(branch_name: str, message: str):
    # create branch
    subprocess.check_call(['git', 'checkout', '-b', branch_name])
    subprocess.check_call(['git', 'add', '.'])
    subprocess.check_call(['git', 'commit', '-m', message])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Modify files in place')
    parser.add_argument('--commit', action='store_true', help='Create a branch and commit changes')
    parser.add_argument('--branch', type=str, default='fix/wrap-arabic')
    args = parser.parse_args()

    grouped = run_finder(only_line_only=True)
    if not grouped:
        print('No line-only unwrapped Arabic found.')
        return

    print('Found potential line-only Arabic snippets in these files:')
    for path, lines in grouped.items():
        print(f"- {path}: lines {', '.join(map(str, lines))}")

    changes = apply_changes(grouped, apply=args.apply)
    if not changes:
        print('No changes to apply (maybe all lines were already wrapped or skipped due to markup).')
        return

    print('\nChanges:')
    for path, touched in changes.items():
        print(f"\n{path}:")
        for t in touched:
            print('  - ' + t)

    if args.apply and args.commit:
        branch = args.branch
        msg = 'Auto-wrap Arabic line-only snippets with lang=ar dir=rtl (scripts/wrap_arabic.py)'
        print(f"\nCreating branch {branch} and committing changes...")
        try:
            git_commit_changes(branch, msg)
            print('Committed. You can now open a PR from branch:', branch)
        except subprocess.CalledProcessError as e:
            print('Git operations failed:', e)
            print('Please commit changes manually.')


if __name__ == '__main__':
    main()
