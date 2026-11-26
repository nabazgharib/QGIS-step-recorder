# -*- coding: utf-8 -*-
"""Export a Session to Markdown / HTML / PDF / plain text / JSON.

Everything except PDF is pure Python (no Qt) so it can be tested anywhere.
"""
import base64
import datetime
import html as _html
import os
import re
import shutil

from . import log
from .i18n import T, is_rtl
from .model import ROLE_ACTION, ROLE_NOTE, ROLE_RESULT
from .textutils import strip_markup

FORMATS = {
    "md": ("Markdown (*.md)", ".md"),
    "html": ("Web page (*.html)", ".html"),
    "pdf": ("PDF document (*.pdf)", ".pdf"),
    "txt": ("Plain text (*.txt)", ".txt"),
    "json": ("Step Recorder session (*.json)", ".json"),
}


# ------------------------------------------------------------------ helpers
def markup_to_html(text):
    s = _html.escape(text or "", quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def blocks(session):
    """Group the enabled steps.

    Returns a list of dicts:
      {'type': 'action', 'n': 1, 'step': Step, 'results': [Step, ...]}
      {'type': 'note',   'step': Step}
      {'type': 'result', 'step': Step}      (a result with no action before it)
    """
    out, current, n = [], None, 0
    for s in session.steps:
        if not s.enabled:
            continue
        if s.role == ROLE_ACTION:
            n += 1
            current = {"type": "action", "n": n, "step": s, "results": []}
            out.append(current)
        elif s.role == ROLE_RESULT:
            if current is not None:
                current["results"].append(s)
            else:
                out.append({"type": "result", "step": s})
        else:
            current = None
            out.append({"type": "note", "step": s})
    return out


def prepare_images(session, dest_dir, rel_prefix=None):
    """Copy the screenshots of enabled steps into *dest_dir* with tidy names.

    Returns {step.uid: reference} where reference is relative to the export
    file (rel_prefix + filename) or absolute when rel_prefix is None.
    """
    mapping, i = {}, 0
    for s in session.steps:
        if not s.enabled or not s.image or not os.path.exists(s.image):
            continue
        i += 1
        os.makedirs(dest_dir, exist_ok=True)
        name = "step_%03d.png" % i
        shutil.copy2(s.image, os.path.join(dest_dir, name))
        if rel_prefix is None:
            mapping[s.uid] = os.path.join(dest_dir, name)
        else:
            mapping[s.uid] = "%s/%s" % (rel_prefix, name)
    return mapping


def _data_uri(path):
    with open(path, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode("ascii")


def _meta_line(session):
    bits = []
    if session.author:
        bits.append(session.author)
    bits.append(datetime.date.today().isoformat())
    version = _qgis_version()
    if version:
        bits.append("QGIS %s" % version)
    return " · ".join(bits)


def _qgis_version():
    """QGIS version string, or '' when exporting outside QGIS (unit tests)."""
    try:
        from qgis.core import Qgis
    except ImportError:
        return ""
    return str(Qgis.QGIS_VERSION).split("-")[0]


def _title(session):
    return session.title or T(session.lang, "untitled")


# ----------------------------------------------------------------- markdown
def to_markdown(session, images=None, include_commands=True):
    images = images or {}
    L = session.lang
    out = ["# %s" % _title(session), "", "_%s_" % _meta_line(session), ""]
    if session.description:
        out += [session.description.strip(), ""]
    out += ["## %s" % T(L, "steps_heading"), ""]

    def img_line(step, indent):
        ref = images.get(step.uid)
        if not ref:
            return []
        return [indent + "![%s](%s)" % (strip_markup(step.text).replace("]", ""), ref.replace(" ", "%20")), ""]

    def extras(step, indent):
        lines = []
        if step.details:
            lines += [indent + T(L, "summary_title"), ""]
            lines += [indent + "- %s" % d for d in step.details] + [""]
        if include_commands and step.command:
            lines += [indent + "```" + (step.command_lang or ""),
                      ] + [indent + c for c in step.command.splitlines()] + [indent + "```", ""]
        return lines

    for b in blocks(session):
        s = b["step"]
        if b["type"] == "action":
            out.append("%d. %s" % (b["n"], s.text))
            out.append("")
            out += img_line(s, "   ")
            out += extras(s, "   ")
            for r in b["results"]:
                out.append("   - %s" % r.text)
                out.append("")
                out += img_line(r, "     ")
                out += extras(r, "     ")
        else:
            out += [s.text, ""]
            out += img_line(s, "")
            out += extras(s, "")
    out += ["---", "", "_%s_" % T(L, "generated"), ""]
    return "\n".join(out)


# --------------------------------------------------------------------- text
def to_text(session, include_commands=True):
    L = session.lang
    title = _title(session)
    out = [title, "=" * len(title), ""]
    if session.description:
        out += [session.description.strip(), ""]
    for b in blocks(session):
        s = b["step"]
        if b["type"] == "action":
            out.append("%d. %s" % (b["n"], strip_markup(s.text)))
            for d in s.details:
                out.append("     * %s" % strip_markup(d))
            if include_commands and s.command:
                out += ["     " + c for c in s.command.splitlines()]
            for r in b["results"]:
                out.append("   -> %s" % strip_markup(r.text))
                for d in r.details:
                    out.append("        * %s" % strip_markup(d))
                if include_commands and r.command:
                    out += ["        " + c for c in r.command.splitlines()]
        else:
            out += ["", strip_markup(s.text), ""]
    out += ["", "-- " + T(L, "generated")]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------- html
_CSS = """
:root{--fg:#1f2933;--muted:#667085;--bg:#f6f7f9;--card:#fff;--accent:#2e7d32;--line:#e4e7ec}
@media (prefers-color-scheme:dark){:root{--fg:#e6e9ee;--muted:#9aa4b2;--bg:#14181d;--card:#1d232a;--line:#2c343d}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans Arabic",sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 16px 64px}
h1{margin:0 0 4px;font-size:30px}
.meta{color:var(--muted);margin:0 0 20px;font-size:14px}
.desc{margin:0 0 24px}
h2{font-size:20px;margin:28px 0 12px}
.step{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:0 0 14px;display:flex;gap:14px}
.num{flex:0 0 34px;height:34px;border-radius:50%;background:var(--accent);color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center}
.body{flex:1;min-width:0}
.body p{margin:4px 0 8px}
strong{background:rgba(46,125,50,.12);padding:0 4px;border-radius:4px;font-weight:600}
code{background:rgba(127,127,127,.18);padding:1px 5px;border-radius:4px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.92em}
pre{background:#10151b;color:#e6edf3;padding:12px 14px;border-radius:8px;overflow:auto;font-size:13px;direction:ltr;text-align:left}
pre code{background:none;padding:0;color:inherit}
img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:8px;margin:6px 0;display:block}
ul.results{margin:6px 0 0;padding-inline-start:20px;color:var(--muted)}
ul.results li{margin:4px 0}
ul.results strong{color:var(--fg)}
.note{border-inline-start:4px solid var(--accent);padding:6px 14px;margin:0 0 14px;background:var(--card);border-radius:0 8px 8px 0}
.label{font-size:13px;color:var(--muted);margin:8px 0 2px}
footer{margin-top:40px;color:var(--muted);font-size:13px;text-align:center}
@media print{body{background:#fff}.step,.note{break-inside:avoid}}
"""


def build_html(session, images=None, mode="web", embed=False, include_commands=True,
               img_width=None):
    """Return an HTML string.

    mode 'web' - full styled page.   mode 'qt' - simple markup for QTextDocument.
    images: {uid: file path or relative ref}.  embed: inline images as data URIs
    (needs real paths in *images*).  img_width: callable(path)->int (qt mode).
    """
    images = images or {}
    L = session.lang
    rtl = is_rtl(L)
    d = ' dir="rtl"' if rtl else ""

    def img_tag(step):
        ref = images.get(step.uid)
        if not ref:
            return ""
        src = ref
        if mode == "web" and embed and os.path.exists(ref):
            src = _data_uri(ref)
        elif mode == "qt":
            try:
                from pathlib import Path
                src = Path(os.path.abspath(ref)).as_uri()
            except ValueError:
                log.ignored("exporter.build_html: path to URI")
                src = ref
        width = ""
        if mode == "qt":
            w = img_width(ref) if img_width else 600
            width = ' width="%d"' % min(w, 600)
        alt = _html.escape(strip_markup(step.text), quote=True)
        return '<img src="%s" alt="%s"%s>' % (_html.escape(src, quote=True), alt, width)

    def extras(step):
        h = ""
        if step.details:
            h += '<div class="label">%s</div><ul class="results">%s</ul>' % (
                _html.escape(T(L, "summary_title")),
                "".join("<li>%s</li>" % markup_to_html(x) for x in step.details))
        if include_commands and step.command:
            h += "<pre><code>%s</code></pre>" % _html.escape(step.command)
        return h

    parts = []
    for b in blocks(session):
        s = b["step"]
        if b["type"] == "action":
            res = ""
            if b["results"]:
                items = []
                for r in b["results"]:
                    items.append("<li>%s%s%s</li>" % (markup_to_html(r.text), img_tag(r), extras(r)))
                res = '<ul class="results">%s</ul>' % "".join(items)
            body = "<p%s>%s</p>%s%s%s" % (d, markup_to_html(s.text), img_tag(s), extras(s), res)
            if mode == "web":
                parts.append('<section class="step"><div class="num">%d</div><div class="body">%s</div></section>'
                             % (b["n"], body))
            else:
                parts.append("<p%s><b>%d.</b> %s</p>%s%s%s" % (
                    d, b["n"], markup_to_html(s.text), img_tag(s), extras(s),
                    ("<ul>%s</ul>" % "".join("<li>%s%s%s</li>" % (markup_to_html(r.text), img_tag(r), extras(r))
                                              for r in b["results"])) if b["results"] else ""))
        else:
            inner = "<p%s>%s</p>%s%s" % (d, markup_to_html(s.text), img_tag(s), extras(s))
            parts.append('<div class="note">%s</div>' % inner if mode == "web" else inner)

    title = _html.escape(_title(session))
    meta = _html.escape(_meta_line(session))
    desc = ("<p class=\"desc\"%s>%s</p>" % (d, _html.escape(session.description.strip()).replace("\n", "<br>"))
            if session.description else "")
    foot = _html.escape(T(L, "generated"))
    if mode == "web":
        return (
            '<!doctype html>\n<html lang="%s"%s><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>%s</title><style>%s</style></head><body><main>"
            '<h1>%s</h1><p class="meta">%s</p>%s<h2>%s</h2>%s'
            "<footer>%s</footer></main></body></html>\n"
        ) % (L, d, title, _CSS, title, meta, desc, _html.escape(T(L, "steps_heading")),
             "\n".join(parts), foot)
    return ("<html><body%s><h1>%s</h1><p><i>%s</i></p>%s<h2>%s</h2>%s<hr><p><i>%s</i></p></body></html>"
            % (d, title, meta, desc, _html.escape(T(L, "steps_heading")), "".join(parts), foot))


# --------------------------------------------------------------------- PDF
def _enum(cls, scope, name):
    try:
        return getattr(getattr(cls, scope), name)
    except AttributeError:
        return getattr(cls, name)


def export_pdf(session, path, include_commands=True):
    from qgis.PyQt.QtGui import QImage, QTextDocument
    from qgis.PyQt.QtPrintSupport import QPrinter

    folder = os.path.join(session.base_dir, "_pdf_images")
    shutil.rmtree(folder, ignore_errors=True)
    images = prepare_images(session, folder, None)

    def img_width(p):
        im = QImage(p)
        return im.width() if not im.isNull() else 600

    doc = QTextDocument()
    doc.setHtml(build_html(session, images, mode="qt", include_commands=include_commands,
                           img_width=img_width))
    printer = QPrinter(_enum(QPrinter, "PrinterMode", "ScreenResolution"))
    printer.setOutputFormat(_enum(QPrinter, "OutputFormat", "PdfFormat"))
    printer.setOutputFileName(path)
    printer_print = getattr(doc, "print_", None) or getattr(doc, "print")
    printer_print(printer)


# ------------------------------------------------------------- orchestrator
def export(session, path, fmt, embed_html=True, include_commands=True):
    """Write *session* to *path* in format *fmt* ('md','html','pdf','txt','json')."""
    stem = os.path.splitext(path)[0]
    if fmt == "md":
        folder = stem + "_images"
        images = prepare_images(session, folder, os.path.basename(folder))
        data = to_markdown(session, images, include_commands)
        _write(path, data)
    elif fmt == "html":
        if embed_html:
            tmp = os.path.join(session.base_dir, "_html_images")
            shutil.rmtree(tmp, ignore_errors=True)
            images = prepare_images(session, tmp, None)
            data = build_html(session, images, "web", True, include_commands)
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            folder = stem + "_images"
            images = prepare_images(session, folder, os.path.basename(folder))
            data = build_html(session, images, "web", False, include_commands)
        _write(path, data)
    elif fmt == "txt":
        _write(path, to_text(session, include_commands))
    elif fmt == "pdf":
        export_pdf(session, path, include_commands)
    elif fmt == "json":
        session.save(path)
    else:
        raise ValueError("Unknown format: %s" % fmt)
    return path


def _write(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(data)
