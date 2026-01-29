# -*- coding: utf-8 -*-
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                                QLabel, QGroupBox)

class XmlSubTab(QWidget):
    """
    Sub-pestaña 3.3: Exportación XML
    Encargada de la UI y ejecución de la exportación a LandXML.
    """
    
    # Señales
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    execute_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()
        
    def setupUi(self):
        layout = QVBoxLayout()
        
        # Header con icono y título
        header_layout = QHBoxLayout()
        icon_label = QLabel("📄")
        icon_label.setStyleSheet("font-size: 20px; margin-right: 8px;")
        title_label = QLabel("EXPORTACIÓN A XML")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #6A4C93;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc = QLabel("Exporta superficies trianguladas a formato LandXML 1.2 estándar")
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Formato LandXML
        format_group = QGroupBox("📋 Formato LandXML")
        format_layout = QVBoxLayout()
        
        format_info = QLabel("""ESTÁNDAR: LandXML 1.2
    UNIDADES: Métricos (metro, metro cuadrado, metro cúbico)
    SUPERFICIE: Triangulated Irregular Network (TIN)
    DATOS: Puntos 3D + Caras triangulares
    METADATOS: Área 2D/3D, elevación mín/máx
    
    CONFIGURACIÓN: Optimizada automáticamente
    • Intercambio XY: Activado
    • Muestreo rasters: Cada 2 píxeles""")
        format_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #f3f0ff; padding: 10px; border: 1px solid #6A4C93; border-radius: 3px;")
        format_layout.addWidget(format_info)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # Procesamiento por tipo
        process_group = QGroupBox("🔄 Procesamiento por Tipo")
        process_layout = QVBoxLayout()
        
        process_info = QLabel("""CSV → Puntos de capa + Triangulación Delaunay
    ASC → Muestreo de raster + Triangulación Delaunay

    Salida: PROC_ROOT/XML/{nombre_base}.xml""")
        process_info.setStyleSheet("color: #666; background-color: #f9f9f9; padding: 8px; border-left: 3px solid #6A4C93;")
        process_layout.addWidget(process_info)
        
        process_group.setLayout(process_layout)
        layout.addWidget(process_group)
        
        layout.addStretch()
        
        # Botón ejecutar
        self.btn_xml = QPushButton("📤 Exportar a LandXML")
        self.btn_xml.setStyleSheet("""
            QPushButton {
                background-color: #6A4C93; 
                color: white; 
                font-weight: bold; 
                padding: 10px; 
                border: none; 
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #563A7A;
            }
            QPushButton:pressed {
                background-color: #422C5E;
            }
        """)
        self.btn_xml.clicked.connect(self.execute_signal.emit)
        layout.addWidget(self.btn_xml)
        
        self.setLayout(layout)

    def ejecutar_xml(self, proc_root):
        """
        Ejecuta la exportación a XML.
        """
        if not proc_root or not proc_root.strip():
            self.log_signal.emit("❌ Error: Debe configurar la carpeta de procesamiento (PROC_ROOT)")
            return False
            
        self.progress_signal.emit(0, "Iniciando")
        
        self.log_signal.emit("📄 Iniciando exportación a LandXML...")
        self.log_signal.emit(f"📁 PROC_ROOT: {proc_root}")
        
        try:
            # Importar procesador dinámicamente
            from ....core.xml_export import XMLExportProcessor
            
            processor = XMLExportProcessor(
                proc_root=proc_root,
                progress_callback=lambda v, m="": self.progress_signal.emit(v, m),
                log_callback=lambda m: self.log_signal.emit(m)
            )
            
            # Ejecutar
            resultado = processor.ejecutar_exportacion_xml_completa()
            
            if resultado['success']:
                self.log_signal.emit("🎉 ¡Exportación XML completada exitosamente!")
                self.log_signal.emit(f"📊 {resultado.get('archivos_generados', 0)} archivos generados")
                return True
            else:
                self.log_signal.emit(f"❌ Error: {resultado['message']}")
                return False
                
        except Exception as e:
            self.log_signal.emit(f"❌ Error inesperado: {e}")
            return False
