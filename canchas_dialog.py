# -*- coding: utf-8 -*-
import os
from qgis.PyQt import QtWidgets, QtCore
from qgis.PyQt.QtCore import pyqtSignal, QThread, QSettings, QTime
from qgis.PyQt.QtWidgets import (QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, 
                                QPushButton, QTextEdit, QProgressBar, QLabel, 
                                QLineEdit, QFileDialog)
from .gui.tabs.validation_tab import ValidationTab
from .gui.tabs.processing_tab import ProcessingTab
from .gui.tabs.analysis_tab import AnalysisTab
from .gui.tabs.reports_tab import ReportsTab

class CanchasDialog(QDialog):
    """Diálogo principal del plugin con pestañas reorganizado"""
    
    def __init__(self):
        super(CanchasDialog, self).__init__()
        self.setupUi()
        self.init_connections()
        self.load_settings()
        
    @property
    def proc_root(self):
        return self.validation_tab.proc_root
        
    @property
    def gpkg_path(self):
        return self.validation_tab.gpkg_path
        
    @property
    def csv_folder(self):
        return self.validation_tab.csv_folder
        
    @property
    def img_folder(self):
        return self.validation_tab.img_folder
        
    def setupUi(self):
        """Crear la interfaz con pestañas reorganizada (1-2-3-4)"""
        self.setWindowTitle("Canchas Las Tortolas - Procesador Topográfico")
        self.setMinimumSize(800, 600)
        
        # Layout principal
        layout = QVBoxLayout()
        
        # Crear widget de pestañas principales (solo 3)
        self.tab_widget = QTabWidget()
        
        # Crear las pestañas principales
        # Crear las pestañas principales
        # Pestaña 1: Validación (Refactorizada)
        self.validation_tab = ValidationTab()
        self.validation_tab.log_signal.connect(self.log_message)
        self.validation_tab.progress_signal.connect(self.update_progress)
        self.tab_widget.addTab(self.validation_tab, "1. Validación")
        
        # Pestaña 2: Procesamiento (Refactorizada)
        self.processing_tab = ProcessingTab()
        self.processing_tab.log_signal.connect(self.log_message)
        self.processing_tab.progress_signal.connect(self.update_progress)
        self.processing_tab.execute_signal.connect(self.ejecutar_procesamiento_bridge)
        self.tab_widget.addTab(self.processing_tab, "2. Procesamiento")
        
        # Pestaña 3: Análisis (Refactorizada)
        self.analysis_tab = AnalysisTab()
        self.analysis_tab.log_signal.connect(self.log_message)
        self.analysis_tab.progress_signal.connect(self.update_progress)
        
        # Conectar señales de ejecución de sub-pestañas a puentes
        self.analysis_tab.table_tab.execute_signal.connect(self.ejecutar_tabla_bridge)
        self.analysis_tab.volumes_tab.execute_signal.connect(self.ejecutar_volumenes_bridge)
        self.analysis_tab.xml_tab.execute_signal.connect(self.ejecutar_xml_bridge)
        self.analysis_tab.save_settings_signal.connect(self.save_settings)
        
        self.tab_widget.addTab(self.analysis_tab, "3. Análisis")
        
        # Pestaña 4: Datos Reporte (Refactorizada)
        self.reports_tab = ReportsTab()
        self.reports_tab.log_signal.connect(self.log_message)
        self.reports_tab.progress_signal.connect(self.update_progress)
        self.reports_tab.execute_reports_signal.connect(self.ejecutar_reportes_bridge)
        self.reports_tab.execute_composer_signal.connect(self.abrir_compositor_bridge)
        
        self.tab_widget.addTab(self.reports_tab, "4. Datos Reporte")
        
        layout.addWidget(self.tab_widget)
        
        # Barra de progreso global
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Log de resultados
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setPlaceholderText("Los resultados de las operaciones aparecerán aquí...")
        layout.addWidget(self.log_text)
        
        # Botones finales
        button_layout = QHBoxLayout()
        self.btn_close = QPushButton("Cerrar")
        button_layout.addStretch()
        button_layout.addWidget(self.btn_close)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    


    
    def init_connections(self):
        """Conectar señales"""
        self.btn_close.clicked.connect(self.close)
        # El botón de compositor ya está conectado en su creación: self.btn_open_composer.clicked.connect(self.abrir_compositor_plantilla)
    
    def select_file(self, line_edit, filter_text):
        """Seleccionar archivo"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", "", filter_text)
        if file_path:
            line_edit.setText(file_path)
    
    def select_folder(self, line_edit):
        """Seleccionar carpeta"""
        folder_path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if folder_path:
            line_edit.setText(folder_path)
    
    def log_message(self, message):
        """Agregar mensaje al log"""
        self.log_text.append(f"[{QTime.currentTime().toString()}] {message}")
    
    def load_settings(self):
        """Cargar configuración guardada"""
        settings = QSettings()
        
        # Cargar rutas guardadas
        try:
            val_root = settings.value("canchas/proc_root", "")
            if val_root: 
                self.proc_root.setText(str(val_root))
                
            val_gpkg = settings.value("canchas/gpkg_path", "")
            if val_gpkg: 
                self.gpkg_path.setText(str(val_gpkg))
                
            val_csv = settings.value("canchas/csv_folder", "")
            if val_csv: 
                self.csv_folder.setText(str(val_csv))
                
            val_img = settings.value("canchas/img_folder", "")
            if val_img: 
                self.img_folder.setText(str(val_img))
        except Exception as e:
            self.log_message(f"Error cargando configuración: {str(e)}")

    def save_settings(self):
        """Guardar configuración"""
        settings = QSettings()
        
        settings.setValue("canchas/proc_root", self.proc_root.text())
        settings.setValue("canchas/gpkg_path", self.gpkg_path.text())
        settings.setValue("canchas/csv_folder", self.csv_folder.text())
        settings.setValue("canchas/img_folder", self.img_folder.text())

    def closeEvent(self, event):
        """Al cerrar el diálogo, guardar configuración"""
        self.save_settings()
        super().closeEvent(event)
    
    # ===================================================================
    # MÉTODOS EJECUTAR (SIN CAMBIOS - TODA LA FUNCIONALIDAD INTACTA)
    # ===================================================================
    
    def update_progress(self, value, message=""):
        """Callback para actualizar progreso"""
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)
        self.progress_bar.setValue(value)
        # No logear mensajes rutinarios de progreso - solo actualizar barra
    
        
    def ejecutar_procesamiento_bridge(self):
        """Puente para ejecutar procesamiento inyectando proc_root"""
        # Obtener proc_root desde la pestaña de validación (via propiedad)
        proc_root_path = self.proc_root.text()
        
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)
            
        success = self.processing_tab.ejecutar_procesamiento(proc_root_path)
        
        if success:
            self.save_settings()
        
        self.progress_bar.setVisible(False)
        
    def ejecutar_tabla_bridge(self, protocolo_inicio):
        """Puente para ejecutar tabla con parámetros del subtab"""
        proc_root_path = self.proc_root.text()
        
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)
            
        success = self.analysis_tab.table_tab.ejecutar_tabla(proc_root_path)
            
        self.progress_bar.setVisible(False)
        
    def ejecutar_volumenes_bridge(self, params):
        """Puente para ejecutar volúmenes con parámetros del subtab"""
        proc_root_path = self.proc_root.text()
        
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)
        
        # El subtab ya tiene los parms porque los emitió el mismo, 
        # pero ejecutar_volumenes_pantallazos solo pide proc_root 
        # y lee de sus propios widgets.
        # Asi que solo llamamos con proc_root
        success = self.analysis_tab.volumes_tab.ejecutar_volumenes_pantallazos(proc_root_path)
        
        self.progress_bar.setVisible(False)
        
    def ejecutar_xml_bridge(self):
        """Puente para ejecutar xml"""
        proc_root_path = self.proc_root.text()
        
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)
            
        success = self.analysis_tab.xml_tab.ejecutar_xml(proc_root_path)
        
        self.progress_bar.setVisible(False)
        
    def ejecutar_reportes_bridge(self):
        """Puente para ejecutar reportes"""
        proc_root_path = self.proc_root.text()
        
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)
            
        success = self.reports_tab.ejecutar_fusion_y_analisis(proc_root_path)
        
        if success:
            self.save_settings()
            
        self.progress_bar.setVisible(False)
        
    def abrir_compositor_bridge(self):
        """Puente para abrir compositor"""
        proc_root_path = self.proc_root.text()
        # No requiere progress bar, abre UI
        self.reports_tab.abrir_compositor_plantilla(proc_root_path)