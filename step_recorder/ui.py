# -*- coding: utf-8 -*-
"""Dock panel, options dialog and export dialog."""
import os

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget, QFileDialog,
    QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox,
    QSplitter, QTextEdit, QToolButton, QVBoxLayout, QWidget,
)

from . import exporter
from .compat import (
    ALIGN_CENTER, CHECKED, CONTEXT_CUSTOM, DD_INTERNAL_MOVE, ITEM_USER_CHECKABLE,
    LAYOUT_LTR, MSG_YES, ORIENT_VERTICAL, SMOOTH_TRANSFORM, STD_OK_CANCEL, UNCHECKED,
    USER_ROLE, exec_dialog, exec_menu,
)
from .i18n import LANGUAGES, T, is_rtl
from .model import ROLE_ACTION, ROLE_NOTE, ROLE_RESULT, Step
from .options import SPEC
from .textutils import shorten, strip_markup


def mark_ignored(w):
    """Mark a widget so the recorder never records interaction with it."""
    w.setProperty("sr_ignore", True)
    return w


# =============================================================== options
class OptionsDialog(QDialog):
    def __init__(self, options, parent=None):
        super().__init__(parent)
        mark_ignored(self)
        self.setWindowTitle("Step Recorder — Options")
        self.opt = options
        self.fields = {}
        lay = QVBoxLayout(self)
        form = QFormLayout()
        lay.addLayout(form)
        for key, (default, label, extra) in SPEC:
            cur = getattr(options, key)
            if isinstance(default, bool):
                w = QCheckBox(label)
                w.setChecked(bool(cur))
                form.addRow(w)
            elif isinstance(extra, dict):
                w = QComboBox()
                for k, v in extra.items():
                    w.addItem(v, k)
                w.setCurrentIndex(max(0, w.findData(cur)))
                form.addRow(label, w)
            elif isinstance(default, int):
                w = QSpinBox()
                w.setRange(*extra)
                w.setValue(int(cur))
                form.addRow(label, w)
            else:
                w = QLineEdit(str(cur))
                form.addRow(label, w)
            self.fields[key] = w
        bb = QDialogButtonBox(STD_OK_CANCEL)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def apply(self):
        for key, w in self.fields.items():
            if isinstance(w, QCheckBox):
                v = w.isChecked()
            elif isinstance(w, QComboBox):
                v = w.currentData()
            elif isinstance(w, QSpinBox):
                v = w.value()
            else:
                v = w.text().strip()
            setattr(self.opt, key, v)
        self.opt.save()


