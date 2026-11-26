# -*- coding: utf-8 -*-
"""Helpers that look at Qt widgets and work out human-readable names."""
import os

from qgis.PyQt.QtWidgets import (
    QAbstractSpinBox, QCheckBox, QComboBox, QDockWidget, QFormLayout,
    QGridLayout, QGroupBox, QLabel, QLineEdit, QMenu, QMenuBar, QPlainTextEdit,
    QRadioButton, QTextEdit, QToolBar, QToolButton, QWidget,
)

from .compat import associated_widgets, DISPLAY_ROLE, ECHO_NORMAL, FORM_LABEL_ROLE, TOOLTIP_ROLE
from . import log
from .i18n import T
from .textutils import clean_label, clean_text, clean_title, pretty_name, shorten

try:
    from qgis.PyQt.Qsci import QsciScintilla
except ImportError:  # pragma: no cover
    QsciScintilla = None

# widgets that are made of several child widgets - we record the outer one
COMPOSITE_NAMES = frozenset([
    "QgsFileWidget", "QgsProjectionSelectionWidget",
    "QgsFieldExpressionWidget", "QgsExpressionLineEdit",
])

SEP = " ▸ "


def mro_names(w):
    return set(c.__name__ for c in type(w).__mro__)


def ev_pos(ev):
    try:
        return ev.position().toPoint()
    except AttributeError:
        return ev.pos()


def is_ignored(w):
    """True when *w* belongs to the Step Recorder UI itself."""
    while w is not None:
        try:
            if w.property("sr_ignore"):
                return True
            w = w.parentWidget()
        except RuntimeError:
            return True
    return False


# ----------------------------------------------------------------- labels
def logical_widget(w):
    """Outermost composite widget that contains *w* (or *w* itself)."""
    top, p, depth = w, w.parentWidget(), 0
    while p is not None and depth < 4 and not p.isWindow():
        if mro_names(p) & COMPOSITE_NAMES:
            top = p
        p, depth = p.parentWidget(), depth + 1
    return top


def _text_of(wid):
    if isinstance(wid, QLabel):
        return clean_label(wid.text())
    if isinstance(wid, (QCheckBox, QRadioButton)):
        return clean_label(wid.text())
    return ""


def _locate_chain(layout, w):
    """[(layout, index), ...] from outer to inner layout holding *w*; [] if absent."""
    for i in range(layout.count()):
        it = layout.itemAt(i)
        if it is None:
            continue
        if it.widget() is w:
            return [(layout, i)]
        sub = it.layout()
        if sub is not None:
            chain = _locate_chain(sub, w)
            if chain:
                return [(layout, i)] + chain
    return []


def _label_from_layout(lay, idx):
    """Label text sitting before item *idx* of layout *lay*."""
    try:
        if isinstance(lay, QFormLayout):
            row, _role = lay.getItemPosition(idx)
            if row >= 0:
                it = lay.itemAt(row, FORM_LABEL_ROLE)
                if it is not None and it.widget() is not None:
                    return _text_of(it.widget())
            return ""
        if isinstance(lay, QGridLayout):
            r, c = lay.getItemPosition(idx)[:2]
            for rr, cc in ((r, c - 1), (r - 1, c)):
                if rr >= 0 and cc >= 0:
                    it = lay.itemAtPosition(rr, cc)
                    if it is not None and it.widget() is not None:
                        t = _text_of(it.widget())
                        if t:
                            return t
            return ""
        j = idx - 1
        if j >= 0:
            it = lay.itemAt(j)
            if it is not None and it.widget() is not None:
                return _text_of(it.widget())
    except (RuntimeError, TypeError, ValueError):
        log.ignored("widgets._label_from_layout")
    return ""


def _label_for(w):
    # 1. explicit buddy
    win = w.window()
    if win is not None:
        for lbl in win.findChildren(QLabel):
            try:
                if lbl.buddy() is w:
                    t = clean_label(lbl.text())
                    if t:
                        return t
            except RuntimeError:
                log.ignored("widgets._label_for")
                continue
    # 2. neighbour label in the parent's layout
    par = w.parentWidget()
    if par is not None and par.layout() is not None:
        chain = _locate_chain(par.layout(), w)
        for lay, idx in reversed(chain):
            t = _label_from_layout(lay, idx)
            if t:
                return t
    return ""


def fallback_label(w):
    if isinstance(w, QLineEdit) and w.placeholderText():
        return clean_label(w.placeholderText())
    for t in (w.accessibleName(), w.toolTip()):
        t = clean_label(t)
        if t:
            return shorten(t.split(".")[0], 40)
    return pretty_name(w.objectName())


def find_label(widget):
    """Best human label for an input widget ('' when none can be found)."""
    if isinstance(widget, (QCheckBox, QRadioButton)):
        t = clean_label(widget.text())
        if t:
            return t
    if isinstance(widget, QGroupBox) and widget.title():
        return clean_label(widget.title())
    w = logical_widget(widget)
    cur = w
    for _ in range(4):
        t = _label_for(cur)
        if t:
            return t
        cur = cur.parentWidget()
        if cur is None or cur.isWindow():
            break
    return fallback_label(w)


