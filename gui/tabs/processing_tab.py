# -*- coding: utf-8 -*-
from qgis.PyQt import QtWidgets, QtCore
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QGroupBox)

class ProcessingTab(QWidget):
    """
    Pestaña 2: Procesamiento Espacial
    Encargada de la UI y ejecución de la etapa de procesamiento (Puntos, Polígonos, TIN).
    Depende de que se le provea el 'proc_root' al momento de ejecutar.
    """
    
    # Señales
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    execute_signal = pyqtSignal() # Señal para pedir al controlador que inicie el proceso (inyectando proc_root)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()
        
    def setupUi(self):
        layout = QVBoxLayout()
        
        # Título y descripción
        title = QLabel("🗺️ PROCESAMIENTO ESPACIAL")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #F18F01;")
        layout.addWidget(title)
        
        desc = QLabel("Genera capas de puntos, polígonos y triangulaciones a partir de archivos validados")
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Grupo de salidas esperadas
        output_group = QGroupBox("📤 Salidas que se generarán")
        output_layout = QVBoxLayout()
        
        outputs_info = QLabel("""• Grupo: Procesamiento_YYMMDD (contraído y apagado)
    └── Puntos/ (capas de puntos de archivos CSV)
    └── Poligonos/ (concave hulls de CSV, polígonos suavizados de ASC)
    └── Triangulaciones/ (TIN recortados de CSV, rasters ASC)""")
        outputs_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #f8f8f8; padding: 10px; border: 1px solid #ddd;")
        output_layout.addWidget(outputs_info)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        layout.addStretch()
        
        # Botón ejecutar con estilo
        self.btn_processing = QPushButton("⚙️ Generar Capas Espaciales")
        self.btn_processing.setStyleSheet("""
            QPushButton {
                background-color: #F18F01; 
                color: white; 
                font-weight: bold; 
                padding: 10px; 
                border: none; 
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #9c5d03;
            }
            QPushButton:pressed {
                background-color: #164B73;
            }
        """)
        self.btn_processing.clicked.connect(self.emit_execute_signal)
        layout.addWidget(self.btn_processing)
        
        self.setLayout(layout)
        
    def emit_execute_signal(self):
        """Emite la señal de que el usuario quiere ejecutar"""
        self.execute_signal.emit()
        
    def emit_log(self, message):
        """Helper para emitir log"""
        self.log_signal.emit(message)
        
    def emit_progress(self, value, message=""):
        """Helper para emitir progreso"""
        self.progress_signal.emit(value, message)

    def ejecutar_procesamiento(self, proc_root):
        """
        Ejecutar proceso de procesamiento espacial.
        Recibe proc_root explícitamente para evitar acoplamiento con la UI de inputs.
        """
        # Verificar que PROC_ROOT esté configurado
        if not proc_root or not proc_root.strip():
            self.emit_log("❌ Error: Debe configurar la carpeta de procesamiento (PROC_ROOT)")
            return
            
        self.emit_progress(0)
        
        self.emit_log("⚙️ Iniciando procesamiento espacial...")
        self.emit_log(f"📁 PROC_ROOT: {proc_root}")
        
        # Parámetros fijos de procesamiento optimizados (configurables en código si fuese necesario)
        pixel_size = 0.1  # Resolución TIN en metros
        suavizado_tolerance = 1.0  # Tolerancia suavizado ASC en metros  
        min_dist_vertices = 2.0  # Distancia mínima entre vértices en metros
        
        self.emit_log(f"🔧 Píxel TIN: {pixel_size} metros")
        self.emit_log(f"🎯 Tolerancia suavizado: {suavizado_tolerance} metros")
        self.emit_log(f"📏 Distancia mínima vértices: {min_dist_vertices} metros")
        
        try:
            # Importar el procesador dinámicamente
            from ...core.processing import ProcessingProcessor
            
            # Crear procesador con parámetros optimizados
            processor = ProcessingProcessor(
                proc_root=proc_root,
                pixel_size=pixel_size,
                suavizado_tolerance=suavizado_tolerance,
                min_dist_vertices=min_dist_vertices,
                progress_callback=self.emit_progress,
                log_callback=self.emit_log
            )
            
            # Ejecutar procesamiento completo
            resultado = processor.ejecutar_procesamiento_completo()
            
            if resultado['success']:
                self.emit_log("🎉 ¡Procesamiento espacial completado exitosamente!")
                self.emit_log(f"📊 {resultado.get('total_archivos', 0)} archivos procesados")
                self.emit_log(f"📁 Grupo creado: {resultado.get('group_name', 'N/A')}")
                # El guardado de settings se gestiona en el padre
                return True
            else:
                self.emit_log(f"❌ Error: {resultado['message']}")
                if 'details' in resultado:
                    self.emit_log("📋 Ver detalles del error arriba")
                return False
                
        except Exception as e:
            self.emit_log(f"❌ Error inesperado: {e}")
            return False
        finally:
             # Ocultar barra de progreso si fuese necesario manejado por el padre
             pass
