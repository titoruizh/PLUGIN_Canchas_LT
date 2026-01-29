# -*- coding: utf-8 -*-
import os
from qgis.PyQt import QtWidgets, QtCore
from qgis.PyQt.QtCore import pyqtSignal, QThread, QSettings, QTime
from qgis.PyQt.QtWidgets import (QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, 
                                QPushButton, QTextEdit, QProgressBar, QLabel, 
                                QLineEdit, QFileDialog)
from .gui.tabs.validation_tab import ValidationTab
from .gui.tabs.processing_tab import ProcessingTab

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
        
        self.create_analysis_tab()        # Pestaña 3 (con sub-pestañas)
        self.create_reports_tab()         # Pestaña 4 (Datos Reporte)
        
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
    
    

    def create_analysis_tab(self):
        """Pestaña 3: Análisis Completo (NUEVA con sub-pestañas)"""
        tab = QtWidgets.QWidget()
        layout = QVBoxLayout()
        
        # Título principal con estilo mejorado
        header_layout = QHBoxLayout()
        icon_label = QLabel("📊")
        icon_label.setStyleSheet("font-size: 24px; margin-right: 10px;")
        title_label = QLabel("ANÁLISIS COMPLETO")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #F18F01;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc = QLabel("Ejecuta análisis detallados: tabla base, volúmenes, pantallazos y exportación XML")
        desc.setStyleSheet("color: gray; margin-bottom: 15px; font-size: 12px;")
        layout.addWidget(desc)
        
        # Widget de sub-pestañas
        self.analysis_tab_widget = QTabWidget()
        self.analysis_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #C0C0C0;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 8px 12px;
                margin-right: 2px;
                border: 1px solid #C0C0C0;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
        """)
        
        # Crear las 3 sub-pestañas (eliminando pantallazos separados)
        self.create_table_subtab()        # 3.1
        self.create_volumes_subtab()      # 3.2 (UNIFICADO con pantallazos)  
        self.create_xml_subtab()          # 3.3 (renumerado)
        
        layout.addWidget(self.analysis_tab_widget)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "3. Análisis")

    def create_table_subtab(self):
        """Sub-pestaña 3.1: Tabla Base"""
        tab = QtWidgets.QWidget()
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
        config_group = QtWidgets.QGroupBox("🔧 Configuración")
        config_layout = QVBoxLayout()
        
        # Protocolo topográfico inicial
        protocol_layout = QHBoxLayout()
        protocol_layout.addWidget(QLabel("Protocolo topográfico inicial:"))
        self.protocolo_inicio = QtWidgets.QSpinBox()
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
        campos_group = QtWidgets.QGroupBox("📋 Campos de la tabla")
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
        self.btn_table.clicked.connect(self.ejecutar_tabla)
        layout.addWidget(self.btn_table)
        
        tab.setLayout(layout)
        self.analysis_tab_widget.addTab(tab, "3.1 Tabla")

    def create_volumes_subtab(self):
        """Sub-pestaña 3.2: Volúmenes y Pantallazos (UNIFICADO)"""
        tab = QtWidgets.QWidget()
        layout = QVBoxLayout()
        
        # Header con icono y título
        header_layout = QHBoxLayout()
        icon_label = QLabel("�📸")
        icon_label.setStyleSheet("font-size: 20px; margin-right: 8px;")
        title_label = QLabel("VOLÚMENES Y PANTALLAZOS")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #F18F01;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc = QLabel("Proceso incremental: cut/fill + pantallazos de diferencias DEM + pegado automático")
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Configuración de volúmenes y pantallazos
        config_group = QtWidgets.QGroupBox("⚙️ Parámetros de Cálculo Volumétrico")
        config_layout = QVBoxLayout()
        
        # Número de puntos aleatorios
        random_points_layout = QHBoxLayout()
        random_points_layout.addWidget(QLabel("Puntos aleatorios para análisis:"))
        self.num_random_points = QtWidgets.QSpinBox()
        self.num_random_points.setMinimum(5)
        self.num_random_points.setMaximum(100)
        self.num_random_points.setValue(20)
        self.num_random_points.setToolTip("Número de puntos para validación de volúmenes")
        random_points_layout.addWidget(self.num_random_points)
        random_points_layout.addStretch()
        config_layout.addLayout(random_points_layout)
        
        # Espesor mínimo
        min_thickness_layout = QHBoxLayout()
        min_thickness_layout.addWidget(QLabel("Espesor mínimo permitido:"))
        self.min_espesor = QLineEdit("0.01")
        self.min_espesor.setMaximumWidth(100)
        self.min_espesor.setToolTip("Valor mínimo absoluto para espesores (metros)")
        min_thickness_layout.addWidget(self.min_espesor)
        min_thickness_layout.addWidget(QLabel("metros"))
        min_thickness_layout.addStretch()
        config_layout.addLayout(min_thickness_layout)
        
        # Algoritmo de remuestreo
        resample_layout = QHBoxLayout()
        resample_layout.addWidget(QLabel("Algoritmo de remuestreo:"))
        self.resample_algorithm = QtWidgets.QComboBox()
        self.resample_algorithm.addItems(['near', 'bilinear', 'cubic', 'cubicspline'])
        self.resample_algorithm.setCurrentText('bilinear')  # Cambiado a bilinear como default
        
        # Conectar cambio de selección para actualizar tooltip dinámico
        self.resample_algorithm.currentTextChanged.connect(self.update_resample_tooltip)
        self.update_resample_tooltip('bilinear')  # Establecer tooltip inicial
        
        resample_layout.addWidget(self.resample_algorithm)
        resample_layout.addStretch()
        config_layout.addLayout(resample_layout)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Configuración de pantallazos
        screenshot_group = QtWidgets.QGroupBox("📸 Parámetros de Pantallazos")
        screenshot_layout = QVBoxLayout()
        
        # Dimensiones
        dimensions_layout = QHBoxLayout()
        dimensions_layout.addWidget(QLabel("Dimensiones:"))
        
        self.screenshot_width = QtWidgets.QSpinBox()
        self.screenshot_width.setMinimum(400)
        self.screenshot_width.setMaximum(2000)
        self.screenshot_width.setValue(800)
        self.screenshot_width.setSuffix(" px")
        dimensions_layout.addWidget(self.screenshot_width)
        
        dimensions_layout.addWidget(QLabel("×"))
        
        self.screenshot_height = QtWidgets.QSpinBox()
        self.screenshot_height.setMinimum(300)
        self.screenshot_height.setMaximum(1500)
        self.screenshot_height.setValue(500)
        self.screenshot_height.setSuffix(" px")
        dimensions_layout.addWidget(self.screenshot_height)
        
        dimensions_layout.addStretch()
        screenshot_layout.addLayout(dimensions_layout)
        
        # Factor de expansión
        expansion_layout = QHBoxLayout()
        expansion_layout.addWidget(QLabel("Factor de expansión:"))
        self.expansion_factor = QtWidgets.QDoubleSpinBox()
        self.expansion_factor.setMinimum(1.0)
        self.expansion_factor.setMaximum(3.0)
        self.expansion_factor.setValue(1.3)
        self.expansion_factor.setSingleStep(0.1)
        self.expansion_factor.setToolTip("Margen alrededor del área (1.0 = sin margen)")
        expansion_layout.addWidget(self.expansion_factor)
        expansion_layout.addStretch()
        screenshot_layout.addLayout(expansion_layout)
        
        # Capa de fondo
        background_layout = QHBoxLayout()
        background_layout.addWidget(QLabel("Capa de fondo:"))
        self.background_layer = QLineEdit("tif")
        self.background_layer.setToolTip("Nombre de la capa que se usará como fondo")
        background_layout.addWidget(self.background_layer)
        background_layout.addStretch()
        screenshot_layout.addLayout(background_layout)
        
        screenshot_group.setLayout(screenshot_layout)
        layout.addWidget(screenshot_group)
        
        # Proceso incremental unificado
        process_group = QtWidgets.QGroupBox("🔄 Proceso Incremental Unificado")
        process_layout = QVBoxLayout()
        
        process_info = QLabel("""NUEVO FLUJO UNIFICADO:
    1. ORDEN CRONOLÓGICO: Procesa filas por fecha de tabla
    2. CÁLCULO VOLUMEN: TIN_nuevo vs DEM_muro → Cut/Fill/Espesor
    3. PANTALLAZOS DEM: Diferencia TIN vs DEM con colores cut/fill 
    4. PEGADO INCREMENTAL: TIN_nuevo se pega sobre DEM_muro
    5. ACTUALIZACIÓN: DEM_muro listo para siguiente iteración

    Resultado: Cut, Fill, Espesor + Pantallazos regulares + Pantallazos MovTierra""")
        process_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #fff8e7; padding: 10px; border: 1px solid #F18F01; border-radius: 3px;")
        process_layout.addWidget(process_info)
        
        process_group.setLayout(process_layout)
        layout.addWidget(process_group)
        
        layout.addStretch()
        
        # Botón ejecutar unificado
        self.btn_volume_screenshot = QPushButton("📊📸 Ejecutar Volúmenes y Pantallazos")
        self.btn_volume_screenshot.setStyleSheet("""
            QPushButton {
                background-color: #F18F01; 
                color: white; 
                font-weight: bold; 
                padding: 12px; 
                border: none; 
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #D17A01;
            }
            QPushButton:pressed {
                background-color: #B16801;
            }
        """)
        self.btn_volume_screenshot.clicked.connect(self.ejecutar_volumenes_pantallazos)
        layout.addWidget(self.btn_volume_screenshot)
        
        tab.setLayout(layout)
        self.analysis_tab_widget.addTab(tab, "3.2 Vol+Screenshots")

    def create_screenshots_subtab(self):
        """Sub-pestaña 3.3: Pantallazos"""
        tab = QtWidgets.QWidget()
        layout = QVBoxLayout()
        
        # Header con icono y título
        header_layout = QHBoxLayout()
        icon_label = QLabel("📸")
        icon_label.setStyleSheet("font-size: 20px; margin-right: 8px;")
        title_label = QLabel("GENERACIÓN DE PANTALLAZOS")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #C73E1D;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc = QLabel("Genera imágenes JPG de los polígonos con capa de fondo para documentación")
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Configuración de imagen
        image_group = QtWidgets.QGroupBox("🖼️ Configuración de Imagen")
        image_layout = QVBoxLayout()
        
        # Dimensiones
        dimensions_layout = QHBoxLayout()
        dimensions_layout.addWidget(QLabel("Dimensiones:"))
        
        self.screenshot_width = QtWidgets.QSpinBox()
        self.screenshot_width.setMinimum(400)
        self.screenshot_width.setMaximum(2000)
        self.screenshot_width.setValue(800)
        self.screenshot_width.setSuffix(" px")
        dimensions_layout.addWidget(self.screenshot_width)
        
        dimensions_layout.addWidget(QLabel("×"))
        
        self.screenshot_height = QtWidgets.QSpinBox()
        self.screenshot_height.setMinimum(300)
        self.screenshot_height.setMaximum(1500)
        self.screenshot_height.setValue(500)
        self.screenshot_height.setSuffix(" px")
        dimensions_layout.addWidget(self.screenshot_height)
        
        dimensions_layout.addStretch()
        image_layout.addLayout(dimensions_layout)
        
        # Factor de expansión
        expansion_layout = QHBoxLayout()
        expansion_layout.addWidget(QLabel("Factor de expansión:"))
        self.expansion_factor = QtWidgets.QDoubleSpinBox()
        self.expansion_factor.setMinimum(1.0)
        self.expansion_factor.setMaximum(3.0)
        self.expansion_factor.setValue(1.3)
        self.expansion_factor.setSingleStep(0.1)
        self.expansion_factor.setToolTip("Margen alrededor del polígono (1.0 = sin margen)")
        expansion_layout.addWidget(self.expansion_factor)
        expansion_layout.addStretch()
        image_layout.addLayout(expansion_layout)
        
        # Capa de fondo
        background_layout = QHBoxLayout()
        background_layout.addWidget(QLabel("Capa de fondo:"))
        self.background_layer = QLineEdit("tif")
        self.background_layer.setToolTip("Nombre de la capa que se usará como fondo")
        background_layout.addWidget(self.background_layer)
        background_layout.addStretch()
        image_layout.addLayout(background_layout)
        
        image_group.setLayout(image_layout)
        layout.addWidget(image_group)
        
        # Estilo de polígono
        style_group = QtWidgets.QGroupBox("🎨 Estilo de Polígono")
        style_layout = QVBoxLayout()
        
        style_info = QLabel("""CONTORNO: Rojo, grosor 1.5px
    RELLENO: Transparente (sin relleno)
    OPACIDAD: 100%
    FORMATO: JPG con fondo blanco""")
        style_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #ffe6e6; padding: 10px; border: 1px solid #C73E1D; border-radius: 3px;")
        style_layout.addWidget(style_info)
        
        style_group.setLayout(style_layout)
        layout.addWidget(style_group)
        
        layout.addStretch()
        
        # Botón ejecutar
        self.btn_screenshots = QPushButton("🖼️ Generar Pantallazos")
        self.btn_screenshots.setStyleSheet("""
            QPushButton {
                background-color: #C73E1D; 
                color: white; 
                font-weight: bold; 
                padding: 10px; 
                border: none; 
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #A33118;
            }
            QPushButton:pressed {
                background-color: #7D2612;
            }
        """)
        self.btn_screenshots.clicked.connect(self.ejecutar_pantallazos)
        layout.addWidget(self.btn_screenshots)
        
        tab.setLayout(layout)
        self.analysis_tab_widget.addTab(tab, "3.3 Pantallazos")

    def create_xml_subtab(self):
        """Sub-pestaña 3.3: Export XML"""
        tab = QtWidgets.QWidget()
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
        format_group = QtWidgets.QGroupBox("📋 Formato LandXML")
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
        process_group = QtWidgets.QGroupBox("🔄 Procesamiento por Tipo")
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
        self.btn_xml.clicked.connect(self.ejecutar_xml)
        layout.addWidget(self.btn_xml)
        
        tab.setLayout(layout)
        self.analysis_tab_widget.addTab(tab, "3.3 XML")
    
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
        self.proc_root.setText(settings.value("canchas/proc_root", r"E:\CANCHAS_QFIELD\QGIS PROCESAMIENTO\Archivos Procesados TERRENO"))
        self.gpkg_path.setText(settings.value("canchas/gpkg_path", ""))
        self.csv_folder.setText(settings.value("canchas/csv_folder", ""))
        self.img_folder.setText(settings.value("canchas/img_folder", ""))

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
    
    def update_resample_tooltip(self, algorithm):
        """Actualiza el tooltip del algoritmo de remuestreo según la selección"""
        tooltips = {
            'near': """🔵 NEAR (Vecino más cercano) - RÁPIDO
            
