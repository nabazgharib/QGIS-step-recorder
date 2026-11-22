# -*- coding: utf-8 -*-
"""User options, stored in QGIS settings under 'StepRecorder/'."""

from .i18n import LANGUAGES

# key: (default, label, choices-or-None)
SPEC = [
    ("lang", ("en", "Instruction language", LANGUAGES)),
    ("shots", (True, "Take a screenshot for every action", None)),
    ("shots_dialogs", (True, "Take a screenshot when a dialog opens", None)),
    ("shot_mode", ("window", "Screenshot area",
                   {"window": "Active window only",
                    "screen": "Whole screen around the window (needs X11/Windows/macOS)"})),
    ("highlight", (True, "Highlight the clicked element in the screenshot", None)),
    ("highlight_color", ("#e53935", "Highlight colour (#RRGGBB)", None)),
    ("highlight_width", (3, "Highlight line width (px)", (1, 10))),
    ("rec_menu_open", (True, "Record opening of menus and drop-down lists (with screenshot)", None)),
    ("rec_dialogs", (True, "Record 'dialog opens' and message boxes", None)),
    ("rec_messages", (True, "Record message-bar messages", None)),
    ("rec_layers", (True, "Record layers added/removed and edit mode", None)),
    ("rec_selection", (True, "Record feature selection results", None)),
    ("rec_processing", (True, "Record Processing algorithm runs (with Python command)", None)),
    ("rec_wheel", (True, "Record mouse-wheel zoom on the map", None)),
    ("rec_shortcuts", (True, "Record keyboard shortcuts", None)),
    ("rec_summary", (True, "Add a 'Settings used' list when pressing Run / OK / Apply", None)),
    ("coords", (True, "Include map coordinates for map clicks", None)),
    ("merge_clicks", (True, "Merge repeated map clicks into one step", None)),
    ("full_paths", (False, "Show full file paths (instead of file names only)", None)),
    ("float_dock", (True, "Float the recorder panel while recording (keeps it out of screenshots)", None)),
    ("author", ("", "Default author name", None)),
]

DEFAULTS = dict((k, v[0]) for k, v in SPEC)
PREFIX = "StepRecorder/"


class Options(object):
    def __init__(self):
        for k, v in DEFAULTS.items():
            setattr(self, k, v)

    def load(self):
        from qgis.core import QgsSettings
        s = QgsSettings()
        for k, default in DEFAULTS.items():
            val = s.value(PREFIX + k, default)
            if isinstance(default, bool):
                val = val in (True, "true", "True", 1, "1")
            elif isinstance(default, int):
                try:
                    val = int(val)
                except (TypeError, ValueError):
                    val = default
            else:
                val = str(val) if val is not None else default
            setattr(self, k, val)
        return self

    def save(self):
        from qgis.core import QgsSettings
        s = QgsSettings()
        for k in DEFAULTS:
            s.setValue(PREFIX + k, getattr(self, k))