# =============================================================== export
class ExportDialog(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        mark_ignored(self)
        self.session = session
        self.setWindowTitle("Export tutorial")
        lay = QVBoxLayout(self)
        form = QFormLayout()
        lay.addLayout(form)
        self.fmt = QComboBox()
        for k, (label, _ext) in exporter.FORMATS.items():
            self.fmt.addItem(label.split(" (")[0], k)
        form.addRow("Format", self.fmt)
        self.embed = QCheckBox("HTML: embed screenshots in the file (single self-contained file)")
        self.embed.setChecked(True)
        self.cmds = QCheckBox("Include Python commands")
        self.cmds.setChecked(True)
        lay.addWidget(self.embed)
        lay.addWidget(self.cmds)
        self.path = QLineEdit()
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        lay.addLayout(row)
        bb = QDialogButtonBox(STD_OK_CANCEL)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.resize(520, 200)

    def _browse(self):
        k = self.fmt.currentData()
        label, ext = exporter.FORMATS[k]
        start = self.path.text() or (self.session.title or "tutorial").replace(" ", "_") + ext
        p, _ = QFileDialog.getSaveFileName(self, "Export", start, label)
        if p:
            if not p.lower().endswith(ext):
                p += ext
            self.path.setText(p)

    def _ok(self):
        if not self.path.text().strip():
            self._browse()
        if self.path.text().strip():
            self.accept()

    def run(self):
        """Returns the written path or None."""
        if not exec_dialog(self):
            return None
        k = self.fmt.currentData()
        ext = exporter.FORMATS[k][1]
        path = self.path.text().strip()
        if not path.lower().endswith(ext):
            path += ext
        exporter.export(self.session, path, k, self.embed.isChecked(), self.cmds.isChecked())
        return path


# =============================================================== dock
class StepDock(QDockWidget):
    def __init__(self, plugin, parent=None):
        super().__init__("Step Recorder", parent)
        mark_ignored(self)
        self.setObjectName("StepRecorderDock")
        self.plugin = plugin
        self.session = plugin.session
        self._busy = False
        self.session.add_listener(self._on_session_event)

        root = QWidget()
        lay = QVBoxLayout(root)
        lay.setContentsMargins(6, 6, 6, 6)

        # --- title / language -------------------------------------------
        form = QFormLayout()
        self.title = QLineEdit(self.session.title)
        self.title.setPlaceholderText("Tutorial title")
        self.title.textChanged.connect(lambda t: setattr(self.session, "title", t))
        form.addRow("Title", self.title)
        self.lang = QComboBox()
        for k, v in LANGUAGES.items():
            self.lang.addItem(v, k)
        self.lang.setCurrentIndex(max(0, self.lang.findData(plugin.options.lang)))
        self.lang.currentIndexChanged.connect(self._lang_changed)
        form.addRow("Language", self.lang)
        lay.addLayout(form)

        # --- record controls -------------------------------------------
        bar = QHBoxLayout()
        self.btn_rec = QPushButton("● Start recording")
        self.btn_rec.setCheckable(True)
        self.btn_rec.toggled.connect(self._rec_toggled)
        self.btn_note = QPushButton("+ Note")
        self.btn_note.clicked.connect(self._add_note)
        self.btn_shot = QPushButton("+ Screenshot")
        self.btn_shot.clicked.connect(self._add_shot)
        for b in (self.btn_rec, self.btn_note, self.btn_shot):
            bar.addWidget(b)
        lay.addLayout(bar)
        self.status = QLabel("")
        lay.addWidget(self.status)

        # --- step list + preview ---------------------------------------
        split = QSplitter(ORIENT_VERTICAL)
        self.list = QListWidget()
        self.list.setDragDropMode(DD_INTERNAL_MOVE)
        self.list.setContextMenuPolicy(CONTEXT_CUSTOM)
        self.list.customContextMenuRequested.connect(self._menu)
        self.list.itemChanged.connect(self._item_changed)
        self.list.itemDoubleClicked.connect(lambda it: self._edit(it))
        self.list.currentItemChanged.connect(self._show_preview)
        self.list.model().rowsMoved.connect(self._rows_moved)
        split.addWidget(self.list)
        self.preview = QLabel("Screenshot preview")
        self.preview.setAlignment(ALIGN_CENTER)
        self.preview.setMinimumHeight(120)
        split.addWidget(self.preview)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        lay.addWidget(split, 1)

        # --- bottom buttons --------------------------------------------
        row = QHBoxLayout()
        for text, fn in (("Export…", self._export), ("Save…", self._save),
                         ("Open…", self._open), ("Clear", self._clear),
                         ("Options", self._options)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        self.setWidget(root)
        self.refresh()

    # ------------------------------------------------------------ listing
    def _label(self, step, n):
        txt = strip_markup(step.text) or "(empty)"
        if step.role == ROLE_ACTION:
            prefix = "%d. " % n
        elif step.role == ROLE_RESULT:
            prefix = "    ↳ "
        else:
            prefix = "✎ "
        icon = " \U0001F5BC" if step.image else ""
        return prefix + shorten(txt, 90) + icon

    def refresh(self):
        self._busy = True
        cur = self.list.currentItem().data(USER_ROLE) if self.list.currentItem() else None
        self.list.clear()
        n = 0
        for s in self.session.steps:
            if s.role == ROLE_ACTION and s.enabled:
                n += 1
            it = QListWidgetItem(self._label(s, n))
            it.setData(USER_ROLE, s.uid)
            it.setFlags(it.flags() | ITEM_USER_CHECKABLE)
            it.setCheckState(CHECKED if s.enabled else UNCHECKED)
            it.setToolTip(strip_markup(s.text))
            self.list.addItem(it)
            if cur == s.uid:
                self.list.setCurrentItem(it)
        self._busy = False
        if self.list.currentItem() is None and self.list.count():
            self.list.scrollToBottom()
        self._update_status()

    def _update_status(self):
        n = self.session.action_count()
        state = "Recording…" if self.plugin.recorder.recording else "Stopped"
        self.status.setText("%s  •  %d step(s)" % (state, n))

    def _on_session_event(self, event, step):
        self.refresh()
        if event == "added":
            self.list.scrollToBottom()

    def _step_of(self, item):
        uid = item.data(USER_ROLE)
        for s in self.session.steps:
            if s.uid == uid:
                return s
        return None

    # ------------------------------------------------------------ actions
    def _rec_toggled(self, on):
        self.plugin.set_recording(on)
        self.btn_rec.setText("■ Stop recording" if on else "● Start recording")
        self._update_status()

    def _lang_changed(self, _i):
        self.plugin.options.lang = self.lang.currentData()
        self.session.lang = self.plugin.options.lang
        self.plugin.options.save()
        self.setLayoutDirection(LAYOUT_LTR)

    def _add_note(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add note", "Text to insert in the tutorial:")
        if ok and text.strip():
            row = self.list.currentRow()
            self.session.add(Step(text.strip(), ROLE_NOTE, "note"),
                             row + 1 if row >= 0 else None)

    def _add_shot(self):
        self.plugin.recorder.add_manual_screenshot()

    def _item_changed(self, item):
        if self._busy:
            return
        s = self._step_of(item)
        if s is not None:
            s.enabled = item.checkState() == CHECKED
            self.refresh()

    def _rows_moved(self, *a):
        if self._busy:
            return
        order = [self._step_of(self.list.item(i)) for i in range(self.list.count())]
        if all(order):
            self.session.set_order(order)

    def _edit(self, item):
        s = self._step_of(item)
        if s is None:
            return
        dlg = QDialog(self)
        mark_ignored(dlg)
        dlg.setWindowTitle("Edit step")
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Text   (use **bold** for UI names and `code` for values)"))
        te = QPlainTextEdit(s.text)
        v.addWidget(te)
        role = QComboBox()
        for k, label in ((ROLE_ACTION, "Numbered step"), (ROLE_RESULT, "Result (sub-point)"),
                         (ROLE_NOTE, "Note / paragraph")):
            role.addItem(label, k)
        role.setCurrentIndex(max(0, role.findData(s.role)))
        v.addWidget(role)
        bb = QDialogButtonBox(STD_OK_CANCEL)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        dlg.resize(460, 260)
        if exec_dialog(dlg):
            s.text = te.toPlainText().strip()
            s.role = role.currentData()
            self.session.touch(s)

    def _menu(self, pos):
        it = self.list.itemAt(pos)
        if it is None:
            return
        s = self._step_of(it)
        m = QMenu(self)
        mark_ignored(m)
        a_edit = m.addAction("Edit text…")
        a_up = m.addAction("Move up")
        a_dn = m.addAction("Move down")
        a_img = m.addAction("Remove screenshot") if s.image else None
        a_cap = m.addAction("Replace with a new screenshot of QGIS")
        a_del = m.addAction("Delete step")
        chosen = exec_menu(m, self.list.viewport().mapToGlobal(pos))
        i = self.session.steps.index(s)
        if chosen is a_edit:
            self._edit(it)
        elif chosen is a_up and i > 0:
            self.session.steps[i - 1], self.session.steps[i] = self.session.steps[i], self.session.steps[i - 1]
            self.session._fire("order")
        elif chosen is a_dn and i < len(self.session.steps) - 1:
            self.session.steps[i + 1], self.session.steps[i] = self.session.steps[i], self.session.steps[i + 1]
            self.session._fire("order")
        elif a_img is not None and chosen is a_img:
            s.image = ""
            self.session.touch(s)
        elif chosen is a_cap:
            path = self.session.new_image_path()
            if self.plugin.iface.mainWindow().grab().save(path, "PNG"):
                s.image = path
                self.session.touch(s)
        elif chosen is a_del:
            self.session.remove(s)

    def _show_preview(self, item, _prev=None):
        s = self._step_of(item) if item is not None else None
        if s is None or not s.image or not os.path.exists(s.image):
            self.preview.setPixmap(QPixmap())
            self.preview.setText("No screenshot for this step")
            return
        pm = QPixmap(s.image)
        w = max(self.preview.width() - 8, 200)
        self.preview.setPixmap(pm.scaledToWidth(w, SMOOTH_TRANSFORM) if pm.width() > w else pm)

    def _export(self):
        if not self.session.steps:
            QMessageBox.information(self, "Step Recorder", "There are no steps to export yet.")
            return
        self.session.title = self.title.text()
        self.session.lang = self.plugin.options.lang
        try:
            path = ExportDialog(self.session, self).run()
        except Exception as e:  # show, don't crash QGIS
            QMessageBox.critical(self, "Step Recorder", "Export failed:\n%s" % e)
            return
        if path:
            self.plugin.iface.messageBar().pushSuccess("Step Recorder", "Tutorial exported to %s" % path)

    def _save(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save session",
                                           (self.session.title or "session") + ".json",
                                           "Step Recorder session (*.json)")
        if p:
            self.session.save(p)

    def _open(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open session", "", "Step Recorder session (*.json)")
        if not p:
            return
        try:
            from .model import Session
            loaded = Session.load(p)
        except Exception as e:
            QMessageBox.critical(self, "Step Recorder", "Cannot open file:\n%s" % e)
            return
        self.session.title, self.session.description = loaded.title, loaded.description
        self.session.author = loaded.author
        self.session.steps = loaded.steps
        self.title.setText(loaded.title)
        self.session._fire("reset")

    def _clear(self):
        if not self.session.steps:
            return
        r = QMessageBox.question(self, "Step Recorder", "Delete all recorded steps?")
        if r == MSG_YES:
            self.session.clear()

    def _options(self):
        dlg = OptionsDialog(self.plugin.options, self)
        if exec_dialog(dlg):
            dlg.apply()
            self.lang.setCurrentIndex(max(0, self.lang.findData(self.plugin.options.lang)))

    def closeEvent(self, ev):  # noqa: N802
        self.session.remove_listener(self._on_session_event)
        super().closeEvent(ev)