✅ VENTAJAS:
• Más rápido computacionalmente
• Preserva valores originales exactamente  
• No introduce nuevos valores

❌ DESVENTAJAS:
• Puede crear efectos de escalera
• Menos suave visualmente
• Discontinuidades en análisis volumétrico

💡 MEJOR PARA: Datos categóricos o cuando se requiere velocidad máxima""",

            'bilinear': """🟢 BILINEAR (Interpolación Bilineal) - RECOMENDADO ⭐
            
✅ VENTAJAS:
• Equilibrio perfecto velocidad/calidad
• Transiciones suaves y realistas
• Ideal para análisis volumétrico
• Reduce efectos de escalera

❌ DESVENTAJAS:
• Introduce valores promediados
• Ligeramente más lento que NEAR

💡 MEJOR PARA: Análisis volumétrico, topografía, datos continuos (TU CASO)""",

            'cubic': """🟡 CUBIC (Interpolación Cúbica) - ALTA CALIDAD
            
✅ VENTAJAS:
• Muy suave y realista
• Preserva mejor las curvas
• Excelente calidad visual
• Ideal para visualización

❌ DESVENTAJAS:
• Más lento que bilinear
• Puede crear valores irreales (overshooting)
• Computacionalmente intensivo

💡 MEJOR PARA: Visualización de alta calidad, análisis detallados""",

            'cubicspline': """🔴 CUBIC SPLINE - MÁXIMA CALIDAD
            
