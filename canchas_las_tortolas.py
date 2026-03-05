# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsProject, QgsMessageLog, Qgis

class CanchasLasTortolas:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor."""
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = '&Canchas Las Tortolas'

    def add_action(
        self,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar."""

        # Usar icono por defecto de QGIS en lugar de archivo
        icon = QIcon(':/plugins/processing/images/toolbox.svg')

        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        # Acción principal: Pipeline Lineal (nueva UI)
        self.add_action(
            text='🟠 Canchas LT — Pipeline',
            callback=self.run,
            parent=self.iface.mainWindow())

        # Acción secundaria: Modo Experto (pestañas originales)
        self.add_action(
            text='⚙️ Canchas LT — Modo Experto',
            callback=self.run_expert,
            add_to_toolbar=False,  # Solo en menú, no en barra de herramientas
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                '&Canchas Las Tortolas',
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Abre el Pipeline Lineal (nueva ventana unificada)."""
        from .gui.pipeline_dialog import PipelineDialog
        dialog = PipelineDialog(parent=self.iface.mainWindow())
        dialog.exec_()

    def run_expert(self):
        """Abre el modo experto con pestañas (UI original — respaldo)."""
        from .canchas_dialog import CanchasDialog
        dialog = CanchasDialog()
        dialog.exec_()