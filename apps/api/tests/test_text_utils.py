from app.utils.text import compact_text, first_meaningful_text, sanitize_abstract_text


def test_sanitize_abstract_text_removes_nature_preamble() -> None:
    raw = (
        "Nature, Published online: 20 April 2026; doi:10.1038/d41586-026-00990-2 "
        "It's an important milestone in many fields."
    )

    assert sanitize_abstract_text(raw) == "It's an important milestone in many fields."


def test_first_meaningful_text_strips_html_nature_preamble() -> None:
    raw = (
        '<p>Nature, Published online: 20 April 2026; '
        '<a href="https://www.nature.com/articles/d41586-026-00990-2">'
        "doi:10.1038/d41586-026-00990-2</a></p>"
        "It’s an important milestone in many fields."
    )

    assert first_meaningful_text([raw]) == "It’s an important milestone in many fields."


def test_compact_text_uses_sanitized_abstract_text() -> None:
    raw = (
        "Nature, Published online: 20 April 2026; doi:10.1038/d41586-026-00990-2 "
        "A concise summary."
    )

    assert compact_text(raw) == "A concise summary."
