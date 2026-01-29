# -*- coding: utf-8 -*-
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                                QLabel, QGroupBox, QSpinBox)

class TableSubTab(QWidget):
    """
    Sub-pestaña 3.1: Tabla Base
    Encargada de la UI y ejecución de la creación de tabla.
    """
    
    # Señales
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    execute_signal = pyqtSignal(int) # Envía el protocolo_inicio
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()
        
    def setupUi(self):
        layout = QVBoxLayout()
        
        # Header con icono y título
        header_layout = QHBoxLayout()
        icon_label = QLabel("📋")
        icon_label.setStyleSheet("font-size: 20px; margin-right: 8px;")
        title_label = QLabel("TABLA BASE DATOS")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #A23B72;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc = QLabel("Crea tabla con vértices extremos, metadata y campos calculados")
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Configuración
        config_group = QGroupBox("🔧 Configuración")
        config_layout = QVBoxLayout()
        
        # Protocolo topográfico inicial
        protocol_layout = QHBoxLayout()
        protocol_layout.addWidget(QLabel("Protocolo topográfico inicial:"))
        self.protocolo_inicio = QSpinBox()
        self.protocolo_inicio.setMinimum(1)
        self.protocolo_inicio.setMaximum(9999)
        self.protocolo_inicio.setValue(1)
        self.protocolo_inicio.setToolTip("Número inicial para la secuencia de protocolos")
        protocol_layout.addWidget(self.protocolo_inicio)
        protocol_layout.addStretch()
        config_layout.addLayout(protocol_layout)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Campos que se crearán
        campos_group = QGroupBox("📋 Campos de la tabla")
        campos_layout = QVBoxLayout()
        
        campos_info = QLabel("""METADATA: Protocolo Topográfico, Muro, Fecha, Sector, Relleno
    COORDENADAS: P1-P4 (ESTE, NORTE, COTA) - vértices extremos
    ARCHIVOS: Foto, Plano, Control Topográfico, Operador  
    GEOMETRÍA: Area, Ancho, Largo, Cut, Fill, Espesor (mín/máx)
    TÉCNICO: Disciplina, N° Capas""")
        campos_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #f8f8f8; padding: 10px; border: 1px solid #ddd;")
        campos_layout.addWidget(campos_info)
        
        campos_group.setLayout(campos_layout)
        layout.addWidget(campos_group)
        
        layout.addStretch()
        
        # Botón ejecutar
        self.btn_table = QPushButton("📋 Crear Tabla Base Datos")
        self.btn_table.setStyleSheet("""
            QPushButton {
                background-color: #A23B72; 
                color: white; 
                font-weight: bold; 
                padding: 10px; 
                border: none; 
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7A2A56;
            }
            QPushButton:pressed {
                background-color: #5D1F41;
            }
        """)
        self.btn_table.clicked.connect(self.emit_execute_signal)
        layout.addWidget(self.btn_table)
        
        self.setLayout(layout)
        
    def emit_execute_signal(self):
        """Emite señal de ejecución con los parámetros"""
        self.execute_signal.emit(self.protocolo_inicio.value())

    def ejecutar_tabla(self, proc_root):
        """
        Ejecuta la lógica de creación de tabla.
        Recibe proc_root desde el controlador.
        """
        if not proc_root or not proc_root.strip():
            self.log_signal.emit("❌ Error: Debe configurar la carpeta de procesamiento (PROC_ROOT)")
            return False
            
        self.progress_signal.emit(0, "Iniciando")
        
        self.log_signal.emit("📋 Iniciando creación de tabla base...")
        self.log_signal.emit(f"📁 PROC_ROOT: {proc_root}")
        self.log_signal.emit(f"🔢 Protocolo inicial: {self.protocolo_inicio.value()}")
        
        try:
            # Importar el procesador dinámicamente
            from ....core.table_creation import TableCreationProcessor
            
            # Crear procesador
            processor = TableCreationProcessor(
                proc_root=proc_root,
                protocolo_topografico_inicio=self.protocolo_inicio.value(),
                progress_callback=lambda v, m="": self.progress_signal.emit(v, m),
                log_callback=lambda m: self.log_signal.emit(m)
            )
            
            # Ejecutar
            resultado = processor.ejecutar_creacion_tabla_completa()
            
            if resultado['success']:
                self.log_signal.emit("🎉 ¡Tabla base creada exitosamente!")
                self.log_signal.emit(f"📊 {resultado.get('registros_creados', 0)} registros creados")
                self.log_signal.emit(f"📋 Tabla: {resultado.get('tabla_nombre', 'N/A')}")
                return True
            else:
                self.log_signal.emit(f"❌ Error: {resultado['message']}")
                if 'details' in resultado:
                    self.log_signal.emit("📋 Ver detalles del error arriba")
                return False
                
        except Exception as e:
            self.log_signal.emit(f"❌ Error inesperado: {e}")
            return False