✅ VENTAJAS:
• Máxima suavidad posible
• Mejor preservación de curvaturas
• Calidad visual superior

❌ DESVENTAJAS:
• El más lento de todos
• Mayor posibilidad de artefactos
• Puede ser excesivo para análisis volumétrico

💡 MEJOR PARA: Análisis científicos muy detallados, investigación avanzada"""
        }
        
        self.resample_algorithm.setToolTip(tooltips.get(algorithm, "Algoritmo de remuestreo para alinear rasters"))
        
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
        
    def ejecutar_tabla(self):
        """Ejecutar proceso de creación de tabla base"""
        # Verificar que PROC_ROOT esté configurado
        if not self.proc_root.text().strip():
            self.log_message("❌ Error: Debe configurar la carpeta de procesamiento")
            return

        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.log_message("📋 Iniciando creación de tabla base...")
        self.log_message(f"📁 PROC_ROOT: {self.proc_root.text()}")
        self.log_message(f"🔢 Protocolo inicial: {self.protocolo_inicio.value()}")
        
        try:
            # Importar el procesador
            from .core.table_creation import TableCreationProcessor
            
            # Crear procesador con parámetros de la GUI
            processor = TableCreationProcessor(
                proc_root=self.proc_root.text(),
                protocolo_topografico_inicio=self.protocolo_inicio.value(),
                progress_callback=self.update_progress,
                log_callback=self.log_message
            )
            
            # Ejecutar creación de tabla completa
            resultado = processor.ejecutar_creacion_tabla_completa()
            
            if resultado['success']:
                self.log_message("🎉 ¡Tabla base creada exitosamente!")
                self.log_message(f"📊 {resultado.get('registros_creados', 0)} registros creados")
                self.log_message(f"📋 Tabla: {resultado.get('tabla_nombre', 'N/A')}")
                self.save_settings()
            else:
                self.log_message(f"❌ Error: {resultado['message']}")
                if 'details' in resultado:
                    self.log_message("📋 Ver detalles del error arriba")
                
        except Exception as e:
            self.log_message(f"❌ Error inesperado: {e}")
        finally:
            self.progress_bar.setVisible(False)
        
    def ejecutar_volumenes(self):
        """Ejecutar proceso de cálculo de volúmenes"""
        # Verificar que PROC_ROOT esté configurado
        if not self.proc_root.text().strip():
            self.log_message("❌ Error: Debe configurar la carpeta de procesamiento")
            return

        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.log_message("📊 Iniciando cálculo de volúmenes y espesores...")
        self.log_message(f"📁 PROC_ROOT: {self.proc_root.text()}")
        self.log_message(f"🎯 Puntos aleatorios: {self.num_random_points.value()}")
        self.log_message(f"📏 Espesor mínimo: {self.min_espesor.text()} metros")
        self.log_message(f"🔄 Algoritmo remuestreo: {self.resample_algorithm.currentText()}")
        
        try:
            # Importar el procesador
            from .core.volume_calculation import VolumeCalculationProcessor
            
            # Crear procesador con parámetros de la GUI
            processor = VolumeCalculationProcessor(
                proc_root=self.proc_root.text(),
                num_random_points=self.num_random_points.value(),
                min_espesor=float(self.min_espesor.text()),
                resample_algorithm=self.resample_algorithm.currentText(),
                progress_callback=self.update_progress,
                log_callback=self.log_message
            )
            
            # Ejecutar cálculo completo
            resultado = processor.ejecutar_calculo_volumenes_completo()
            
            if resultado['success']:
                self.log_message("🎉 ¡Cálculo de volúmenes completado exitosamente!")
                self.log_message(f"📊 {resultado.get('registros_procesados', 0)} registros procesados")
                self.log_message(f"🗺️ DEMs actualizados: {', '.join(resultado.get('dem_actualizados', []))}")
                self.save_settings()
            else:
                self.log_message(f"❌ Error: {resultado['message']}")
                if 'details' in resultado:
                    self.log_message("📋 Ver detalles del error arriba")
                
        except Exception as e:
            self.log_message(f"❌ Error inesperado: {e}")
        finally:
            self.progress_bar.setVisible(False)
        
    def ejecutar_pantallazos(self):
        """Ejecutar proceso de generación de pantallazos"""
        # Verificar que PROC_ROOT esté configurado
        if not self.proc_root.text().strip():
            self.log_message("❌ Error: Debe configurar la carpeta de procesamiento")
            return

        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.log_message("📸 Iniciando generación de pantallazos...")
        self.log_message(f"📁 PROC_ROOT: {self.proc_root.text()}")
        self.log_message(f"📐 Dimensiones: {self.screenshot_width.value()}×{self.screenshot_height.value()} px")
        self.log_message(f"🔍 Factor expansión: {self.expansion_factor.value()}")
        self.log_message(f"🖼️ Capa fondo: {self.background_layer.text()}")
        
        try:
            # Importar el procesador
            from .core.screenshot_generation import ScreenshotGenerationProcessor
            
            # Crear procesador con parámetros de la GUI
            processor = ScreenshotGenerationProcessor(
                proc_root=self.proc_root.text(),
                screenshot_width=self.screenshot_width.value(),
                screenshot_height=self.screenshot_height.value(),
                expansion_factor=self.expansion_factor.value(),
                background_layer=self.background_layer.text(),
                progress_callback=self.update_progress,
                log_callback=self.log_message
            )
            
            # Ejecutar generación completa
            resultado = processor.ejecutar_generacion_pantallazos_completa()
            
            if resultado['success']:
                self.log_message("🎉 ¡Pantallazos generados exitosamente!")
                self.log_message(f"📸 {resultado.get('pantallazos_exitosos', 0)}/{resultado.get('total_pantallazos', 0)} pantallazos exitosos")
                self.log_message(f"📁 Guardados en: {resultado.get('carpeta_salida', 'N/A')}")
                self.save_settings()
            else:
                self.log_message(f"❌ Error: {resultado['message']}")
                if 'details' in resultado:
                    self.log_message("📋 Ver detalles del error arriba")
                
        except Exception as e:
            self.log_message(f"❌ Error inesperado: {e}")
        finally:
            self.progress_bar.setVisible(False)
    
    def ejecutar_volumenes_pantallazos(self):
        """Ejecutar proceso unificado de volúmenes y pantallazos"""
        # Verificar que PROC_ROOT esté configurado
        if not self.proc_root.text().strip():
            self.log_message("❌ Error: Debe configurar la carpeta de procesamiento")
            return

        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.log_message("📊📸 Iniciando proceso unificado de volúmenes y pantallazos...")
        self.log_message(f"📁 PROC_ROOT: {self.proc_root.text()}")
        self.log_message(f"🎯 Puntos aleatorios: {self.num_random_points.value()}")
        self.log_message(f"📏 Espesor mínimo: {self.min_espesor.text()} metros")
        self.log_message(f"🔄 Algoritmo remuestreo: {self.resample_algorithm.currentText()}")
        self.log_message(f"📐 Dimensiones imágenes: {self.screenshot_width.value()}×{self.screenshot_height.value()} px")
        self.log_message(f"🔍 Factor expansión: {self.expansion_factor.value()}")
        self.log_message(f"🖼️ Capa fondo: {self.background_layer.text()}")
        
        try:
            # Importar el procesador unificado
            from .core.volume_screenshot import VolumeScreenshotProcessor
            
            # Crear procesador con parámetros de la GUI
            processor = VolumeScreenshotProcessor(
                proc_root=self.proc_root.text(),
                num_random_points=self.num_random_points.value(),
                min_espesor=float(self.min_espesor.text()),
                resample_algorithm=self.resample_algorithm.currentText(),
                screenshot_width=self.screenshot_width.value(),
                screenshot_height=self.screenshot_height.value(),
                expansion_factor=self.expansion_factor.value(),
                background_layer=self.background_layer.text(),
                progress_callback=self.update_progress,
                log_callback=self.log_message
            )
            
            # Ejecutar proceso unificado
            resultado = processor.ejecutar_calculo_volumenes_con_pantallazos()
            
            if resultado['success']:
                self.log_message("🎉 ¡Proceso unificado completado exitosamente!")
                self.log_message(f"📊 {resultado.get('registros_procesados', 0)} registros procesados")
                self.log_message(f"📸 {resultado.get('pantallazos_exitosos', 0)} pantallazos generados")
                self.log_message(f"📁 Planos regulares: {resultado.get('carpeta_planos', 'N/A')}")
                self.log_message(f"📁 Planos MovTierra: {resultado.get('carpeta_movtierra', 'N/A')}")
                self.save_settings()
            else:
                self.log_message(f"❌ Error: {resultado['message']}")
                if 'details' in resultado:
                    self.log_message("📋 Ver detalles del error arriba")
                
        except Exception as e:
            self.log_message(f"❌ Error inesperado: {e}")
        finally:
            self.progress_bar.setVisible(False)
        
    def ejecutar_xml(self):
        """Ejecutar proceso de exportación XML"""
        # Verificar que PROC_ROOT esté configurado
        if not self.proc_root.text().strip():
            self.log_message("❌ Error: Debe configurar la carpeta de procesamiento")
            return

        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.log_message("📄 Iniciando exportación a LandXML...")
        self.log_message(f"📁 PROC_ROOT: {self.proc_root.text()}")
        # Configuración optimizada fija (configurable en código)
        swap_xy = True  # Intercambiar coordenadas X-Y (común para sistemas locales)
        raster_sample_step = 2  # Muestreo cada 2 píxeles (equilibrio calidad/rendimiento)
        self.log_message(f"🔄 Intercambiar X-Y: {'Sí' if swap_xy else 'No'}")
        self.log_message(f"📐 Paso muestreo rasters: {raster_sample_step} píxeles")
        
        try:
            # Importar el procesador
            from .core.xml_export import XMLExportProcessor
            
            # Crear procesador con configuración optimizada
            processor = XMLExportProcessor(
                proc_root=self.proc_root.text(),
                swap_xy=swap_xy,
                raster_sample_step=raster_sample_step,
                progress_callback=self.update_progress,
                log_callback=self.log_message
            )
            
            # Ejecutar exportación completa
            resultado = processor.ejecutar_exportacion_xml_completa()
            
            if resultado['success']:
                self.log_message("🎉 ¡Exportación XML completada exitosamente!")
                self.log_message(f"📄 {resultado.get('archivos_exitosos', 0)}/{resultado.get('total_archivos', 0)} archivos XML generados")
                self.log_message(f"📁 Guardados en: {resultado.get('carpeta_salida', 'N/A')}")
                self.save_settings()
            else:
                self.log_message(f"❌ Error: {resultado['message']}")
                if 'capas_disponibles' in resultado:
                    self.log_message(f"📋 Capas disponibles: {', '.join(resultado['capas_disponibles'])}")
                if 'subgrupos_disponibles' in resultado:
                    self.log_message(f"📋 Subgrupos disponibles: {', '.join(resultado['subgrupos_disponibles'])}")
                if 'details' in resultado:
                    self.log_message("📋 Ver detalles del error arriba")
                
        except Exception as e:
            self.log_message(f"❌ Error inesperado: {e}")
        finally:
            self.progress_bar.setVisible(False)

    def create_reports_tab(self):
        """Pestaña 4: Datos para Reporte"""
        tab = QtWidgets.QWidget()
        layout = QVBoxLayout()
        
        # Header principal
        header_layout = QHBoxLayout()
        icon_label = QLabel("📄")
        icon_label.setStyleSheet("font-size: 24px; margin-right: 10px;")
        title_label = QLabel("DATOS PARA REPORTE")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #2E4057;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc = QLabel("Genera datos auxiliares para reportes y realiza análisis histórico")
        desc.setStyleSheet("color: gray; margin-bottom: 15px; font-size: 12px;")
        layout.addWidget(desc)
        
        # Eliminado el grupo de compositor
        
        # Configuración de reportes
        config_group = QtWidgets.QGroupBox("📋 Tablas utilizadas")
        config_layout = QVBoxLayout()
        
        # Info de la tabla base
        table_info = QLabel("� Tabla Base Datos: Contiene los datos actuales")
        table_info.setStyleSheet("color: #666; margin: 5px 0;")
        config_layout.addWidget(table_info)
        
        # Info de la tabla histórica
        table_hist_info = QLabel("📊 DATOS HISTORICOS: Almacena todos los datos históricos y actuales")
        table_hist_info.setStyleSheet("color: #666; margin: 5px 0;")
        config_layout.addWidget(table_hist_info)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Proceso de Fusión
        merge_group = QtWidgets.QGroupBox("� Proceso de Fusión de Datos")
        merge_layout = QVBoxLayout()
        
        merge_info = QLabel("""Al ejecutar "Generar Datos Reporte", se realizan las siguientes acciones:

        0️⃣ Detección y normalización automática de formatos de fecha
        1️⃣ Fusión de datos históricos
        2️⃣ Análisis histórico (fechas de intervención y crecimiento anual)
        3️⃣ Generación de gráficos de barras por sector (G1)
        4️⃣ Generación de series temporales de espesores (G2)
        5️⃣ Generación de pantallazos heatmap (PH)
        6️⃣ Clasificación automática de espesores

        La tabla "DATOS HISTORICOS" queda actualizada con todos los datos procesados
        y es la que debe utilizarse como fuente para reportes.""")
        merge_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #f8f8f8; padding: 10px; border: 1px solid #ddd; border-radius: 3px;")
        merge_layout.addWidget(merge_info)
        
        merge_group.setLayout(merge_layout)
        layout.addWidget(merge_group)
        
        # Análisis histórico
        historical_group = QtWidgets.QGroupBox("📈 Análisis Histórico")
        historical_layout = QVBoxLayout()
        
        # Periodo para crecimiento anual
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Periodo para cálculo de crecimiento anual:"))
        self.dias_crecimiento = QtWidgets.QSpinBox()
        self.dias_crecimiento.setMinimum(30)
        self.dias_crecimiento.setMaximum(730)  # 2 años
        self.dias_crecimiento.setValue(365)    # 1 año por defecto
        self.dias_crecimiento.setSuffix(" días")
        period_layout.addWidget(self.dias_crecimiento)
        period_layout.addStretch()
        historical_layout.addLayout(period_layout)
        
        # Información de columnas generadas
        columnas_info = QLabel("""El proceso de análisis histórico genera las siguientes columnas:

