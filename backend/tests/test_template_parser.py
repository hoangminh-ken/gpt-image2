import pytest

from app.parsers.template import build_items


def test_one_per_ref():
    items = build_items("a prompt", ["a.png", "b.png", "c.png"])
    assert len(items) == 3
    assert [i.row_idx for i in items] == [0, 1, 2]
    assert all(i.prompt == "a prompt" for i in items)
    assert items[0].refs == ["a.png"]
    assert items[1].refs == ["b.png"]


def test_empty_prompt():
    with pytest.raises(ValueError):
        build_items("", ["a.png"])


def test_empty_refs():
    with pytest.raises(ValueError):
        build_items("p", [])
