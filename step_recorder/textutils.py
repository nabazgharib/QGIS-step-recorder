# -*- coding: utf-8 -*-
"""Small pure-Python text helpers (no Qt)."""
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_MNEMONIC_RE = re.compile(r"&(?!&)")
_PREFIX_RE = re.compile(r"^(m|le|cb|cmb|chk|rb|btn|pb|tb|spin|sb|txt|lbl)(?=[A-Z_0-9])")
_WORD_RE = re.compile(
    r"^(LineEdit|ComboBox|CheckBox|RadioButton|PushButton|ToolButton|DoubleSpinBox|SpinBox"
    r"|TextEdit|Button|Combo|Check|Radio|Label)(?=[A-Z_0-9])"
)
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def strip_html(text):
    return _TAG_RE.sub("", text or "")


def clean_text(text, keep_ellipsis=True):
    """Clean a Qt widget/action text: remove &mnemonics, html, tab shortcuts."""
    if not text:
        return ""
    text = str(text).split("\t")[0]
    text = strip_html(text)
    text = _MNEMONIC_RE.sub("", text).replace("&&", "&")
    text = _WS_RE.sub(" ", text).strip()
    if not keep_ellipsis:
        text = text.rstrip(".…").strip()
    return text


def clean_label(text):
    """Clean a label text: as clean_text but without a trailing colon."""
    text = clean_text(text)
    text = text.rstrip(":：؛ ").strip()
    return text


def pretty_name(object_name):
    """'mLineEdit_bufferDistance' -> 'Buffer distance'."""
    name = object_name or ""
    if not name or name.startswith("qt_") or name.startswith("_"):
        return ""
    for _ in range(3):
        new = _WORD_RE.sub("", _PREFIX_RE.sub("", name, count=1), count=1)
        if new == name:
            break
        name = new
    name = name.strip("_")
    name = _CAMEL_RE.sub(" ", name.replace("_", " "))
    name = _WS_RE.sub(" ", name).strip()
    if not name:
        return ""
    return name[0].upper() + name[1:].lower()


def shorten(text, n=60):
    text = _WS_RE.sub(" ", text or "").strip()
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "…"


_ATTR_TITLE_RE = re.compile(r"^(.*?)\s+[—\-]\s+Features Total.*$")


def clean_title(title):
    """Make a window title suitable for 'In the **X** dialog'."""
    title = clean_text(title)
    m = _ATTR_TITLE_RE.match(title)
    if m:
        title = "%s — Attribute Table" % m.group(1)
    for suffix in (" — QGIS", " - QGIS"):
        if title.endswith(suffix):
            title = title[: -len(suffix)]
    return title.strip()


def strip_markup(text):
    """Remove **bold** and `code` markers."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text or "")
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text