1️⃣ "Ultima Intervencion": Fecha de última intervención para mismo Muro/Sector
    • Busca en DATOS HISTORICOS intervenciones anteriores a la fecha del registro
    • Formato: YYYY-MM-DD (ej: 2025-05-15)

2️⃣ "Ultimo Crecimiento Anual": Suma de espesores en el período configurado
    • Calcula la suma de espesores para registros dentro del período establecido
    • Formato: Número decimal (ej: 24.4640)

3️⃣ "Movimiento Tierra Anual Neto": Diferencia Fill - Cut en el período
    • Calcula Fill - Cut del último año (movimiento neto de tierra)
    • Formato: Número decimal (ej: 150.2500)

4️⃣ "Relleno Anual Acumulado": Suma total de Fill en el período
    • Suma todos los valores de relleno del último año
    • Formato: Número decimal (ej: 200.7850)

5️⃣ "Corte Anual Acumulado": Suma total de Cut en el período
    • Suma todos los valores de corte del último año
    • Formato: Número decimal (ej: 50.5350)""")
        columnas_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #f0f0ff; padding: 10px; border: 1px solid #ddd; border-radius: 3px; margin-top: 10px;")
        historical_layout.addWidget(columnas_info)
        
        historical_group.setLayout(historical_layout)
        layout.addWidget(historical_group)
        
        # Clasificación de Espesores
        clasificacion_group = QtWidgets.QGroupBox("📏 Clasificación Automática de Espesores")
        clasificacion_layout = QVBoxLayout()
        
        clasificacion_info = QLabel("""Durante el proceso de "Generar Datos Reporte" se ejecutan automáticamente:

