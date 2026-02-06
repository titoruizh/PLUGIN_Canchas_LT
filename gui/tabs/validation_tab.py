# -*- coding: utf-8 -*-
import os
from qgis.PyQt import QtWidgets, QtCore
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                                QPushButton, QLabel, QLineEdit, QFileDialog, QGroupBox)
from ...gui.styles import Styles

class ValidationTab(QWidget):
    """
    Pestaña 1: Validación de Archivos
    Encargada de la UI y ejecución de la etapa de validación.
    """
    
    # Señales para comunicar progreso y logs al Dialog principal
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()
        
    def setupUi(self):
        layout = QVBoxLayout()
        layout.setSpacing(15) 
        
        # Título y descripción con estilo
        title = QLabel("📋 VALIDACIÓN DE ARCHIVOS")
        title.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {Styles.Theme.PRIMARY};")
        layout.addWidget(title)
        
        desc = QLabel("Valida archivos CSV/ASC espacialmente y los prepara para procesamiento")
        desc.setStyleSheet(f"color: {Styles.Theme.TEXT_MUTED}; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Grupo de carpeta principal
        main_group = QGroupBox("📁 CARPETA PRINCIPAL DE TRABAJO")
        main_group.setStyleSheet(Styles.get_card_style())
        main_layout = QVBoxLayout()
        
        # PROC_ROOT con estilo
        proc_layout = QHBoxLayout()
        lbl_proc = QLabel("Carpeta Procesamiento (PROC_ROOT):")
        lbl_proc.setStyleSheet("font-weight: bold;") 
        proc_layout.addWidget(lbl_proc)
        
        self.proc_root = QLineEdit()
        self.proc_root.setPlaceholderText("E:\\CANCHAS_QFIELD\\QGIS PROCESAMIENTO\\Archivos Procesados TERRENO")
        self.proc_root.setText(r"E:\CANCHAS_QFIELD\QGIS PROCESAMIENTO\Archivos Procesados TERRENO")
        self.proc_root.setStyleSheet(Styles.get_input_style())
        proc_layout.addWidget(self.proc_root)
        
        btn_proc = QPushButton("📁")
        btn_proc.setMaximumWidth(40)
        btn_proc.setStyleSheet(Styles.get_tool_button_style())
        btn_proc.clicked.connect(lambda: self.select_folder(self.proc_root))
        proc_layout.addWidget(btn_proc)
        main_layout.addLayout(proc_layout)
        
        # Info sobre carpetas que se crearán
        carpetas_info = QLabel("""📤 Carpetas que se crearán automáticamente:
    • CSV-ASC (archivos procesados)    • IMAGENES (fotos con prefijo F)
    • XML (archivos LandXML)          • Planos (pantallazos JPG)
    • backups (respaldos de originales)""")
        carpetas_info.setStyleSheet(f"color: {Styles.Theme.TEXT_MAIN}; background-color: {Styles.Theme.BG_APP}; padding: 10px; border-left: 3px solid {Styles.Theme.PRIMARY}; margin: 5px 0; border-radius: 4px;")
        main_layout.addWidget(carpetas_info)
        
        main_group.setLayout(main_layout)
        layout.addWidget(main_group)
        
        # Grupo de archivos originales
        orig_group = QGroupBox("📥 ARCHIVOS ORIGINALES")
        orig_group.setStyleSheet(Styles.get_card_style())
        orig_layout = QVBoxLayout()
        
        # GPKG original
        gpkg_layout = QHBoxLayout()
        gpkg_layout.addWidget(QLabel("GPKG Original:"))
        self.gpkg_path = QLineEdit()
        self.gpkg_path.setPlaceholderText("Ruta al archivo Levantamientos.gpkg")
        self.gpkg_path.setStyleSheet(Styles.get_input_style())
        gpkg_layout.addWidget(self.gpkg_path)
        
        btn_gpkg = QPushButton("📁")
        btn_gpkg.setMaximumWidth(40)
        btn_gpkg.setStyleSheet(Styles.get_tool_button_style())
        btn_gpkg.clicked.connect(lambda: self.select_file(self.gpkg_path, "GPKG (*.gpkg)"))
        gpkg_layout.addWidget(btn_gpkg)
        orig_layout.addLayout(gpkg_layout)
        
        # Carpeta CSV-ASC
        csv_layout = QHBoxLayout()
        csv_layout.addWidget(QLabel("Carpeta CSV-ASC:"))
        self.csv_folder = QLineEdit()
        self.csv_folder.setPlaceholderText("Carpeta con archivos CSV y ASC originales")
        self.csv_folder.setStyleSheet(Styles.get_input_style())
        csv_layout.addWidget(self.csv_folder)
        
        btn_csv = QPushButton("📁")
        btn_csv.setMaximumWidth(40)
        btn_csv.setStyleSheet(Styles.get_tool_button_style())
        btn_csv.clicked.connect(lambda: self.select_folder(self.csv_folder))
        csv_layout.addWidget(btn_csv)
        orig_layout.addLayout(csv_layout)
        
        # Carpeta imágenes
        img_layout = QHBoxLayout()
        img_layout.addWidget(QLabel("Carpeta Imágenes:"))
        self.img_folder = QLineEdit()
        self.img_folder.setPlaceholderText("Carpeta con archivos JPG originales")
        self.img_folder.setStyleSheet(Styles.get_input_style())
        img_layout.addWidget(self.img_folder)
        
        btn_img = QPushButton("📁")
        btn_img.setMaximumWidth(40)
        btn_img.setStyleSheet(Styles.get_tool_button_style())
        btn_img.clicked.connect(lambda: self.select_folder(self.img_folder))
        img_layout.addWidget(btn_img)
        orig_layout.addLayout(img_layout)
        
        orig_group.setLayout(orig_layout)
        layout.addWidget(orig_group)
        
        # Grupo de validaciones que se realizarán
        validation_group = QGroupBox("🔍 Validaciones que se realizarán")
        validation_group.setStyleSheet(Styles.get_card_style())
        validation_layout = QVBoxLayout()
        
        validations_info = QLabel("""ESPACIALES: Intersección con polígonos de muros y sectores
    FORMATO: Estructura de columnas y tipos de datos
    COORDENADAS: Validación de rangos Norte/Este/Cota  
    DEM: Comparación de cotas contra modelos digitales
    GEOMETRÍA: Generación de ConcaveHull para archivos CSV
    ARCHIVOS: Conversión de formatos y limpieza de nombres""")
        validations_info.setStyleSheet(f"font-family: 'Courier New'; color: {Styles.Theme.TEXT_MUTED}; background-color: {Styles.Theme.BG_APP}; padding: 10px; border: 1px dashed {Styles.Theme.BORDER_LIGHT}; border-radius: 3px;")
        validation_layout.addWidget(validations_info)
        
        validation_group.setLayout(validation_layout)
        layout.addWidget(validation_group)
        
        layout.addStretch()
        
        # Botón ejecutar con estilo mejorado
        self.btn_validation = QPushButton("🔍 Ejecutar Validación Completa")
        self.btn_validation.setStyleSheet(Styles.get_primary_button_style())
        self.btn_validation.clicked.connect(self.ejecutar_validacion)
        layout.addWidget(self.btn_validation)
        
        self.setLayout(layout)
        
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
            
    def emit_log(self, message):
        """Helper para emitir log"""
        self.log_signal.emit(message)
        
    def emit_progress(self, value, message=""):
        """Helper para emitir progreso"""
        self.progress_signal.emit(value, message)

    def ejecutar_validacion(self):
        """Ejecutar proceso de validación completo"""
        # Verificar que PROC_ROOT esté configurado
        if not self.proc_root.text().strip():
            self.emit_log("❌ Error: Debe configurar la carpeta de procesamiento (PROC_ROOT)")
            return
            
        # Verificar que existan las rutas originales
        if not self.proc_root.text() or not self.gpkg_path.text() or not self.csv_folder.text() or not self.img_folder.text():
            self.emit_log("⚠️ Por favor complete todos los campos requeridos")
            return
        
        self.emit_progress(0)
        
        try:
            # Import dinámico para evitar cargar todo al inicio si no es necesario,
            # manteniendo el patrón original
            from ...core.validation import ValidationProcessor
            
            # Crear procesador con callbacks conectados a las señales
            processor = ValidationProcessor(
                proc_root=self.proc_root.text(),
                orig_gpkg=self.gpkg_path.text(),
                dir_csv_orig=self.csv_folder.text(),
                dir_img_orig=self.img_folder.text(),
                progress_callback=self.emit_progress,
                log_callback=self.emit_log
            )
            
            # Ejecutar validación completa
            resultado = processor.ejecutar_validacion_completa()
            
            if resultado['success']:
                self.emit_log("🎉 ¡Validación completada exitosamente!")
                self.emit_log(f"📦 Backup creado en: {resultado.get('backup_folder', 'N/A')}")
                # El guardado de settings se delega al padre, o se añade mecanismo aquí
            else:
                self.emit_log(f"❌ Error: {resultado['message']}")
                if 'details' in resultado:
                    self.emit_log("📋 Ver detalles del error arriba")
                
        except ImportError as e:
            self.emit_log(f"❌ Error: No se pudo importar el módulo de validación: {e}")
        except Exception as e:
            self.emit_log(f"❌ Error inesperado: {e}")
        finally:
            # Ocultar barra de progreso (enviando -1 o manejándolo en el padre)
            # El padre manejaba setVisible(False), aquí podemos enviar 100 o señal personalizada
            pass
