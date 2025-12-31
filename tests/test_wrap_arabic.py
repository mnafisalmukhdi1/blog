import os
import tempfile
from scripts.wrap_arabic import wrap_line_content, apply_changes


def test_wrap_line_content():
    line = '   كلمة'
    wrapped = wrap_line_content(line)
    assert 'lang="ar"' in wrapped


def test_apply_changes(tmp_path):
    p = tmp_path / 'post.md'
    p.write_text('First line\nكلمة\nLast line\n', encoding='utf-8')
    grouped = {str(p): [2]}
    changes = apply_changes(grouped, apply=False)
    assert str(p) in changes
    # apply and ensure file changed
    apply_changes(grouped, apply=True)
    content = p.read_text(encoding='utf-8')
    assert '<p lang="ar"' in content
