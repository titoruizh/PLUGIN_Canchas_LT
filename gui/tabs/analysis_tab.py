# -*- coding: utf-8 -*-
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QLabel, QHBoxLayout)

from .analysis.table_subtab import TableSubTab
from .analysis.volumes_subtab import VolumesSubTab
from .analysis.xml_subtab import XmlSubTab

class AnalysisTab(QWidget):
    """
    Pestaña 3: Análisis Completo
    Contenedor para las sub-pestañas de Tabla, Volúmenes y XML.
    Agrupa y delega las señales al controlador principal.
    """
    
    # Señales agregadas
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    save_settings_signal = pyqtSignal() # Señal para pedir que se guarden settings tras éxito
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()
        
    def setupUi(self):
        layout = QVBoxLayout()
        
        # Título principal
        header_layout = QHBoxLayout()
        icon_label = QLabel("📊")
        icon_label.setStyleSheet("font-size: 24px; margin-right: 10px;")
        title_label = QLabel("ANÁLISIS COMPLETO")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #F18F01;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Widget de pestañas interno
        self.sub_tab_widget = QTabWidget()
        
        # Instanciar sub-pestañas
        self.table_tab = TableSubTab()
        self.volumes_tab = VolumesSubTab()
        self.xml_tab = XmlSubTab()
        
        # Conectar señales de sub-pestañas a señales de esta pestaña
        self.connect_subtab(self.table_tab)
        self.connect_subtab(self.volumes_tab)
        self.connect_subtab(self.xml_tab)
        
        # Agregar al TabWidget
        self.sub_tab_widget.addTab(self.table_tab, "3.1 Tabla")
        self.sub_tab_widget.addTab(self.volumes_tab, "3.2 Vol+Screenshots")
        self.sub_tab_widget.addTab(self.xml_tab, "3.3 XML")
        
        layout.addWidget(self.sub_tab_widget)
        self.setLayout(layout)
        
    def connect_subtab(self, subtab):
        """Conecta las señales de log y progreso de un subtab"""
        subtab.log_signal.connect(self.log_signal.emit)
        subtab.progress_signal.connect(self.progress_signal.emit)
        
    def ejecutar_tabla(self, proc_root):
        """Ejecuta proceso de tabla usando el subtab"""
        if self.table_tab.ejecutar_tabla(proc_root):
            self.save_settings_signal.emit()
            return True
        return False

    def ejecutar_volumenes(self, proc_root):
        """Ejecuta proceso de volúmenes usando el subtab"""
        if self.volumes_tab.ejecutar_volumenes_pantallazos(proc_root):
            self.save_settings_signal.emit()
            return True
        return False
        
    def ejecutar_xml(self, proc_root):
        """Ejecuta proceso XML usando el subtab"""
        return self.xml_tab.ejecutar_xml(proc_root)