# ----------------------------------------------------------------- context
def context_of(w, main_window):
    """('dialog'|'panel', title) describing where *w* lives, or None."""
    win = w.window()
    if win is None or win is main_window:
        p = w
        while p is not None and p is not main_window:
            if isinstance(p, QDockWidget):
                t = clean_title(p.windowTitle())
                if t:
                    return ("panel", t)
            p = p.parentWidget()
        return None
    if isinstance(win, QMenu):
        return None
    t = clean_title(win.windowTitle())
    if not t:
        return None
    return ("panel", t) if isinstance(win, QDockWidget) else ("dialog", t)


def toolbar_of(w):
    p = w.parentWidget()
    if isinstance(p, QToolBar):
        return clean_title(p.windowTitle()) or pretty_name(p.objectName())
    return ""


# ----------------------------------------------------------------- names
def button_name(b):
    t = clean_text(b.text())
    if not t and isinstance(b, QToolButton) and b.defaultAction() is not None:
        t = clean_text(b.defaultAction().text())
    if not t:
        t = clean_text(b.toolTip())
    if not t:
        t = pretty_name(b.objectName())
    return t


def menu_path(menu, action):
    """(['File', 'Open Recent', 'x.qgz'], from_menubar) for an action in *menu*."""
    parts = [clean_text(action.text())]
    cur, seen, from_bar = menu, set(), False
    while isinstance(cur, QMenu) and id(cur) not in seen:
        seen.add(id(cur))
        ma = cur.menuAction()
        txt = clean_text(ma.text()) if ma is not None else ""
        if not txt:
            txt = clean_text(cur.title())
        parent = None
        if ma is not None:
            for aw in associated_widgets(ma):
                if aw is not cur and isinstance(aw, (QMenu, QMenuBar)):
                    parent = aw
                    break
        if txt and (parent is not None):
            parts.insert(0, txt)
        if isinstance(parent, QMenuBar):
            from_bar = True
            break
        cur = parent
    return parts, from_bar


def index_path(idx, depth=4):
    """'Vector geometry ▸ Buffer' for a model index (walks up the parents)."""
    parts = []
    while idx.isValid() and len(parts) < depth:
        t = idx.data(DISPLAY_ROLE)
        t = clean_text(t if isinstance(t, str) else "")
        if not t:
            tt = idx.data(TOOLTIP_ROLE)
            t = clean_text(tt if isinstance(tt, str) else "")
            t = t.splitlines()[0] if t else ""
        if t:
            parts.insert(0, shorten(t, 60))
        idx = idx.parent()
    return SEP.join(parts)


# ------------------------------------------------------------------ values
def widget_value(w, lang="en", full_paths=False):
    """Text describing the current value of an input widget, or None."""
    names = mro_names(w)
    try:
        if "QgsFileWidget" in names:
            p = w.filePath()
            if not full_paths and p:
                p = os.path.basename(p.rstrip("/\\")) or p
            return p
        if "QgsProjectionSelectionWidget" in names:
            crs = w.crs()
            return (crs.authid() or crs.description()) if crs.isValid() else ""
        if "QgsColorButton" in names:
            return w.color().name()
        if isinstance(w, QComboBox):
            if "QgsCheckableComboBox" in names:
                return ", ".join(w.checkedItems())
            return clean_text(w.currentText())
        if isinstance(w, QAbstractSpinBox):
            return clean_text(w.text())
        if isinstance(w, QLineEdit):
            if w.echoMode() != ECHO_NORMAL:      # never record passwords
                return None
            return w.text()
        if isinstance(w, QCheckBox):             # only checked boxes are interesting
            return T(lang, "val_on") if w.isChecked() else None
        if isinstance(w, QRadioButton):
            return T(lang, "val_sel") if w.isChecked() else None
        if isinstance(w, (QTextEdit, QPlainTextEdit)):
            return shorten(w.toPlainText().strip(), 80)
        if QsciScintilla is not None and isinstance(w, QsciScintilla):
            return shorten(w.text().strip(), 80)
    except (RuntimeError, AttributeError, TypeError):
        return None
    return None


def dialog_summary(dialog, lang="en", full_paths=False):
    """['**Label**: `value`', ...] for the visible inputs of *dialog*."""
    rows, seen = [], set()
    for w in dialog.findChildren(QWidget):
        try:
            if not w.isVisibleTo(dialog) or not w.isEnabled():
                continue
            if is_ignored(w) or logical_widget(w) is not w:
                continue
            if isinstance(w, QLineEdit) and (w.isReadOnly() or w.objectName() == "qt_spinbox_lineedit"):
                continue
            val = widget_value(w, lang, full_paths)
            if val is None or val == "":
                continue
            label = find_label(w) or T(lang, "no_label")
        except RuntimeError:
            log.ignored("widgets.dialog_summary")
            continue
        key = (label, val)
        if key in seen:
            continue
        seen.add(key)
        rows.append("**%s**: `%s`" % (label, val))
    return rows
