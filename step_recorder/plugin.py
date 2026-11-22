# -*- coding: utf-8 -*-
"""QGIS plugin entry point."""
import os

from qgis.PyQt.QtGui import QIcon

from .compat import QAction, RIGHT_DOCK_AREA
from .model import Session
from .options import Options
from .recorder import Recorder
from .ui import StepDock


class StepRecorderPlugin(object):
    def __init__(self, iface):
        self.iface = iface
        self.dir = os.path.dirname(__file__)
        self.options = Options().load()
        self.session = Session(author=self.options.author, lang=self.options.lang)
        self.recorder = Recorder(iface, self.session, self.options)
        self.dock = None
        self.action = None
        self.toggle = None

    # ----------------------------------------------------------- lifecycle
    def initGui(self):  # noqa: N802
        icon = QIcon(os.path.join(self.dir, "icon.png"))
        self.action = QAction(icon, "Step Recorder panel", self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self.show_dock)
        self.iface.addPluginToMenu("&Step Recorder", self.action)
        self.iface.addToolBarIcon(self.action)

        self.dock = StepDock(self, self.iface.mainWindow())
        self.iface.addDockWidget(RIGHT_DOCK_AREA, self.dock)
        self.dock.visibilityChanged.connect(self.action.setChecked)
        self.dock.hide()

    def unload(self):
        self.recorder.stop()
        if self.dock is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
        if self.action is not None:
            self.iface.removePluginMenu("&Step Recorder", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None

    # ------------------------------------------------------------- actions
    def show_dock(self, checked=True):
        if self.dock is None:
            return
        self.dock.setVisible(bool(checked))
        if checked:
            self.dock.raise_()

    def set_recording(self, on):
        if on:
            if self.options.float_dock and self.dock is not None:
                self.dock.setFloating(True)     # keeps the panel out of the screenshots
            self.recorder.start()
        else:
            self.recorder.stop()
            if self.dock is not None and self.dock.isFloating():
                self.dock.setFloating(False)
