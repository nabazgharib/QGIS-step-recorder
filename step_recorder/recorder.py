# -*- coding: utf-8 -*-
"""The recording engine: watches Qt events + QGIS signals and writes Steps."""
import functools
import time
import traceback

from qgis.PyQt.QtCore import QObject, QPoint, QRect, QTimer
from qgis.PyQt.QtGui import QKeySequence
from qgis.PyQt.QtWidgets import (
    QAbstractButton, QAbstractItemView, QAbstractSpinBox, QApplication, QCheckBox,
    QComboBox, QDialog, QDialogButtonBox, QGroupBox, QHeaderView, QLineEdit, QMenu, QMenuBar,
    QMessageBox, QPlainTextEdit, QRadioButton, QTabBar, QTextEdit, QToolButton,
    QWidget,
)

from qgis.core import Qgis, QgsApplication, QgsProject, QgsVectorLayer

from . import capture
from .compat import (
    BTN_ACCEPT_ROLE, BTN_APPLY_ROLE, associated_widgets, QAction, SEQ_EXACT, TB_DELAYED_POPUP, EV_DBLCLICK, EV_FOCUSIN, EV_FOCUSOUT, EV_KEY,
    EV_PRESS, EV_RELEASE, EV_SHOW, EV_WHEEL, KEY_ENTER, KEY_RETURN, LEFT, MOD_ALT,
    MOD_CTRL, RIGHT, WATCHED_EVENTS, WT_POPUP,
)
from .i18n import T, wrap_context, wrap_tool
from .model import ROLE_ACTION, ROLE_RESULT, Step
from .textutils import clean_text, clean_title, shorten
from . import widgets as W

try:
    from qgis.gui import QgsMapCanvas
except Exception:  # pragma: no cover
    QgsMapCanvas = None

_RUN_NAMES = ("run", "ok", "apply")
_LEVELS = {0: "Info", 1: "Warning", 2: "Critical", 3: "Success"}


def _level_name(level):
    try:
        return _LEVELS.get(int(level), "Info")
    except (TypeError, ValueError):
        name = str(level).split(".")[-1]
        return name if name in _LEVELS.values() else "Info"