📅 Normalización de fechas: Detecta y convierte formatos automáticamente
📏 Clasificación de espesores según rangos:
• Mayor a 1.3 = "Triple Capa"
• Mayor a 0.8 = "Doble Capa" 
• Mayor a 0.2 = "Relleno"
• Entre -0.2 a 0.2 = "Corte Relleno"
• Menor a -0.2 = "Corte"

La columna 'Comentarios Espesor' se crea/actualiza automáticamente en 'Tabla Base Datos'.""")
        clasificacion_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #f9f9f9; padding: 10px; border: 1px solid #ddd; border-radius: 3px;")
        clasificacion_layout.addWidget(clasificacion_info)
        
        clasificacion_group.setLayout(clasificacion_layout)
        layout.addWidget(clasificacion_group)
        
        layout.addStretch()
        
        # Botón ejecutar - CAMBIADO
        self.btn_reports = QPushButton("� Generar Datos Reporte")
        self.btn_reports.setStyleSheet("""
            QPushButton {
                background-color: #2E4057; 
                color: white; 
                font-weight: bold; 
                padding: 12px; 
                border: none; 
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #3D5A75;
            }
            QPushButton:pressed {
                background-color: #1E2B3A;
            }
        """)
        self.btn_reports.clicked.connect(self.ejecutar_fusion_y_analisis)
        layout.addWidget(self.btn_reports)
        
        # Botón para abrir el compositor - AGREGADO AQUÍ
        self.btn_open_composer = QPushButton("🖨️ Abrir Compositor")
        self.btn_open_composer.setStyleSheet("""
            QPushButton {
                background-color: #2E4057; 
                color: white; 
                font-weight: bold; 
                padding: 12px; 
                border: none; 
                border-radius: 5px;
                font-size: 13px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #3D5A75;
            }
            QPushButton:pressed {
                background-color: #1E2B3A;
            }
        """)
        self.btn_open_composer.clicked.connect(self.abrir_compositor_plantilla)
        layout.addWidget(self.btn_open_composer)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "4. Datos Reporte")

    def ejecutar_fusion_datos(self):
        """Ejecutar proceso de fusión de datos para reportes"""
        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.log_message("� Iniciando fusión de datos para reportes...")
        
        try:
            # Importar el procesador
            from .core.data_merge import DataMergeProcessor
            
            # Crear procesador
            processor = DataMergeProcessor(
                progress_callback=self.update_progress,
                log_callback=self.log_message
            )
            
            # Ejecutar fusión de datos
            resultado = processor.fusionar_datos_historicos()
            
            if resultado['success']:
                self.log_message("🎉 ¡Fusión de datos completada exitosamente!")
                self.log_message(f"📊 Registros copiados: {resultado.get('registros_copiados', 0)}")
                self.log_message(f"📊 Nuevos registros: {resultado.get('nuevos_ids', 0)}")
                self.log_message(f"� Total de registros en DATOS HISTORICOS: {resultado.get('total_registros', 0)}")
                self.log_message(f"ℹ️ Ahora puede usar la tabla 'DATOS HISTORICOS' para crear reportes manualmente en el compositor de QGIS")
                self.save_settings()
            else:
                self.log_message(f"❌ Error: {resultado['message']}")
                if 'details' in resultado:
                    self.log_message("📋 Ver detalles del error arriba")
                
        except ImportError as e:
            self.log_message(f"❌ Error de importación: {e}")
            self.log_message("ℹ️ Asegúrese de que el archivo data_merge.py exista en la carpeta core/")
        except Exception as e:
            self.log_message(f"❌ Error inesperado: {e}")
        finally:
            self.progress_bar.setVisible(False)
    
    def ejecutar_fusion_y_analisis(self):
        """Ejecutar proceso de fusión de datos, análisis histórico y generación de gráficos"""
        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Paso 1: Fusionar datos
        self.log_message("🔄 Iniciando proceso completo (fusión + análisis + gráficos)...")
        
        try:
            # Importar el procesador
            from .core.data_merge import DataMergeProcessor
            
            # Crear procesador
            processor = DataMergeProcessor(
                progress_callback=self.update_progress,
                log_callback=self.log_message
            )
            
            # Ejecutar fusión de datos
            self.log_message("📋 Paso 1: Fusión de datos históricos...")
            resultado = processor.fusionar_datos_historicos()
            
            if resultado['success']:
                self.log_message("✅ Fusión de datos completada")
                self.log_message(f"📊 Registros copiados: {resultado.get('registros_copiados', 0)}")
                self.log_message(f"📊 Nuevos registros: {resultado.get('nuevos_ids', 0)}")
                self.log_message(f"📋 Total de registros en DATOS HISTORICOS: {resultado.get('total_registros', 0)}")
                
                # Paso 2: Análisis histórico
                self.log_message("📈 Paso 2: Iniciando análisis histórico...")
                self.log_message(f"⚙️ Periodo crecimiento anual: {self.dias_crecimiento.value()} días")
                
                try:
                    # Importar el procesador
                    from .core.historical_analysis import HistoricalAnalysisProcessor
                    
                    # Crear procesador
                    processor_hist = HistoricalAnalysisProcessor(
                        progress_callback=self.update_progress,
                        log_callback=self.log_message
                    )
                    
                    # Ejecutar análisis histórico
                    resultado_hist = processor_hist.ejecutar_analisis_historico_completo(
                        dias_crecimiento_anual=self.dias_crecimiento.value()
                    )
                    
                    if resultado_hist['success']:
                        self.log_message("✅ Análisis histórico completado")
                        
                        # Mostrar resumen de intervenciones
                        resultado_interv = resultado_hist.get('resultado_intervencion', {})
                        self.log_message(f"📅 Análisis de intervenciones:")
                        self.log_message(f"  • Registros con intervención: {resultado_interv.get('registros_actualizados', 0)}")
                        self.log_message(f"  • Registros sin intervención previa: {resultado_interv.get('registros_sin_intervencion', 0)}")
                        
                        # Mostrar resumen de crecimiento
                        resultado_crec = resultado_hist.get('resultado_crecimiento', {})
                        self.log_message(f"📏 Análisis de crecimiento anual:")
                        self.log_message(f"  • Registros con crecimiento calculado: {resultado_crec.get('registros_actualizados', 0)}")
                        self.log_message(f"  • Registros sin datos suficientes: {resultado_crec.get('registros_sin_datos', 0)}")
                        
                        self.log_message(f"🔄 Total de registros analizados: {resultado_hist.get('registros_totales', 0)}")
                        
                        # Paso 3: Generar gráficos de barras
                        self.log_message("📊 Paso 3: Generando gráficos de barras por sector...")
                        
                        try:
                            # Importar el generador de gráficos (usando la versión simple)
                            from .core.bar_charts_simple import SimpleBarChartGenerator
                            
                            # Obtener la ruta de procesamiento
                            proc_root = self.proc_root.text().strip()
                            if not proc_root:
                                self.log_message("⚠️ No se ha configurado la carpeta PROC_ROOT. No se generarán gráficos.")
                            else:
                                # Crear generador de gráficos
                                chart_generator = SimpleBarChartGenerator(
                                    proc_root=proc_root,
                                    progress_callback=self.update_progress,
                                    log_callback=self.log_message
                                )
                                
                                # Ejecutar generación de gráficos
                                resultado_charts = chart_generator.generar_graficos_barras()
                                
                                if resultado_charts['success']:
                                    self.log_message("✅ Generación de gráficos completada")
                                    self.log_message(f"📊 Gráficos generados: {resultado_charts.get('graficos_generados', 0)}")
                                    if resultado_charts.get('graficos_fallidos', 0) > 0:
                                        self.log_message(f"⚠️ Gráficos fallidos: {resultado_charts.get('graficos_fallidos', 0)}")
                                    self.log_message(f"📁 Carpeta de gráficos: {resultado_charts.get('carpeta_salida', '')}")
                                else:
                                    self.log_message(f"❌ Error en generación de gráficos: {resultado_charts['message']}")
                                    if 'details' in resultado_charts:
                                        self.log_message("📋 Ver detalles del error arriba")
                        
                        except ImportError as e:
                            self.log_message(f"❌ Error de importación: {e}")
                            self.log_message("ℹ️ Asegúrese de que el archivo bar_charts_simple.py exista en la carpeta core/")
                        except Exception as e:
                            import traceback
                            self.log_message(f"❌ Error inesperado en generación de gráficos: {e}")
                            self.log_message(traceback.format_exc())
                        
                        # Paso 4: Generar gráficos de series temporales
                        self.log_message("📈 Paso 4: Generando gráficos de series temporales...")
                        
                        try:
                            # Importar el generador de series temporales
                            from .core.time_series_charts import TimeSeriesChartGenerator
                            
                            # Obtener la ruta de procesamiento
                            proc_root = self.proc_root.text().strip()
                            if not proc_root:
                                self.log_message("⚠️ No se ha configurado la carpeta PROC_ROOT. No se generarán series temporales.")
                            else:
                                # Crear generador de series temporales
                                series_generator = TimeSeriesChartGenerator(
                                    proc_root=proc_root,
                                    progress_callback=self.update_progress,
                                    log_callback=self.log_message
                                )
                                
                                # Ejecutar generación de series temporales
                                resultado_series = series_generator.generar_graficos_series_temporales()
                                
                                if resultado_series['success']:
                                    self.log_message("✅ Generación de series temporales completada")
                                    self.log_message(f"📈 Series temporales generadas: {resultado_series.get('graficos_generados', 0)}")
                                    if resultado_series.get('graficos_fallidos', 0) > 0:
                                        self.log_message(f"⚠️ Series temporales fallidas: {resultado_series.get('graficos_fallidos', 0)}")
                                    self.log_message(f"📁 Carpeta de series temporales: {resultado_series.get('carpeta_salida', '')}")
                                else:
                                    self.log_message(f"❌ Error en generación de series temporales: {resultado_series['message']}")
                                    if 'details' in resultado_series:
                                        self.log_message("📋 Ver detalles del error arriba")
                        
                        except ImportError as e:
                            self.log_message(f"❌ Error de importación: {e}")
                            self.log_message("ℹ️ Asegúrese de que el archivo time_series_charts.py exista en la carpeta core/")
                        except Exception as e:
                            import traceback
                            self.log_message(f"❌ Error inesperado en generación de series temporales: {e}")
                            self.log_message(traceback.format_exc())
                        
                        # Paso 5: Generar pantallazos heatmap
                        self.log_message("📷 Paso 5: Generando pantallazos heatmap...")
                        
                        try:
                            # Importar el generador de pantallazos heatmap
                            from .core.heatmap_screenshots import HeatmapScreenshotGenerator
                            
                            # Obtener la ruta de procesamiento
                            proc_root = self.proc_root.text().strip()
                            if not proc_root:
                                self.log_message("⚠️ No se ha configurado la carpeta PROC_ROOT. No se generarán pantallazos heatmap.")
                            else:
                                # Crear generador de pantallazos heatmap
                                heatmap_generator = HeatmapScreenshotGenerator(
                                    proc_root=proc_root,
                                    progress_callback=self.update_progress,
                                    log_callback=self.log_message
                                )
                                
                                # Ejecutar generación de pantallazos heatmap
                                resultado_heatmap = heatmap_generator.generar_pantallazos_heatmap()
                                
                                if resultado_heatmap['success']:
                                    self.log_message("✅ Generación de pantallazos heatmap completada")
                                    self.log_message(f"📷 Pantallazos heatmap generados: {resultado_heatmap.get('graficos_generados', 0)}")
                                    if resultado_heatmap.get('graficos_fallidos', 0) > 0:
                                        self.log_message(f"⚠️ Pantallazos heatmap fallidos: {resultado_heatmap.get('graficos_fallidos', 0)}")
                                    self.log_message(f"📁 Carpeta de pantallazos heatmap: {resultado_heatmap.get('carpeta_salida', '')}")
                                else:
                                    self.log_message(f"❌ Error en generación de pantallazos heatmap: {resultado_heatmap['message']}")
                                    if 'details' in resultado_heatmap:
                                        self.log_message("📋 Ver detalles del error arriba")
                        
                        except ImportError as e:
                            self.log_message(f"❌ Error de importación: {e}")
                            self.log_message("ℹ️ Asegúrese de que el archivo heatmap_screenshots.py exista en la carpeta core/")
                        except Exception as e:
                            import traceback
                            self.log_message(f"❌ Error inesperado en generación de pantallazos heatmap: {e}")
                            self.log_message(traceback.format_exc())
                        
                        # Paso 6: Clasificar espesores automáticamente
                        self.log_message("📏 Paso 6: Clasificando espesores automáticamente...")
                        
                        try:
                            # Importar el procesador de clasificación
                            from .core.espesor_classification import EspesorClassificationProcessor
                            
                            # Crear procesador
                            processor_espesor = EspesorClassificationProcessor(
                                progress_callback=self.update_progress,
                                log_callback=self.log_message
                            )
                            
                            # Ejecutar clasificación
                            resultado_espesor = processor_espesor.ejecutar_clasificacion_espesor()
                            
                            if resultado_espesor['success']:
                                self.log_message("✅ Clasificación de espesores completada")
                                self.log_message(f"📊 Registros procesados: {resultado_espesor.get('registros_procesados', 0)}")
                                self.log_message(f"📋 Columna 'Comentarios Espesor' actualizada")
                            else:
                                self.log_message(f"❌ Error en clasificación de espesores: {resultado_espesor['message']}")
                                if 'details' in resultado_espesor:
                                    self.log_message("📋 Ver detalles del error arriba")
                        
                        except ImportError as e:
                            self.log_message(f"❌ Error de importación: {e}")
                            self.log_message("ℹ️ Asegúrese de que el archivo espesor_classification.py exista en la carpeta core/")
                        except Exception as e:
                            import traceback
                            self.log_message(f"❌ Error inesperado en clasificación de espesores: {e}")
                            self.log_message(traceback.format_exc())
                        
                        # Mensaje final
                        self.log_message("🎉 PROCESO COMPLETO FINALIZADO CON ÉXITO")
                        self.save_settings()
                    else:
                        self.log_message(f"❌ Error en análisis histórico: {resultado_hist['message']}")
                        if 'details' in resultado_hist:
                            self.log_message("📋 Ver detalles del error arriba")
                        
                except ImportError as e:
                    self.log_message(f"❌ Error de importación: {e}")
                    self.log_message("ℹ️ Asegúrese de que el archivo historical_analysis.py exista en la carpeta core/")
                except Exception as e:
                    self.log_message(f"❌ Error inesperado en análisis histórico: {e}")
            else:
                self.log_message(f"❌ Error en fusión: {resultado['message']}")
                if 'details' in resultado:
                    self.log_message("📋 Ver detalles del error arriba")
                
        except ImportError as e:
            self.log_message(f"❌ Error de importación: {e}")
            self.log_message("ℹ️ Asegúrese de que el archivo data_merge.py exista en la carpeta core/")
        except Exception as e:
            self.log_message(f"❌ Error inesperado en fusión: {e}")
        finally:
            self.progress_bar.setVisible(False)
            
    def ejecutar_reportes(self):
        """MÉTODO LEGACY - Ya no se utiliza pero se mantiene por compatibilidad"""
        self.log_message("⚠️ Esta funcionalidad ha sido reemplazada por 'Generar Datos Reporte'")
        self.log_message("ℹ️ Los reportes ahora se crean manualmente en el compositor de impresiones de QGIS")
        self.log_message("ℹ️ Use la tabla 'DATOS HISTORICOS' como fuente de datos para sus reportes")
    
    def abrir_compositor_plantilla(self):
        """Abre el compositor de impresión con la plantilla predefinida y configura Atlas"""
        try:
            from qgis.core import (
                QgsProject, QgsLayoutManager, QgsReadWriteContext, QgsPrintLayout,
                QgsMapLayer
            )
            from qgis.PyQt.QtXml import QDomDocument
            from qgis.utils import iface
            import os
            from datetime import datetime
            
            self.log_message("🖨️ Abriendo compositor con plantilla y configurando Atlas...")
            
            # Obtener la plantilla del plugin - usando la ruta correcta al directorio del plugin
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(plugin_dir, "resources", "templates", "Plantilla_Protocolos_LT.qpt")
            
            if not os.path.exists(template_path):
                self.log_message(f"❌ Error: No se encontró la plantilla en {template_path}")
                return
            
            # Obtener el PROC_ROOT para sustituirlo en las expresiones
            proc_root_text = self.proc_root.text().strip()
            if not proc_root_text:
                self.log_message("⚠️ PROC_ROOT no configurado, se usará la plantilla sin modificaciones")
                # Leer el archivo QPT sin modificaciones
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
            else:
                # Normalizar la ruta PROC_ROOT (usando forward slash)
                proc_root_normalized = proc_root_text.replace('\\', '/')
                
                # Leer el archivo QPT
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                # Reemplazo directo en el texto (enfoque más simple)
                self.log_message(f"🔄 Aplicando reemplazos de rutas con PROC_ROOT: {proc_root_normalized}")
                
                # Buscar patrones comunes de rutas en las expresiones
                patrones_rutas = [
                    # Patrones de rutas absolutas comunes (ajustar según sea necesario)
                    r"'[A-Z]:/[^']*?/IMAGENES/'",
                    r"'[A-Z]:/[^']*?/Planos/'",
                    r"'[A-Z]:/[^']*?/Perfiles/'",
                    r"'[A-Z]:/[^']*?/Aux Reporte/Grafico Barras/'",
                    r"'[A-Z]:/[^']*?/Aux Reporte/Grafico Series/'",
                    r"'[A-Z]:/[^']*?/Aux Reporte/Pantallazos Heatmap/'",
                    # Patrón para reemplazar [PROC_ROOT] placeholder
                    r"'\[PROC_ROOT\]/Perfiles/'"
                ]
                
                reemplazos_rutas = [
                    f"'{proc_root_normalized}/IMAGENES/'",
                    f"'{proc_root_normalized}/Planos/'",
                    f"'{proc_root_normalized}/Perfiles/'",
                    f"'{proc_root_normalized}/Aux Reporte/Grafico Barras/'",
                    f"'{proc_root_normalized}/Aux Reporte/Grafico Series/'",
                    f"'{proc_root_normalized}/Aux Reporte/Pantallazos Heatmap/'",
                    f"'{proc_root_normalized}/Perfiles/'"
                ]
                
                # Aplicar todos los reemplazos
                import re
                for i, patron in enumerate(patrones_rutas):
                    # Contar cuántas veces aparece el patrón
                    coincidencias = len(re.findall(patron, template_content))
                    if coincidencias > 0:
                        # Aplicar el reemplazo
                        template_content = re.sub(patron, reemplazos_rutas[i], template_content)
                        self.log_message(f"✔️ Reemplazo aplicado: {patron} → {reemplazos_rutas[i]} ({coincidencias} coincidencias)")
                
            # Crear un archivo temporal con el contenido modificado
            import tempfile
            temp_qpt = os.path.join(tempfile.gettempdir(), f"Plantilla_LT_Temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.qpt")
            
            with open(temp_qpt, 'w', encoding='utf-8') as f:
                f.write(template_content)
                
            self.log_message(f"📄 Plantilla temporal creada en: {temp_qpt}")
            
            # Ahora cargar el documento desde el archivo temporal
            with open(temp_qpt, 'r', encoding='utf-8') as f:
                template_content = f.read()
                
            # Crear un documento DOM a partir del contenido modificado
            doc = QDomDocument()
            doc.setContent(template_content)
            
            # Obtener el proyecto actual y el layout manager
            project = QgsProject.instance()
            layout_manager = project.layoutManager()
            
            # Crear nombre único para la composición
            layout_name = f"Reporte_Canchas_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Verificar si ya existe un layout con ese nombre y eliminarlo
            existing_layout = layout_manager.layoutByName(layout_name)
            if existing_layout:
                layout_manager.removeLayout(existing_layout)
                
            # Crear un nuevo layout
            layout = QgsPrintLayout(project)
            layout.setName(layout_name)
            
            # Cargar desde documento
            context = QgsReadWriteContext()
            if not layout.readLayoutXml(doc.documentElement(), doc, context):
                self.log_message("❌ Error al cargar la plantilla")
                return
                
            # Agregar al proyecto
            layout_manager.addLayout(layout)
            
            # Buscar la capa "Tabla Base Datos"
            tabla_layer = None
            for layer in project.mapLayers().values():
                if layer.name() == "Tabla Base Datos" and layer.type() == QgsMapLayer.VectorLayer:
                    tabla_layer = layer
                    break
                    
            if not tabla_layer:
                self.log_message("❌ Error: No se encontró la capa 'Tabla Base Datos'")
                self.log_message("ℹ️ Debe crear la tabla base antes de usar esta funcionalidad")
                return
                
            # Configurar Atlas para la tabla
            atlas = layout.atlas()
            if atlas:
                # Configurar capa de cobertura
                atlas.setCoverageLayer(tabla_layer)
                
                # Habilitar Atlas
                atlas.setEnabled(True)
                
                # Configurar orden
                atlas.setSortFeatures(True)
                atlas.setSortExpression('"Protocolo Topografico"')
                atlas.setSortAscending(True)
                
                self.log_message("✔️ Atlas configurado correctamente con 'Tabla Base Datos'")
            
            # El código para actualizar las expresiones dinámicas ahora se ejecuta directamente sobre el XML
                
            # Abrir el diseñador con el layout
            iface.openLayoutDesigner(layout)
            
            self.log_message("✔️ Compositor abierto exitosamente")
            self.log_message("ℹ️ Configure filtros por muro usando la expresión: \"Muro\" = 'Principal'")
            self.log_message("ℹ️ Para generar PDF use el botón 'Exportar Atlas como PDF'")
            
        except Exception as e:
            import traceback
            self.log_message(f"❌ Error al abrir el compositor: {str(e)}")
            self.log_message(f"📋 Detalles: {traceback.format_exc()}")
        
    def create_historical_tab(self):
        """Pestaña 5: Análisis Histórico"""
        tab = QtWidgets.QWidget()
        layout = QVBoxLayout()
        
        # Header principal
        header_layout = QHBoxLayout()
        icon_label = QLabel("📈")
        icon_label.setStyleSheet("font-size: 24px; margin-right: 10px;")
        title_label = QLabel("ANÁLISIS HISTÓRICO")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #5F4B8B;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc = QLabel("Realiza análisis de datos históricos para calcular fechas de intervención y crecimiento anual")
        desc.setStyleSheet("color: gray; margin-bottom: 15px; font-size: 12px;")
        layout.addWidget(desc)
        
        # Configuración del análisis histórico
        config_group = QtWidgets.QGroupBox("⚙️ Configuración de Análisis")
        config_layout = QVBoxLayout()
        
        # Periodo para crecimiento anual
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Periodo para crecimiento anual:"))
        self.dias_crecimiento = QtWidgets.QSpinBox()
        self.dias_crecimiento.setMinimum(30)
        self.dias_crecimiento.setMaximum(730)  # 2 años
        self.dias_crecimiento.setValue(365)    # 1 año por defecto
        self.dias_crecimiento.setSuffix(" días")
        period_layout.addWidget(self.dias_crecimiento)
        period_layout.addStretch()
        config_layout.addLayout(period_layout)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Columnas generadas
        columnas_group = QtWidgets.QGroupBox("📊 Columnas que se Generarán")
        columnas_layout = QVBoxLayout()
        
        columnas_info = QLabel("""1️⃣ "Ultima Intervencion": Fecha de la última intervención en el mismo Muro y Sector
    • Input: Muro, Sector y Fecha de cada registro
    • Busca en DATOS HISTORICOS intervenciones anteriores
    • Formato: YYYY-MM-DD (ej: 2025-05-15)

