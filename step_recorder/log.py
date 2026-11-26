# -*- coding: utf-8 -*-
"""Logging helpers: no exception is ever swallowed silently.

ignored(where) - an expected, harmless failure (e.g. a Qt object that was already
                 deleted). Logged at DEBUG level through the standard logging module.
warn(where)    - an unexpected failure that must not break QGIS. Written once to
                 QGIS's Log Messages panel (tab "StepRecorder") with its traceback.

Call both from inside an ``except`` block. No Qt/QGIS import at module level, so the
pure-Python modules and the unit tests can use it too.
"""
import logging
import traceback

_logger = logging.getLogger("step_recorder")
_seen = set()
_MAX_SEEN = 200


def ignored(where):
    _logger.debug("ignored error in %s", where, exc_info=True)


def warn(where):
    tb = traceback.format_exc()
    key = (where, tb)
    if key in _seen:
        return
    if len(_seen) < _MAX_SEEN:
        _seen.add(key)
    _logger.warning("error in %s\n%s", where, tb)
    try:
        from qgis.core import Qgis, QgsMessageLog
    except ImportError:          # not running inside QGIS (unit tests)
        return
    levels = getattr(Qgis, "MessageLevel", Qgis)     # QGIS >= 3.28 scopes the enum
    level = getattr(levels, "Warning")
    QgsMessageLog.logMessage("%s\n%s" % (where, tb), "StepRecorder", level)
