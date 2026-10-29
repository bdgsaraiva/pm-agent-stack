from pmstack import notepage

NOTE = """<!-- page: x -->
# Morning note — Thursday 29 Oct 2026

## Market levels

| Market | Level | Change | sd |
|---|---:|---:|---:|
| **Energy** | | | |
| Brent (BZZ26) | 114.35 | -0.84% | -0.2 |

## What's happening

Brent -0.84% live on 2026-10-28 ([Reuters](https://example.com/a), also WSJ); US 10y yield +5.2 bp y.

## Data health

GDELT partial.
"""


def test_build_keeps_figures_and_speaks(tmp_path):
    p = tmp_path / "note.md"
    p.write_text(NOTE, encoding="utf-8")
    h = notepage.build(p)
    assert "114.35" in h and "<!DOCTYPE" not in h.upper()
    assert 'class="dn">-0.84%' in h
    title, _, secs = notepage.split_sections(NOTE)
    script = notepage.speech_script(secs, title)
    text = " ".join(l for s in script for l in s["lines"])
    assert "Brent, 114.35, down 0.84 percent." in text
    assert "28 October" in text and "up 5.2 basis points" in text
    assert "example.com" not in text and "Reuters" not in text
    assert "GDELT" not in text  # Data health is not read aloud