2️⃣ "Ultimo Crecimiento Anual": Suma de espesores en el periodo configurado
    • Input: Muro, Sector y Fecha de cada registro
    • Calcula suma de espesores en el periodo definido
    • Formato: Número decimal (ej: 24.4640)

3️⃣ "Movimiento Tierra Anual Neto": Diferencia Fill - Cut en el periodo
    • Input: Muro, Sector y Fecha de cada registro
    • Calcula Fill - Cut del último año (movimiento neto)
    • Formato: Número decimal (ej: 150.2500)

4️⃣ "Relleno Anual Acumulado": Suma total de Fill en el periodo
    • Input: Muro, Sector y Fecha de cada registro
    • Suma todos los valores de relleno del último año
    • Formato: Número decimal (ej: 200.7850)

5️⃣ "Corte Anual Acumulado": Suma total de Cut en el periodo
    • Input: Muro, Sector y Fecha de cada registro
    • Suma todos los valores de corte del último año
    • Formato: Número decimal (ej: 50.5350)""")
        columnas_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #f8f8f8; padding: 10px; border: 1px solid #5F4B8B; border-radius: 3px;")
        columnas_layout.addWidget(columnas_info)
        
        columnas_group.setLayout(columnas_layout)
        layout.addWidget(columnas_group)
        
        # Proceso detallado
        proceso_group = QtWidgets.QGroupBox("🔄 Proceso de Análisis")
        proceso_layout = QVBoxLayout()
        
        proceso_info = QLabel("""El proceso de análisis realiza cinco cálculos principales:

