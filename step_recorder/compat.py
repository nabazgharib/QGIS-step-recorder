# -*- coding: utf-8 -*-
"""Qt5 / Qt6 helpers so the plugin runs on QGIS 3.x (Qt5) and QGIS 4.x (Qt6)."""
from qgis.PyQt.QtCore import Qt, QEvent, QPoint, QRect, QSize  # noqa: F401
from qgis.PyQt.QtGui import QKeySequence  # noqa: F401
from qgis.PyQt.QtWidgets import (  # noqa: F401
    QToolButton, QFormLayout, QDialogButtonBox, QAbstractItemView, QDockWidget, QLineEdit,
)

try:                                    # Qt6
    from qgis.PyQt.QtGui import QAction
except ImportError:                     # Qt5
    from qgis.PyQt.QtWidgets import QAction  # noqa: F401


def enum(cls, scope, name):
    """Return enum member *name* for both Qt5 (flat) and Qt6 (scoped) styles."""
    try:
        return getattr(getattr(cls, scope), name)
    except AttributeError:
        return getattr(cls, name)


def exec_dialog(dlg):
    fn = getattr(dlg, "exec", None) or getattr(dlg, "exec_")
    return fn()


# --- event types ---------------------------------------------------------
EV_PRESS = enum(QEvent, "Type", "MouseButtonPress")
EV_RELEASE = enum(QEvent, "Type", "MouseButtonRelease")
EV_DBLCLICK = enum(QEvent, "Type", "MouseButtonDblClick")
EV_KEY = enum(QEvent, "Type", "KeyPress")
EV_SHOW = enum(QEvent, "Type", "Show")
EV_WHEEL = enum(QEvent, "Type", "Wheel")
EV_SHORTCUT = enum(QEvent, "Type", "Shortcut")
EV_FOCUSOUT = enum(QEvent, "Type", "FocusOut")
EV_FOCUSIN = enum(QEvent, "Type", "FocusIn")
WATCHED_EVENTS = frozenset([EV_PRESS, EV_RELEASE, EV_DBLCLICK, EV_KEY,
                            EV_SHOW, EV_WHEEL, EV_FOCUSOUT, EV_FOCUSIN])

# --- mouse / keys ----------------------------------------------------------
LEFT = enum(Qt, "MouseButton", "LeftButton")
RIGHT = enum(Qt, "MouseButton", "RightButton")
KEY_RETURN = enum(Qt, "Key", "Key_Return")
KEY_ENTER = enum(Qt, "Key", "Key_Enter")

# --- item data -----------------------------------------------------------
DISPLAY_ROLE = enum(Qt, "ItemDataRole", "DisplayRole")
TOOLTIP_ROLE = enum(Qt, "ItemDataRole", "ToolTipRole")
CHECKSTATE_ROLE = enum(Qt, "ItemDataRole", "CheckStateRole")
USER_ROLE = enum(Qt, "ItemDataRole", "UserRole")
CHECKED = enum(Qt, "CheckState", "Checked")
UNCHECKED = enum(Qt, "CheckState", "Unchecked")
ITEM_USER_CHECKABLE = enum(Qt, "ItemFlag", "ItemIsUserCheckable")

# --- windows ---------------------------------------------------------------
WT_POPUP = enum(Qt, "WindowType", "Popup")
WT_TOOLTIP = enum(Qt, "WindowType", "ToolTip")
WT_SPLASH = enum(Qt, "WindowType", "SplashScreen")
WT_MASK = enum(Qt, "WindowType", "WindowType_Mask")
RIGHT_DOCK_AREA = enum(Qt, "DockWidgetArea", "RightDockWidgetArea")

# --- misc enums ------------------------------------------------------------
KEYSEQ_PORTABLE = enum(QKeySequence, "SequenceFormat", "PortableText")
FORM_LABEL_ROLE = enum(QFormLayout, "ItemRole", "LabelRole")
BTN_ACCEPT_ROLE = enum(QDialogButtonBox, "ButtonRole", "AcceptRole")
BTN_APPLY_ROLE = enum(QDialogButtonBox, "ButtonRole", "ApplyRole")
DD_INTERNAL_MOVE = enum(QAbstractItemView, "DragDropMode", "InternalMove")
ALIGN_CENTER = enum(Qt, "AlignmentFlag", "AlignCenter")
KEEP_ASPECT = enum(Qt, "AspectRatioMode", "KeepAspectRatio")
SMOOTH_TRANSFORM = enum(Qt, "TransformationMode", "SmoothTransformation")
CONTEXT_CUSTOM = enum(Qt, "ContextMenuPolicy", "CustomContextMenu")
ECHO_NORMAL = enum(QLineEdit, "EchoMode", "Normal")

MOD_CTRL = enum(Qt, "KeyboardModifier", "ControlModifier")
MOD_ALT = enum(Qt, "KeyboardModifier", "AltModifier")
MOD_NONE = enum(Qt, "KeyboardModifier", "NoModifier")
TB_DELAYED_POPUP = enum(QToolButton, "ToolButtonPopupMode", "DelayedPopup")
SEQ_EXACT = enum(QKeySequence, "SequenceMatch", "ExactMatch")


def associated_widgets(action):
    """Widgets (menus, menu bars, toolbars...) an action was added to.

    Qt5: QAction.associatedWidgets().  Qt6 removed it in favour of
    associatedObjects(), which may also contain non-widget objects.
    """
    from qgis.PyQt.QtWidgets import QWidget
    fn = getattr(action, "associatedObjects", None)
    if fn is None:
        fn = getattr(action, "associatedWidgets", None)
    if fn is None:
        return []
    try:
        return [o for o in fn() if isinstance(o, QWidget)]
    except RuntimeError:
        return []
