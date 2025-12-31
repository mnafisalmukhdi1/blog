import json
import os
import tempfile
from scripts.find_unwrapped_arabic import analyze_file


def test_analyze_file_line_only(tmp_path):
    p = tmp_path / 'post.md'
    p.write_text('This is a test\n\nسورة\nAnother line\n', encoding='utf-8')
    results = analyze_file(str(p), min_len=1)
    # Expect one Arabic line detected
    assert any(r['kind'] == 'line-only' for r in results)


def test_analyze_file_inline(tmp_path):
    p = tmp_path / 'post2.md'
    p.write_text('Mixed line with Arabic كلمة and latin\n', encoding='utf-8')
    results = analyze_file(str(p), min_len=1)
    assert any(r['kind'] == 'inline' for r in results)