1. ÚLTIMA INTERVENCIÓN:
   • Para cada registro de "Tabla Base Datos"
   • Busca en "DATOS HISTORICOS" registros con el mismo Muro y Sector
   • Identifica la fecha más reciente anterior a la fecha del registro
   • Guarda esta fecha como "Ultima Intervencion"

2. CRECIMIENTO ANUAL:
   • Para cada registro de "Tabla Base Datos"
   • Busca en "DATOS HISTORICOS" registros con el mismo Muro y Sector
   • Dentro del periodo configurado (365 días por defecto)
   • Suma todos los espesores encontrados
   • Guarda este valor como "Ultimo Crecimiento Anual"

3. MOVIMIENTOS DE TIERRA ANUALES:
   • Para cada registro busca Fill y Cut del último año
   • Calcula movimiento neto (Fill - Cut) en metros cúbicos
   • Calcula relleno acumulado (suma total de Fill)
   • Calcula corte acumulado (suma total de Cut)
   • Todos los valores con precisión de 4 decimales
""")
        proceso_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #f0f0ff; padding: 10px; border: 1px solid #5F4B8B; border-radius: 3px;")
        proceso_layout.addWidget(proceso_info)
        
        proceso_group.setLayout(proceso_layout)
        layout.addWidget(proceso_group)
        
        layout.addStretch()
        
        # Botón ejecutar
        self.btn_historical = QPushButton("📈 Ejecutar Análisis Histórico")
        self.btn_historical.setStyleSheet("""
            QPushButton {
                background-color: #5F4B8B; 
                color: white; 
                font-weight: bold; 
                padding: 12px; 
                border: none; 
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #483A6A;
            }
            QPushButton:pressed {
                background-color: #372A54;
            }
        """)
        self.btn_historical.clicked.connect(self.ejecutar_analisis_historico)
        layout.addWidget(self.btn_historical)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "5. Análisis Histórico")
        
    def ejecutar_analisis_historico(self):
        """Ejecutar proceso de análisis histórico"""
        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.log_message("📈 Iniciando análisis histórico...")
        self.log_message(f"⚙️ Periodo crecimiento anual: {self.dias_crecimiento.value()} días")
        
        try:
            # Importar el procesador
            from .core.historical_analysis import HistoricalAnalysisProcessor
            
            # Crear procesador
            processor = HistoricalAnalysisProcessor(
                progress_callback=self.update_progress,
                log_callback=self.log_message
            )
            
            # Ejecutar análisis histórico
            resultado = processor.ejecutar_analisis_historico_completo(
                dias_crecimiento_anual=self.dias_crecimiento.value()
            )
            
            if resultado['success']:
                self.log_message("🎉 ¡Análisis histórico completado exitosamente!")
                
                # Mostrar resumen de intervenciones
                resultado_interv = resultado.get('resultado_intervencion', {})
                self.log_message(f"📅 Análisis de intervenciones:")
                self.log_message(f"  • Registros con intervención: {resultado_interv.get('registros_actualizados', 0)}")
                self.log_message(f"  • Registros sin intervención previa: {resultado_interv.get('registros_sin_intervencion', 0)}")
                
                # Mostrar resumen de crecimiento
                resultado_crec = resultado.get('resultado_crecimiento', {})
                self.log_message(f"📏 Análisis de crecimiento anual:")
                self.log_message(f"  • Registros con crecimiento calculado: {resultado_crec.get('registros_actualizados', 0)}")
                self.log_message(f"  • Registros sin datos suficientes: {resultado_crec.get('registros_sin_datos', 0)}")
                
                self.log_message(f"🔄 Total de registros procesados: {resultado.get('registros_totales', 0)}")
                self.save_settings()
            else:
                self.log_message(f"❌ Error: {resultado['message']}")
                if 'details' in resultado:
                    self.log_message("📋 Ver detalles del error arriba")
                
        except ImportError as e:
            self.log_message(f"❌ Error de importación: {e}")
            self.log_message("ℹ️ Asegúrese de que el archivo historical_analysis.py exista en la carpeta core/")
        except Exception as e:
            self.log_message(f"❌ Error inesperado: {e}")
        finally:
            self.progress_bar.setVisible(False)