from app.utils.slug import safe_filename, slugify


def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_unicode():
    assert slugify("Xin chào Việt Nam") == "xin-chao-viet-nam"


def test_slugify_empty():
    assert slugify("") == "untitled"


def test_slugify_truncate():
    out = slugify("a" * 100, max_len=10)
    assert len(out) <= 10


def test_safe_filename_ok():
    assert safe_filename("hero_01.png") == "hero_01.png"


def test_safe_filename_traversal():
    assert safe_filename("../escape.png") == ""
    assert safe_filename("foo/bar.png") == ""
    assert safe_filename("foo\\bar.png") == ""


def test_safe_filename_hidden():
    assert safe_filename(".env") == ""
