from qgis.PyQt import QtWidgets, QtCore
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QGroupBox, QCheckBox, QHBoxLayout)
from ...gui.styles import Styles

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
        layout.setSpacing(20) # Más aire
        
        # Título y descripción
        title = QLabel("🗺️ PROCESAMIENTO ESPACIAL")
        title.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {Styles.Theme.PRIMARY};")
        layout.addWidget(title)
        
        desc = QLabel("Genera capas de puntos, polígonos y triangulaciones a partir de archivos validados")
        desc.setStyleSheet(f"color: {Styles.Theme.TEXT_MUTED}; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Grupo de salidas esperadas
        output_group = QGroupBox("📤 Salidas que se generarán")
        output_group.setStyleSheet(Styles.get_card_style())
        output_layout = QVBoxLayout()
        
        outputs_info = QLabel("""• Grupo: Procesamiento_YYMMDD (contraído y apagado)
    └── Puntos/ (capas de puntos de archivos CSV)
    └── Poligonos/ (concave hulls de CSV, polígonos suavizados de ASC)
    └── Triangulaciones/ (TIN recortados de CSV, rasters ASC)""")
        outputs_info.setStyleSheet(f"font-family: 'Courier New'; color: {Styles.Theme.TEXT_MAIN}; background-color: {Styles.Theme.BG_APP}; padding: 15px; border-radius: 4px; border-left: 3px solid {Styles.Theme.ACCENT};")
        output_layout.addWidget(outputs_info)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # Grupo de Exportación (NUEVO)
        export_group = QGroupBox("💾 Opciones de Exportación")
        export_group.setStyleSheet(Styles.get_card_style())
        export_layout = QVBoxLayout()
        export_layout.setSpacing(10)
        
        export_desc = QLabel("Seleccione los formatos adicionales a generar en la carpeta 'Geoespacial':")
        export_desc.setStyleSheet(f"color: {Styles.Theme.TEXT_MUTED}; font-size: 12px;")
        export_layout.addWidget(export_desc)

        # Container para checkboxes en horizontal o grid
        checks_layout = QHBoxLayout()
        
        self.chk_points = QCheckBox("Puntos (.csv)")
        self.chk_points.setChecked(False)
        self.chk_points.setStyleSheet(f"font-size: 13px; color: {Styles.Theme.TEXT_MAIN};")
        
        self.chk_polygons = QCheckBox("Polígonos (.shp)")
        self.chk_polygons.setChecked(True)
        self.chk_polygons.setStyleSheet(f"font-size: 13px; color: {Styles.Theme.TEXT_MAIN};")
        
        self.chk_tin = QCheckBox("Triangulaciones (.tif)")
        self.chk_tin.setChecked(True)
        self.chk_tin.setStyleSheet(f"font-size: 13px; color: {Styles.Theme.TEXT_MAIN};")
        
        checks_layout.addWidget(self.chk_points)
        checks_layout.addWidget(self.chk_polygons)
        checks_layout.addWidget(self.chk_tin)
        checks_layout.addStretch()
        
        export_layout.addLayout(checks_layout)
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        layout.addStretch()
        
        # Botón ejecutar con estilo HERO
        self.btn_processing = QPushButton("⚙️ Generar Capas Espaciales")
        self.btn_processing.setStyleSheet(Styles.get_primary_button_style())
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
        
        # Recopilar opciones de exportación
        export_options = {
            'points': self.chk_points.isChecked(),
            'polygons': self.chk_polygons.isChecked(),
            'tin': self.chk_tin.isChecked()
        }
        
        if any(export_options.values()):
            self.emit_log(f"💾 Opciones de exportación activas: {export_options}")
        
        # Parámetros fijos de procesamiento optimizados (configurables en código si fuese necesario)
        pixel_size = 0.25  # Resolución TIN en metros (Estándar 25cm)
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
            resultado = processor.ejecutar_procesamiento_completo(export_options)
            
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
