# -*- coding: utf-8 -*-
"""Screenshots with a highlight rectangle around the element that was used."""
from qgis.PyQt.QtCore import QPoint, QRect
from qgis.PyQt.QtGui import QColor, QGuiApplication, QPainter, QPen
from qgis.PyQt.QtWidgets import QApplication, QMenu

from .compat import WT_POPUP, enum

_ANTIALIAS = enum(QPainter, "RenderHint", "Antialiasing")


def global_rect(widget, local_rect=None):
    """Rectangle of *widget* (or of *local_rect* inside it) in screen coordinates."""
    top_left = widget.mapToGlobal(QPoint(0, 0))
    if local_rect is None:
        return QRect(top_left, widget.size())
    return QRect(local_rect).translated(top_left)


def _is_popup(win):
    try:
        return isinstance(win, QMenu) or win.windowType() == WT_POPUP
    except (RuntimeError, AttributeError):
        return isinstance(win, QMenu)


def anchor_window(widget, main_window):
    """Window whose picture best explains a click on *widget*."""
    win = widget.window()
    if _is_popup(win):
        return QApplication.activeModalWidget() or main_window
    return win


def _grab_screen(win, extra_rect):
    screen = None
    handle = win.windowHandle() if hasattr(win, "windowHandle") else None
    if handle is not None:
        screen = handle.screen()
    screen = screen or QGuiApplication.primaryScreen()
    if screen is None:
        return None, None
    region = QRect(win.mapToGlobal(QPoint(0, 0)), win.size())
    if extra_rect is not None:
        region = region.united(extra_rect.adjusted(-16, -16, 16, 16))
    region = region.intersected(screen.geometry())
    if region.isEmpty():
        return None, None
    rel = region.translated(-screen.geometry().topLeft())
    pm = screen.grabWindow(0, rel.x(), rel.y(), rel.width(), rel.height())
    if pm.isNull():
        return None, None
    return pm, region.topLeft()


def take(widget, main_window, rect=None, mode="window", highlight=True,
         color="#e53935", width=3, popup_is_target=False):
    """Grab a picture; returns a QPixmap or None.

    widget : the widget that was used
    rect   : its rectangle in global coordinates (highlighted)
    mode   : 'window' (this window only) or 'screen' (screen area around it)
    popup_is_target : grab the popup (menu) itself instead of the window below
    """
    try:
        if popup_is_target:
            win = widget.window()
        else:
            win = anchor_window(widget, main_window)
        if win is None:
            return None
        pm, origin = None, None
        if mode == "screen":
            pm, origin = _grab_screen(win, rect)
        if pm is None:                       # 'window' mode, or screen grab refused (Wayland)
            pm = win.grab()
            origin = win.mapToGlobal(QPoint(0, 0))
        if pm is None or pm.isNull():
            return None
        if highlight and rect is not None:
            local = rect.translated(-origin.x(), -origin.y())
            p = QPainter(pm)
            p.setRenderHint(_ANTIALIAS, True)
            pen = QPen(QColor(color))
            pen.setWidth(int(width))
            p.setPen(pen)
            p.drawRoundedRect(local.adjusted(-2, -2, 2, 2), 4, 4)
            p.end()
        return pm
    except (RuntimeError, AttributeError, TypeError):
        return None


def save(pixmap, path):
    return bool(pixmap is not None and pixmap.save(path, "PNG"))


def take_menu(menu, anchor_rect=None, parent_menu=None, highlight=True,
              color="#e53935", width=3):
    """Picture of an open menu together with the thing that opened it.

    menu        : the popup that is showing
    anchor_rect : global rect of the menu-bar title / button / parent item (highlighted)
    parent_menu : for a submenu, the menu that contains it (included in the picture)
    Falls back to a picture of the menu alone when screen grabbing is refused.
    """
    try:
        region = QRect(menu.mapToGlobal(QPoint(0, 0)), menu.size())
        if parent_menu is not None:
            region = region.united(QRect(parent_menu.mapToGlobal(QPoint(0, 0)), parent_menu.size()))
        if anchor_rect is not None:
            region = region.united(anchor_rect.adjusted(-24, -24, 24, 24))
        handle = menu.windowHandle() if hasattr(menu, "windowHandle") else None
        screen = (handle.screen() if handle is not None else None) or QGuiApplication.primaryScreen()
        pm, origin = None, None
        if screen is not None and menu.isVisible():
            region = region.intersected(screen.geometry())
            if not region.isEmpty():
                rel = region.translated(-screen.geometry().topLeft())
                pm = screen.grabWindow(0, rel.x(), rel.y(), rel.width(), rel.height())
                origin = region.topLeft()
        if pm is None or pm.isNull():
            if not menu.isVisible():
                return None
            pm = menu.grab()
            origin, anchor_rect = None, None
        if highlight and anchor_rect is not None and origin is not None:
            local = anchor_rect.translated(-origin.x(), -origin.y())
            p = QPainter(pm)
            p.setRenderHint(_ANTIALIAS, True)
            pen = QPen(QColor(color))
            pen.setWidth(int(width))
            p.setPen(pen)
            p.drawRoundedRect(local.adjusted(-2, -2, 2, 2), 4, 4)
            p.end()
        return pm
    except (RuntimeError, AttributeError, TypeError):
        return None