class Recorder(QObject):
    def __init__(self, iface, session, options, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.win = iface.mainWindow()
        self.session = session
        self.opt = options
        self.recording = False
        self._press = None
        self._focus_vals = {}
        self._conns = []
        self._hooked_layers = set()
        self._sel_timers = {}
        self._orig_proc_run = None
        self._in_proc = False
        self._last_text = None
        self._hooked_menus = []
        self._last_err = None

    # ================================================================ control
    def start(self):
        if self.recording:
            return
        self.recording = True
        QApplication.instance().installEventFilter(self)
        self._connect_qgis()
        self._hook_all_menus()

    def stop(self):
        if not self.recording:
            return
        self.recording = False
        try:
            QApplication.instance().removeEventFilter(self)
        except RuntimeError:
            pass
        self._disconnect_qgis()
        self._unhook_menus()

    # ============================================================ step helper
    def _lang(self):
        return self.opt.lang

    def _shot(self, widget, rect=None, popup=False):
        if not self.opt.shots:
            return ""
        pm = capture.take(widget, self.win, rect, self.opt.shot_mode, self.opt.highlight,
                          self.opt.highlight_color, self.opt.highlight_width, popup)
        path = self.session.new_image_path()
        return path if capture.save(pm, path) else ""

    def _add(self, text, role=ROLE_ACTION, kind="manual", image="", details=None,
             command="", merge_key=None):
        """Append a step, de-duplicating accidental double events."""
        last = self.session.last()
        now = time.time()
        if last is not None and last.text == text and last.role == role and now - last.ts < 0.4:
            return last
        step = Step(text, role, kind, image, details, command, merge_key=merge_key)
        self.session.add(step)
        return step

    def _action_text(self, widget, key, ctx=True, **kw):
        txt = T(self._lang(), key, **kw)
        if ctx:
            txt = wrap_context(self._lang(), W.context_of(widget, self.win), txt)
        return txt

    # ============================================================ event filter
    def eventFilter(self, obj, ev):  # noqa: N802
        try:
            et = ev.type()
            if et not in WATCHED_EVENTS or not self.recording:
                return False
            if not isinstance(obj, QWidget) or W.is_ignored(obj):
                return False
            if et == EV_PRESS:
                self._on_press(obj, ev)
            elif et == EV_RELEASE:
                self._on_release(obj, ev)
            elif et == EV_DBLCLICK:
                self._on_dblclick(obj, ev)
            elif et == EV_KEY:
                self._on_key(obj, ev)
            elif et == EV_SHOW:
                self._on_show(obj)
            elif et == EV_WHEEL:
                self._on_wheel(obj, ev)
            elif et == EV_FOCUSIN:
                self._on_focus_in(obj)
            elif et == EV_FOCUSOUT:
                self._on_focus_out(obj)
        except Exception:  # never let the recorder break QGIS
            self._log_error()
        return False

    def _log_error(self):
        """Write the traceback to QGIS's log panel (View > Panels > Log Messages)."""
        try:
            from qgis.core import QgsMessageLog
            tb = traceback.format_exc()
            if tb == self._last_err:
                return
            self._last_err = tb
            try:
                level = Qgis.MessageLevel.Warning
            except AttributeError:
                level = Qgis.Warning
            QgsMessageLog.logMessage(tb, "StepRecorder", level)
        except Exception:
            pass

    # ================================================================ presses
    def _on_press(self, obj, ev):
        self._press = (obj, W.ev_pos(ev), ev.button(), time.time())

    def _on_release(self, obj, ev):
        press, self._press = self._press, None
        if press is None or press[0] is not obj:
            # menus: press happened on the menu bar; release lands on the popup
            if isinstance(obj, QMenu):
                self._on_menu_release(obj, ev)
            return
        _, ppos, pbtn, _t = press
        pos = W.ev_pos(ev)
        btn = ev.button()

        if isinstance(obj, QMenu):
            self._on_menu_release(obj, ev)
            return

        canvas = self._canvas_of(obj)
        if canvas is not None:
            self._on_map_release(canvas, ppos, pos, btn)
            return

        if btn != LEFT and btn != RIGHT:
            return
        if isinstance(obj, QAbstractButton) and btn == LEFT:
            if obj.rect().contains(pos):
                self._on_button(obj)
            return
        if isinstance(obj, QTabBar) and btn == LEFT:
            i = obj.tabAt(pos)
            if i >= 0 and i != obj.currentIndex():
                self._on_tab(obj, i)
            return
        view = self._view_of(obj)
        if view is not None:
            self._on_item(view, pos, btn, double=False)
            return
        if isinstance(obj, QHeaderView) and btn == LEFT:
            self._on_header(obj, pos)

    def _on_dblclick(self, obj, ev):
        view = self._view_of(obj)
        if view is not None and ev.button() == LEFT:
            self._on_item(view, W.ev_pos(ev), LEFT, double=True)

    # ---------------------------------------------------------------- menus
    def _on_menu_release(self, menu, ev):
        act = menu.actionAt(W.ev_pos(ev))
        if act is None or not act.isEnabled():
            return
        self._record_menu_action(act, menu, from_mouse=True)

    def _recent(self, text, within=1.5):
        last = self.session.last()
        return last is not None and last.text == text and time.time() - last.ts < within

    def _record_menu_action(self, act, menu=None, from_mouse=False):
        """Record the choice of a menu item.

        Called twice for every click - from the mouse event (gives a screenshot with
        the item highlighted) and from QMenu.triggered (works for keyboard use,
        native macOS menus and anything the mouse path missed). The second call is
        dropped as a duplicate.
        """
        if act is None or act.isSeparator() or act.menu() is not None:
            return
        holder = menu
        if holder is None or act not in holder.actions():
            holder = next((w for w in associated_widgets(act) if isinstance(w, QMenu)), None)
        if holder is None or W.is_ignored(holder):
            return
        parts, from_bar = W.menu_path(holder, act)
        if not parts or not parts[-1]:
            return
        lang = self._lang()
        if act.isCheckable():
            # on the mouse path the state is not toggled yet, on the signal path it is
            now_on = (not act.isChecked()) if from_mouse else act.isChecked()
            key = "menu_check_on" if now_on else "menu_check_off"
        else:
            key = "menu_bar" if from_bar else "menu_ctx"
        txt = T(lang, key, path=W.SEP.join(parts))
        if self._recent(txt):
            return
        image = ""
        if from_mouse:
            rect = capture.global_rect(holder, holder.actionGeometry(act))
            image = self._shot(holder, rect, popup=True)
        self._add(txt, ROLE_ACTION, "menu", image)

    def _on_menu_triggered(self, act):
        if self.recording:
            try:
                self._record_menu_action(act, None, from_mouse=False)
            except Exception:
                self._log_error()

    # ---- opening of menus / drop-down lists ----------------------------
    def _hook_menu(self, menu):
        if menu.property("sr_hooked") or W.is_ignored(menu):
            return False
        menu.setProperty("sr_hooked", True)
        slot_open = functools.partial(self._menu_about_to_show, menu)
        menu.aboutToShow.connect(slot_open)
        menu.triggered.connect(self._on_menu_triggered)
        self._hooked_menus.append((menu, slot_open))
        return True

    def _hook_all_menus(self):
        for m in self.win.findChildren(QMenu):
            try:
                self._hook_menu(m)
            except RuntimeError:
                pass

    def _unhook_menus(self):
        for menu, slot in self._hooked_menus:
            try:
                menu.aboutToShow.disconnect(slot)
                menu.triggered.disconnect(self._on_menu_triggered)
                menu.setProperty("sr_hooked", False)
            except (RuntimeError, TypeError):
                pass
        self._hooked_menus = []

    def _on_menu_show(self, menu):
        """A menu we have not hooked yet (created on the fly) was shown."""
        if self._hook_menu(menu):
            self._menu_about_to_show(menu)

    def _menu_owner(self, menu):
        """Work out what opened *menu*: ('bar'|'sub'|'button'|'context'|'popup', widget, action)."""
        ma = menu.menuAction()
        assoc = associated_widgets(ma) if ma is not None else []
        for w in assoc:
            if isinstance(w, QMenuBar):
                return ("bar", w, ma)
        for w in assoc:
            if isinstance(w, QMenu) and w is not menu:
                return ("sub", w, ma)
        press = self._press
        if press is not None and time.time() - press[3] < 3:
            p = press[0]
            for _ in range(3):
                if p is None:
                    break
                getter = getattr(p, "menu", None)
                if isinstance(p, QAbstractButton) and callable(getter):
                    try:
                        if getter() is menu:
                            return ("button", p, None)
                    except RuntimeError:
                        pass
                p = p.parentWidget()
            if press[2] == RIGHT:
                return ("context", None, None)
        return ("popup", None, None)

    def _menu_about_to_show(self, menu):
        if not (self.recording and self.opt.rec_menu_open) or W.is_ignored(menu):
            return
        try:
            info = self._menu_owner(menu)
            QTimer.singleShot(120, functools.partial(self._record_menu_open, menu, info))
        except RuntimeError:
            pass

    def _record_menu_open(self, menu, info):
        if not self.recording:
            return
        try:
            kind, owner, ma = info
            lang = self._lang()
            anchor, parent_menu = None, None
            role, step_kind = ROLE_ACTION, "menu_open"
            if kind == "bar":
                name = clean_text(ma.text())
                if not name:
                    return
                text = T(lang, "menu_open_bar", name=name)
                anchor = capture.global_rect(owner, owner.actionGeometry(ma))
            elif kind == "sub":
                name = clean_text(ma.text())
                if not name:
                    return
                text = T(lang, "menu_open_sub", name=name)
                role, step_kind = ROLE_RESULT, "menu_open_sub"
                parent_menu = owner
                anchor = capture.global_rect(owner, owner.actionGeometry(ma))
            elif kind == "button":
                name = W.button_name(owner)
                if not name:
                    return
                bar = W.toolbar_of(owner)
                if bar:
                    text = T(lang, "toolbar_menu", name=name, toolbar=bar)
                else:
                    text = wrap_context(lang, W.context_of(owner, self.win),
                                        T(lang, "toolbar_menu_nobar", name=name))
                anchor = capture.global_rect(owner)
            elif kind == "context":
                text, role, step_kind = T(lang, "menu_context"), ROLE_RESULT, "menu_open_ctx"
            else:
                text, role, step_kind = T(lang, "menu_popup"), ROLE_RESULT, "menu_open_ctx"

            image = ""
            if self.opt.shots and menu.isVisible():
                pm = capture.take_menu(menu, anchor, parent_menu, self.opt.highlight,
                                       self.opt.highlight_color, self.opt.highlight_width)
                path = self.session.new_image_path()
                image = path if capture.save(pm, path) else ""

            # Moving the mouse across the menu bar / submenus while a menu is open
            # opens other menus: keep only the last one instead of one step each.
            last = self.session.last()
            if (last is not None and last.kind == step_kind and last.kind != "menu_open_ctx"
                    and time.time() - last.ts < 10 and kind in ("bar", "sub")):
                self.session._delete_image(last)
                last.text, last.image, last.ts = text, image, time.time()
                self.session.touch(last)
                return
            self._add(text, role, step_kind, image)
        except RuntimeError:
            pass

    # -------------------------------------------------------------- buttons
    def _on_button(self, b):
        if not b.isEnabled() or isinstance(b, QGroupBox):
            return
        if isinstance(b, QToolButton) and b.menu() is not None and b.popupMode() != TB_DELAYED_POPUP:
            return                      # instant-popup buttons only open a menu
        rect = capture.global_rect(b)
        image = self._shot(b, rect)
        lang = self._lang()
        ctx = W.context_of(b, self.win)
        details, command = None, ""

        if isinstance(b, (QCheckBox, QRadioButton)) or (b.isCheckable() and b.text()):
            label = W.find_label(b)
            was = b.isChecked()
            if isinstance(b, QRadioButton):
                if was:
                    return
                key = "radio"
            else:
                key = "uncheck" if was else "check"
            txt = wrap_context(lang, ctx, T(lang, key, label=label or T(lang, "no_label")))
            self._add(txt, ROLE_ACTION, "field", image)
            return

        name = W.button_name(b)
        if not name:
            return
        bar = W.toolbar_of(b)
        label_dots = name in ("...", "…")
        if bar and isinstance(b, QToolButton):
            txt = T(lang, "toolbar_btn", name=name, toolbar=bar)
            ctx = None
        elif label_dots:
            label = W.find_label(b)
            txt = T(lang, "dots_btn", name=name, label=label or T(lang, "no_label"))
        else:
            txt = T(lang, "button", name=name)
        txt = wrap_context(lang, ctx, txt)

        win = b.window()
        if self._is_run_button(b, name) and self.opt.rec_summary and win is not self.win:
            details = W.dialog_summary(win, lang, self.opt.full_paths) or None
            if self.opt.rec_processing:
                command = self._processing_command(win)
        step = self._add(txt, ROLE_ACTION, "button", image, details, command)
        if command and self.opt.rec_processing:
            alg = getattr(win, "algorithm", None)
            try:
                aname = alg().displayName() if alg else ""
            except Exception:
                aname = ""
            if aname:
                self._add(T(lang, "proc_done", name=aname), ROLE_RESULT, "processing")

    def _is_run_button(self, b, name):
        box = b.parentWidget()
        while box is not None and not isinstance(box, QDialogButtonBox):
            box = box.parentWidget()
            if box is not None and box.isWindow():
                box = None
        if box is not None:
            try:
                role = box.buttonRole(b)
                if role in (BTN_ACCEPT_ROLE, BTN_APPLY_ROLE):
                    return True
            except (RuntimeError, TypeError):
                pass
        return name.lower().rstrip(".… ") in _RUN_NAMES

    def _processing_command(self, dialog):
        try:
            alg = dialog.algorithm()
            params = dialog.createProcessingParameters()
            from qgis.core import QgsProcessingContext
            return alg.asPythonCommand(params, QgsProcessingContext())
        except Exception:
            return ""

    def _on_tab(self, bar, i):
        name = clean_text(bar.tabText(i))
        if not name:
            return
        rect = capture.global_rect(bar, bar.tabRect(i))
        txt = wrap_context(self._lang(), W.context_of(bar, self.win),
                           T(self._lang(), "tab", name=name))
        self._add(txt, ROLE_ACTION, "tab", self._shot(bar, rect))

    # ----------------------------------------------------------- item views
    def _view_of(self, obj):
        p = obj
        for _ in range(3):
            if p is None:
                return None
            if isinstance(p, QAbstractItemView):
                return p
            p = p.parentWidget()
        return None

    def _on_item(self, view, pos, btn, double):
        if view.viewport() is None:
            return
        idx = view.indexAt(pos)
        if not idx.isValid():
            return
        text = W.index_path(idx)
        if not text:
            return
        key = "item_dbl" if double else ("item_right" if btn == RIGHT else "item_click")
        rect = capture.global_rect(view.viewport(), view.visualRect(idx))
        txt = wrap_context(self._lang(), W.context_of(view, self.win),
                           T(self._lang(), key, item=text))
        last = self.session.last()
        if double and last is not None and last.kind == "item" and \
                last.text == wrap_context(self._lang(), W.context_of(view, self.win),
                                          T(self._lang(), "item_click", item=text)):
            last.text = txt          # a double-click supersedes the first single click
            self.session.touch(last)
            return
        self._add(txt, ROLE_ACTION, "item", self._shot(view, rect))

    def _on_header(self, header, pos):
        model = header.model()
        if model is None:
            return
        i = header.logicalIndexAt(pos)
        if i < 0:
            return
        name = clean_text(str(model.headerData(i, header.orientation()) or ""))
        if name:
            txt = wrap_context(self._lang(), W.context_of(header, self.win),
                               T(self._lang(), "header_click", name=name))
            self._add(txt, ROLE_ACTION, "item")

    # ------------------------------------------------------------ map canvas
    def _canvas_of(self, obj):
        if QgsMapCanvas is None:
            return None
        p = obj
        for _ in range(3):
            if p is None:
                return None
            if isinstance(p, QgsMapCanvas):
                return p
            p = p.parentWidget()
        return None

    def _tool_name(self, canvas):
        try:
            tool = canvas.mapTool()
            if tool is None:
                return ""
            act = tool.action()
            if act is not None and act.text():
                return clean_text(act.text()).rstrip(".…")
            return clean_text(tool.toolName())
        except Exception:
            return ""

    def _coords(self, canvas, pos):
        if not self.opt.coords:
            return ""
        try:
            pt = canvas.getCoordinateTransform().toMapCoordinates(pos.x(), pos.y())
            crs = canvas.mapSettings().destinationCrs()
            dec = 5 if crs.isGeographic() else 2
            return "%.*f, %.*f (%s)" % (dec, pt.x(), dec, pt.y(), crs.authid())
        except Exception:
            return ""

    def _on_map_release(self, canvas, ppos, pos, btn):
        lang = self._lang()
        tool = self._tool_name(canvas)
        moved = abs(pos.x() - ppos.x()) + abs(pos.y() - ppos.y()) > 6
        coords = self._coords(canvas, pos)
        where = T(lang, "where", coords=coords) if coords else ""
        is_pan = tool.lower() in ("pan map", "pan", "تحريك الخريطة")
        if moved:
            if is_pan:
                txt = T(lang, "map_drag_pan")
                tool = ""
            else:
                txt = T(lang, "map_drag", where=where)
            key = ("drag", tool)
        elif btn == RIGHT:
            txt, key = T(lang, "map_rclick", where=where), ("rclick", tool)
        else:
            txt, key = T(lang, "map_click", where=where), ("click", tool)
        txt = wrap_tool(lang, tool, txt)

        last = self.session.last()
        if (self.opt.merge_clicks and key[0] == "click" and last is not None
                and last.merge_key == key and time.time() - last.ts < 30):
            last.count += 1
            base = wrap_tool(lang, tool, T(lang, "map_click_n", n=last.count))
            last.text, last.ts = base, time.time()
            self.session.touch(last)
            return
        rect = QRect(canvas.mapToGlobal(pos) - QPoint(14, 14), QRect(0, 0, 28, 28).size())
        step = self._add(txt, ROLE_ACTION, "map", self._shot(canvas, rect), merge_key=key)
        if step is not None:
            step.merge_key = key

    def _on_wheel(self, obj, ev):
        if not self.opt.rec_wheel:
            return
        canvas = self._canvas_of(obj)
        if canvas is None:
            return
        dy = ev.angleDelta().y()
        if dy == 0:
            return
        key = "wheel_in" if dy > 0 else "wheel_out"
        last = self.session.last()
        txt = T(self._lang(), key)
        if last is not None and last.kind == "wheel" and last.text == txt and time.time() - last.ts < 3:
            last.ts = time.time()
            return
        self._add(txt, ROLE_ACTION, "wheel")

    # ------------------------------------------------------------- key input
    def _on_key(self, obj, ev):
        key = ev.key()
        mods = ev.modifiers()
        if key in (KEY_RETURN, KEY_ENTER) and isinstance(obj, QLineEdit):
            self._on_focus_out(obj)   # Enter commits the value
        if not self.opt.rec_shortcuts:
            return
        if not (mods & (MOD_CTRL | MOD_ALT)):
            return
        try:
            seq = QKeySequence(ev.keyCombination())
        except AttributeError:
            seq = QKeySequence(int(mods) | key)
        keys = seq.toString()
        if not keys or keys.endswith("+"):      # only a modifier was pressed
            return
        name = ""
        for a in self.win.findChildren(QAction):
            try:
                if not a.shortcut().isEmpty() and a.shortcut().matches(seq) == SEQ_EXACT:
                    name = clean_text(a.text()).rstrip(".…")
                    break
            except Exception:
                break
        txt = T(self._lang(), "shortcut_named" if name else "shortcut", keys=keys, name=name)
        self._add(txt, ROLE_ACTION, "key")

    # ---------------------------------------------------- field value changes
    def _field_target(self, obj):
        """Return the widget whose value should be recorded for focus events on *obj*."""
        p = obj.parentWidget()
        if isinstance(obj, QLineEdit) and isinstance(p, QAbstractSpinBox):
            return p
        if isinstance(obj, QLineEdit) and isinstance(p, QComboBox):
            return None
        if isinstance(obj, (QLineEdit, QAbstractSpinBox, QTextEdit, QPlainTextEdit)):
            if isinstance(obj, QLineEdit) and (obj.isReadOnly() or obj.objectName() == "qt_spinbox_lineedit"):
                return None
            return W.logical_widget(obj)
        return None

    def _on_focus_in(self, obj):
        t = self._field_target(obj)
        if t is not None:
            self._focus_vals[id(t)] = W.widget_value(t, self._lang(), self.opt.full_paths)

    def _on_focus_out(self, obj):
        t = self._field_target(obj)
        if t is None:
            return
        old = self._focus_vals.pop(id(t), None)
        new = W.widget_value(t, self._lang(), self.opt.full_paths)
        if new is None:
            if isinstance(t, QLineEdit) and old is not None:      # a password field
                label = W.find_label(t) or T(self._lang(), "no_label")
                self._add(self._action_text(t, "text_secret", label=label), ROLE_ACTION, "field")
            return
        if new == old or new == "":
            return
        lang = self._lang()
        label = W.find_label(t) or T(lang, "no_label")
        if isinstance(t, (QTextEdit, QPlainTextEdit)) or "Qsci" in type(t).__name__:
            key = "text_block"
        elif isinstance(t, QAbstractSpinBox):
            key = "set_value"
        else:
            key = "text"
        txt = self._action_text(t, key, label=label, value=new)
        self._add(txt, ROLE_ACTION, "field", self._shot(t, capture.global_rect(t)))

    def _on_combo(self, combo, _index=0):
        if not self.recording or W.is_ignored(combo):
            return
        try:
            val = clean_text(combo.currentText())
            if not val:
                return
            label = W.find_label(combo) or T(self._lang(), "no_label")
            txt = self._action_text(combo, "combo", label=label, value=val)
            self._add(txt, ROLE_ACTION, "field", self._shot(combo, capture.global_rect(combo)))
        except RuntimeError:
            pass

    # ------------------------------------------------------- dialogs opening
    def _on_show(self, obj):
        if isinstance(obj, QMenu):
            self._on_menu_show(obj)
            return
        if not obj.isWindow() or obj.property("sr_seen"):
            return
        if not isinstance(obj, QDialog) or obj is self.win:
            return
        if obj.windowType() == WT_POPUP:
            return
        obj.setProperty("sr_seen", True)
        for combo in obj.findChildren(QComboBox):
            if not combo.property("sr_hooked"):
                combo.setProperty("sr_hooked", True)
                combo.activated.connect(functools.partial(self._on_combo, combo))
        if not self.opt.rec_dialogs:
            return
        lang = self._lang()
        if isinstance(obj, QMessageBox):
            text = shorten(clean_text(obj.text()), 200)
            if text:
                QTimer.singleShot(150, lambda o=obj, t=text: self._late_dialog(
                    o, T(lang, "msgbox", text=t), "msgbox"))
            return
        title = clean_title(obj.windowTitle())
        if title:
            QTimer.singleShot(350, lambda o=obj, t=title: self._late_dialog(
                o, T(lang, "dialog_open", title=t), "dialog"))

    def _late_dialog(self, dlg, text, kind):
        if not self.recording:
            return
        try:
            if not dlg.isVisible():
                return
            img = self._shot(dlg, None) if self.opt.shots_dialogs else ""
            self._add(text, ROLE_RESULT, kind, img)
        except RuntimeError:
            pass

    # ======================================================== QGIS signal hooks
    def _link(self, signal, slot):
        try:
            signal.connect(slot)
            self._conns.append((signal, slot))
        except Exception:
            pass

    def _connect_qgis(self):
        proj = QgsProject.instance()
        self._link(proj.layersAdded, self._on_layers_added)
        self._link(proj.layersWillBeRemoved, self._on_layers_removed)
        self._link(proj.projectSaved, self._on_saved)
        try:
            self._link(proj.crsChanged, self._on_crs)
        except AttributeError:
            pass
        for sig in ("newProjectCreated", "projectRead"):
            s = getattr(self.iface, sig, None)
            if s is not None:
                self._link(s, getattr(self, "_on_" + sig))
        try:
            self._link(self.iface.messageBar().widgetAdded, self._on_msgbar)
        except Exception:
            pass
        for layer in proj.mapLayers().values():
            self._hook_layer(layer)
        self._patch_processing()

    def _disconnect_qgis(self):
        for sig, slot in self._conns:
            try:
                sig.disconnect(slot)
            except Exception:
                pass
        self._conns = []
        self._hooked_layers = set()
        for t in self._sel_timers.values():
            t.stop()
        self._sel_timers = {}
        self._unpatch_processing()

    def _hook_layer(self, layer):
        if not isinstance(layer, QgsVectorLayer) or layer.id() in self._hooked_layers:
            return
        self._hooked_layers.add(layer.id())
        lid = layer.id()
        self._link(layer.editingStarted, functools.partial(self._on_edit, lid, True))
        self._link(layer.editingStopped, functools.partial(self._on_edit, lid, False))
        self._link(layer.selectionChanged, functools.partial(self._on_selection, lid))

    def _layer(self, lid):
        return QgsProject.instance().mapLayer(lid)

    def _result(self, text, kind):
        self._add(text, ROLE_RESULT, kind)

    def _on_layers_added(self, layers):
        if not self.opt.rec_layers:
            return
        for lyr in layers:
            self._hook_layer(lyr)
        names = ", ".join("**%s**" % l.name() for l in layers)
        lang = self._lang()
        self._result(T(lang, "layer_added", name=layers[0].name()) if len(layers) == 1
                     else T(lang, "layers_added", n=len(layers), names=names), "layer")

    def _on_layers_removed(self, ids):
        if not self.opt.rec_layers:
            return
        layers = [self._layer(i) for i in ids]
        layers = [l for l in layers if l is not None]
        if not layers:
            return
        lang = self._lang()
        names = ", ".join("**%s**" % l.name() for l in layers)
        self._result(T(lang, "layer_removed", name=layers[0].name()) if len(layers) == 1
                     else T(lang, "layers_removed", n=len(layers), names=names), "layer")

    def _on_edit(self, lid, started, *a):
        if not self.opt.rec_layers:
            return
        lyr = self._layer(lid)
        if lyr is not None:
            self._result(T(self._lang(), "edit_on" if started else "edit_off", name=lyr.name()), "layer")

    def _on_selection(self, lid, *a):
        if not (self.opt.rec_selection and self.recording):
            return
        t = self._sel_timers.get(lid)
        if t is None:
            t = QTimer(self)
            t.setSingleShot(True)
            t.timeout.connect(functools.partial(self._flush_selection, lid))
            self._sel_timers[lid] = t
        t.start(400)

    def _flush_selection(self, lid):
        lyr = self._layer(lid)
        if lyr is None:
            return
        n = lyr.selectedFeatureCount()
        lang = self._lang()
        self._result(T(lang, "selected", n=n, name=lyr.name()) if n
                     else T(lang, "sel_cleared", name=lyr.name()), "selection")

    def _on_msgbar(self, item):
        if not self.opt.rec_messages:
            return
        try:
            text = " ".join(x for x in (clean_text(item.title()).rstrip(":"), clean_text(item.text())) if x)
            if not text:
                return
            lang = self._lang()
            lvl = T(lang, "lvl_" + _level_name(item.level()))
            self._result(T(lang, "msgbar", level=lvl, text=shorten(text, 220)), "message")
        except Exception:
            pass

    def _on_saved(self, *a):
        where = ""
        path = QgsProject.instance().fileName()
        if path:
            import os
            where = " (%s)" % (path if self.opt.full_paths else os.path.basename(path))
        self._result(T(self._lang(), "proj_saved", where=where), "project")

    def _on_newProjectCreated(self, *a):  # noqa: N802
        self._result(T(self._lang(), "proj_new"), "project")
        self._hooked_layers = set()

    def _on_projectRead(self, *a):  # noqa: N802
        import os
        path = QgsProject.instance().fileName()
        self._hooked_layers = set()
        for layer in QgsProject.instance().mapLayers().values():
            self._hook_layer(layer)
        if path:
            self._result(T(self._lang(), "proj_read", name=os.path.basename(path)), "project")

    def _on_crs(self, *a):
        crs = QgsProject.instance().crs()
        if crs.isValid():
            self._result(T(self._lang(), "crs_changed", value=crs.authid() or crs.description()), "project")

    # ----------------------------------------------- Python-console processing
    def _patch_processing(self):
        if not self.opt.rec_processing or self._orig_proc_run is not None:
            return
        try:
            import processing
        except Exception:
            return
        self._orig_proc_run = processing.run
        rec = self

        @functools.wraps(processing.run)
        def run(algOrName, parameters, *args, **kwargs):  # noqa: N803
            res = rec._orig_proc_run(algOrName, parameters, *args, **kwargs)
            try:
                if rec.recording and not rec._in_proc:
                    rec._record_python_run(algOrName, parameters)
            except Exception:
                pass
            return res
        processing.run = run

    def _unpatch_processing(self):
        if self._orig_proc_run is None:
            return
        try:
            import processing
            processing.run = self._orig_proc_run
        except Exception:
            pass
        self._orig_proc_run = None

    def _record_python_run(self, alg_or_name, params):
        import pprint
        alg_id = alg_or_name if isinstance(alg_or_name, str) else alg_or_name.id()
        alg = QgsApplication.processingRegistry().algorithmById(alg_id)
        name = alg.displayName() if alg is not None else alg_id
        safe = {}
        for k, v in (params or {}).items():
            safe[k] = v if isinstance(v, (str, int, float, bool, type(None), list, tuple, dict)) else str(v)
        cmd = "processing.run(%r, %s)" % (alg_id, pprint.pformat(safe, width=80, sort_dicts=False))
        self._add(T(self._lang(), "py_run", name=name), ROLE_ACTION, "command", "", None, cmd)

    # ====================================================== manual additions
    def add_note(self, text):
        self.session.add(Step(text, "note", "note"))

    def add_manual_screenshot(self, text=""):
        path = self.session.new_image_path()
        pm = self.win.grab()
        if capture.save(pm, path):
            self.session.add(Step(text or "", "note", "screenshot", path))
