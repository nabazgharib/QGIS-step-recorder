# -*- coding: utf-8 -*-
"""Step Recorder - turns what you do in QGIS into a step-by-step tutorial."""


def classFactory(iface):  # noqa: N802 (QGIS naming)
    from .plugin import StepRecorderPlugin
    return StepRecorderPlugin(iface)
