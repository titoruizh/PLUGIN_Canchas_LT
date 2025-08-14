# -*- coding: utf-8 -*-
import os
from qgis.PyQt import QtWidgets, QtCore
from qgis.PyQt.QtCore import pyqtSignal, QThread, QSettings, QTime
from qgis.PyQt.QtWidgets import (QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, 
                                QPushButton, QTextEdit, QProgressBar, QLabel, 
                                QLineEdit, QFileDialog)

class CanchasDialog(QDialog):
    """Diálogo principal del plugin con pestañas reorganizado"""
    
    def __init__(self):
        super(CanchasDialog, self).__init__()
        self.setupUi()
        self.init_connections()
        self.load_settings()
        
    def setupUi(self):
        """Crear la interfaz con pestañas reorganizada (1-2-3-4)"""
        self.setWindowTitle("Canchas Las Tortolas - Procesador Topográfico")
        self.setMinimumSize(800, 600)
        
        # Layout principal
        layout = QVBoxLayout()
        
        # Crear widget de pestañas principales (solo 3)
        self.tab_widget = QTabWidget()
        
        # Crear las 3 pestañas principales
        self.create_validation_tab()      # Pestaña 1
        self.create_processing_tab()      # Pestaña 2
        self.create_analysis_tab()        # Pestaña 3 (con sub-pestañas)
        self.create_reports_tab()         # Pestaña 4 (NUEVA)
        
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
    
    def create_validation_tab(self):
        """Pestaña 1: Validación (SIN CAMBIOS)"""
        tab = QtWidgets.QWidget()
        layout = QVBoxLayout()
        
        # Título y descripción con estilo
        title = QLabel("📋 VALIDACIÓN DE ARCHIVOS")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #F18F01;")
        layout.addWidget(title)
        
        desc = QLabel("Valida archivos CSV/ASC espacialmente y los prepara para procesamiento")
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Grupo de carpeta principal
        main_group = QtWidgets.QGroupBox("📁 CARPETA PRINCIPAL DE TRABAJO")
        main_layout = QVBoxLayout()
        
        # PROC_ROOT con estilo
        proc_layout = QHBoxLayout()
        proc_layout.addWidget(QLabel("Carpeta Procesamiento (PROC_ROOT):"))
        self.proc_root = QLineEdit()
        self.proc_root.setPlaceholderText("E:\\CANCHAS_QFIELD\\QGIS PROCESAMIENTO\\Archivos Procesados TERRENO")
        self.proc_root.setText(r"E:\CANCHAS_QFIELD\QGIS PROCESAMIENTO\Archivos Procesados TERRENO")
        self.proc_root.setStyleSheet("padding: 5px; border: 1px solid #F18F01; border-radius: 3px;")
        proc_layout.addWidget(self.proc_root)
        btn_proc = QPushButton("📁")
        btn_proc.setMaximumWidth(40)
        btn_proc.setStyleSheet("""
            QPushButton {
                background-color: #F18F01; 
                color: white; 
                border: none; 
                border-radius: 3px; 
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #9c5d03;
            }
        """)
        btn_proc.clicked.connect(lambda: self.select_folder(self.proc_root))
        proc_layout.addWidget(btn_proc)
        main_layout.addLayout(proc_layout)
        
        # Info sobre carpetas que se crearán
        carpetas_info = QLabel("""📤 Carpetas que se crearán automáticamente:
    • CSV-ASC (archivos procesados)    • IMAGENES (fotos con prefijo F)
    • XML (archivos LandXML)          • Planos (pantallazos JPG)
    • backups (respaldos de originales)""")
        carpetas_info.setStyleSheet("color: #666; background-color: #e8f5f3; padding: 10px; border: 1px solid #F18F01; border-radius: 3px; margin: 5px 0;")
        main_layout.addWidget(carpetas_info)
        
        main_group.setLayout(main_layout)
        layout.addWidget(main_group)
        
        # Grupo de archivos originales
        orig_group = QtWidgets.QGroupBox("📥 ARCHIVOS ORIGINALES")
        orig_layout = QVBoxLayout()
        
        # GPKG original
        gpkg_layout = QHBoxLayout()
        gpkg_layout.addWidget(QLabel("GPKG Original:"))
        self.gpkg_path = QLineEdit()
        self.gpkg_path.setPlaceholderText("Ruta al archivo Levantamientos.gpkg")
        self.gpkg_path.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 3px;")
        gpkg_layout.addWidget(self.gpkg_path)
        btn_gpkg = QPushButton("📁")
        btn_gpkg.setMaximumWidth(40)
        btn_gpkg.setStyleSheet("""
            QPushButton {
                background-color: #666; 
                color: white; 
                border: none; 
                border-radius: 3px; 
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        btn_gpkg.clicked.connect(lambda: self.select_file(self.gpkg_path, "GPKG (*.gpkg)"))
        gpkg_layout.addWidget(btn_gpkg)
        orig_layout.addLayout(gpkg_layout)
        
        # Carpeta CSV-ASC
        csv_layout = QHBoxLayout()
        csv_layout.addWidget(QLabel("Carpeta CSV-ASC:"))
        self.csv_folder = QLineEdit()
        self.csv_folder.setPlaceholderText("Carpeta con archivos CSV y ASC originales")
        self.csv_folder.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 3px;")
        csv_layout.addWidget(self.csv_folder)
        btn_csv = QPushButton("📁")
        btn_csv.setMaximumWidth(40)
        btn_csv.setStyleSheet("""
            QPushButton {
                background-color: #666; 
                color: white; 
                border: none; 
                border-radius: 3px; 
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        btn_csv.clicked.connect(lambda: self.select_folder(self.csv_folder))
        csv_layout.addWidget(btn_csv)
        orig_layout.addLayout(csv_layout)
        
        # Carpeta imágenes
        img_layout = QHBoxLayout()
        img_layout.addWidget(QLabel("Carpeta Imágenes:"))
        self.img_folder = QLineEdit()
        self.img_folder.setPlaceholderText("Carpeta con archivos JPG originales")
        self.img_folder.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 3px;")
        img_layout.addWidget(self.img_folder)
        btn_img = QPushButton("📁")
        btn_img.setMaximumWidth(40)
        btn_img.setStyleSheet("""
            QPushButton {
                background-color: #666; 
                color: white; 
                border: none; 
                border-radius: 3px; 
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        btn_img.clicked.connect(lambda: self.select_folder(self.img_folder))
        img_layout.addWidget(btn_img)
        orig_layout.addLayout(img_layout)
        
        orig_group.setLayout(orig_layout)
        layout.addWidget(orig_group)
        
        # Grupo de validaciones que se realizarán
        validation_group = QtWidgets.QGroupBox("🔍 Validaciones que se realizarán")
        validation_layout = QVBoxLayout()
        
        validations_info = QLabel("""ESPACIALES: Intersección con polígonos de muros y sectores
    FORMATO: Estructura de columnas y tipos de datos
    COORDENADAS: Validación de rangos Norte/Este/Cota  
    DEM: Comparación de cotas contra modelos digitales
    GEOMETRÍA: Generación de ConcaveHull para archivos CSV
    ARCHIVOS: Conversión de formatos y limpieza de nombres""")
        validations_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #f0f8f7; padding: 10px; border: 1px solid #F18F01; border-radius: 3px;")
        validation_layout.addWidget(validations_info)
        
        validation_group.setLayout(validation_layout)
        layout.addWidget(validation_group)
        
        layout.addStretch()
        
        # Botón ejecutar con estilo mejorado
        self.btn_validation = QPushButton("🔍 Ejecutar Validación Completa")
        self.btn_validation.setStyleSheet("""
            QPushButton {
                background-color: #F18F01; 
                color: white; 
                font-weight: bold; 
                padding: 12px; 
                border: none; 
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #9c5d03;
            }
            QPushButton:pressed {
                background-color: #0F6B5F;
            }
        """)
        self.btn_validation.clicked.connect(self.ejecutar_validacion)
        layout.addWidget(self.btn_validation)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "1. Validación")
    
    def create_processing_tab(self):
        """Pestaña 2: Procesamiento (SIN CAMBIOS)"""
        tab = QtWidgets.QWidget()
        layout = QVBoxLayout()
        
        # Título y descripción
        title = QLabel("🗺️ PROCESAMIENTO ESPACIAL")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #F18F01;")
        layout.addWidget(title)
        
        desc = QLabel("Genera capas de puntos, polígonos y triangulaciones a partir de archivos validados")
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Grupo de parámetros
        params_group = QtWidgets.QGroupBox("⚙️ Parámetros de Procesamiento")
        params_layout = QVBoxLayout()
        
        # Tamaño de píxel
        pixel_layout = QHBoxLayout()
        pixel_layout.addWidget(QLabel("Tamaño de píxel (TIN):"))
        self.pixel_size = QLineEdit("0.1")
        self.pixel_size.setMaximumWidth(100)
        self.pixel_size.setToolTip("Resolución para la interpolación TIN (metros)")
        pixel_layout.addWidget(self.pixel_size)
        pixel_layout.addWidget(QLabel("metros"))
        pixel_layout.addStretch()
        params_layout.addLayout(pixel_layout)
        
        # Tolerancia de suavizado ASC
        smooth_layout = QHBoxLayout()
        smooth_layout.addWidget(QLabel("Tolerancia suavizado (ASC):"))
        self.smooth_tolerance = QLineEdit("1.0")
        self.smooth_tolerance.setMaximumWidth(100)
        self.smooth_tolerance.setToolTip("Tolerancia para simplificar geometrías ASC")
        smooth_layout.addWidget(self.smooth_tolerance)
        smooth_layout.addWidget(QLabel("metros"))
        smooth_layout.addStretch()
        params_layout.addLayout(smooth_layout)
        
        # Distancia mínima vértices
        min_dist_layout = QHBoxLayout()
        min_dist_layout.addWidget(QLabel("Distancia mínima vértices:"))
        self.min_dist_vertices = QLineEdit("2.0")
        self.min_dist_vertices.setMaximumWidth(100)
        self.min_dist_vertices.setToolTip("Distancia mínima entre vértices extremos")
        min_dist_layout.addWidget(self.min_dist_vertices)
        min_dist_layout.addWidget(QLabel("metros"))
        min_dist_layout.addStretch()
        params_layout.addLayout(min_dist_layout)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Grupo de salidas esperadas
        output_group = QtWidgets.QGroupBox("📤 Salidas que se generarán")
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
        self.btn_processing.clicked.connect(self.ejecutar_procesamiento)
        layout.addWidget(self.btn_processing)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "2. Procesamiento")

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
        
        # Crear las 4 sub-pestañas
        self.create_table_subtab()        # 3.1
        self.create_volumes_subtab()      # 3.2  
        self.create_screenshots_subtab()  # 3.3
        self.create_xml_subtab()          # 3.4
        
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
        """Sub-pestaña 3.2: Volúmenes"""
        tab = QtWidgets.QWidget()
        layout = QVBoxLayout()
        
        # Header con icono y título
        header_layout = QHBoxLayout()
        icon_label = QLabel("📐")
        icon_label.setStyleSheet("font-size: 20px; margin-right: 8px;")
        title_label = QLabel("CÁLCULO DE VOLÚMENES")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #F18F01;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc = QLabel("Calcula cut/fill, espesores mínimo/máximo y actualiza DEM incrementalmente")
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Configuración de volúmenes
        config_group = QtWidgets.QGroupBox("⚙️ Parámetros de Cálculo")
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
        self.min_espesor = QLineEdit("0.001")
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
        self.resample_algorithm.setCurrentText('near')
        self.resample_algorithm.setToolTip("Algoritmo para alinear rasters en el pegado incremental")
        resample_layout.addWidget(self.resample_algorithm)
        resample_layout.addStretch()
        config_layout.addLayout(resample_layout)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Proceso incremental
        process_group = QtWidgets.QGroupBox("🔄 Proceso Incremental")
        process_layout = QVBoxLayout()
        
        process_info = QLabel("""ORDEN CRONOLÓGICO: Procesa filas por fecha de tabla
    CÁLCULO VOLUMEN: TIN_nuevo vs DEM_muro → Cut/Fill/Espesor
    PEGADO INCREMENTAL: TIN_nuevo se pega sobre DEM_muro
    ACTUALIZACIÓN: DEM_muro se actualiza para siguiente fila

    Resultado: Cut, Fill, Espesor, Espesor mínimo, Espesor máximo""")
        process_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #fff8e7; padding: 10px; border: 1px solid #F18F01; border-radius: 3px;")
        process_layout.addWidget(process_info)
        
        process_group.setLayout(process_layout)
        layout.addWidget(process_group)
        
        layout.addStretch()
        
        # Botón ejecutar
        self.btn_volumes = QPushButton("📊 Calcular Volúmenes y Espesores")
        self.btn_volumes.setStyleSheet("""
            QPushButton {
                background-color: #F18F01; 
                color: white; 
                font-weight: bold; 
                padding: 10px; 
                border: none; 
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #D17A01;
            }
            QPushButton:pressed {
                background-color: #B16801;
            }
        """)
        self.btn_volumes.clicked.connect(self.ejecutar_volumenes)
        layout.addWidget(self.btn_volumes)
        
        tab.setLayout(layout)
        self.analysis_tab_widget.addTab(tab, "3.2 Volúmenes")

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
        """Sub-pestaña 3.4: Export XML"""
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
        
        # Configuración de exportación
        export_group = QtWidgets.QGroupBox("🔧 Configuración de Exportación")
        export_layout = QVBoxLayout()
        
        # Intercambio XY
        swap_layout = QHBoxLayout()
        self.swap_xy = QtWidgets.QCheckBox("Intercambiar coordenadas X-Y")
        self.swap_xy.setChecked(True)
        self.swap_xy.setToolTip("Intercambia X e Y en la exportación (común para algunos sistemas)")
        swap_layout.addWidget(self.swap_xy)
        swap_layout.addStretch()
        export_layout.addLayout(swap_layout)
        
        # Paso de muestreo para rasters
        raster_step_layout = QHBoxLayout()
        raster_step_layout.addWidget(QLabel("Paso de muestreo (rasters ASC):"))
        self.raster_sample_step = QtWidgets.QSpinBox()
        self.raster_sample_step.setMinimum(1)
        self.raster_sample_step.setMaximum(10)
        self.raster_sample_step.setValue(2)
        self.raster_sample_step.setToolTip("Cada cuántos píxeles muestrear del raster (1=todos, 2=cada 2, etc)")
        raster_step_layout.addWidget(self.raster_sample_step)
        raster_step_layout.addWidget(QLabel("píxeles"))
        raster_step_layout.addStretch()
        export_layout.addLayout(raster_step_layout)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        # Formato LandXML
        format_group = QtWidgets.QGroupBox("📋 Formato LandXML")
        format_layout = QVBoxLayout()
        
        format_info = QLabel("""ESTÁNDAR: LandXML 1.2
    UNIDADES: Métricos (metro, metro cuadrado, metro cúbico)
    SUPERFICIE: Triangulated Irregular Network (TIN)
    DATOS: Puntos 3D + Caras triangulares
    METADATOS: Área 2D/3D, elevación mín/máx""")
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
        self.analysis_tab_widget.addTab(tab, "3.4 XML")
    
    def init_connections(self):
        """Conectar señales"""
        self.btn_close.clicked.connect(self.close)
    
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
    
    def ejecutar_validacion(self):
        """Ejecutar proceso de validación completo"""
        # Verificar que PROC_ROOT esté configurado
        if not self.proc_root.text().strip():
            self.log_message("❌ Error: Debe configurar la carpeta de procesamiento (PROC_ROOT)")
            return
            
        # Verificar que existan las rutas originales
        if not self.gpkg_path.text().strip():
            self.log_message("❌ Error: Debe seleccionar el archivo GPKG original")
            return
            
        if not self.csv_folder.text().strip():
            self.log_message("❌ Error: Debe seleccionar la carpeta CSV-ASC")
            return
            
        if not self.img_folder.text().strip():
            self.log_message("❌ Error: Debe seleccionar la carpeta de imágenes")
            return
        
        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.log_message("🔍 Iniciando validación completa...")
        self.log_message(f"📁 PROC_ROOT: {self.proc_root.text()}")
        self.log_message(f"📄 GPKG: {self.gpkg_path.text()}")
        self.log_message(f"📊 CSV-ASC: {self.csv_folder.text()}")
        self.log_message(f"🖼️ Imágenes: {self.img_folder.text()}")
        
        try:
            # Importar el procesador completo
            from .core.validation import ValidationProcessor
            
            # Crear procesador con callbacks
            processor = ValidationProcessor(
                proc_root=self.proc_root.text(),
                orig_gpkg=self.gpkg_path.text(),
                dir_csv_orig=self.csv_folder.text(),
                dir_img_orig=self.img_folder.text(),
                progress_callback=self.update_progress,
                log_callback=self.log_message
            )
            
            # Ejecutar validación completa
            resultado = processor.ejecutar_validacion_completa()
            
            if resultado['success']:
                self.log_message("🎉 ¡Validación completada exitosamente!")
                self.log_message(f"📦 Backup creado en: {resultado.get('backup_folder', 'N/A')}")
                self.save_settings()
            else:
                self.log_message(f"❌ Error: {resultado['message']}")
                if 'details' in resultado:
                    self.log_message("📋 Ver detalles del error arriba")
                
        except ImportError as e:
            self.log_message(f"❌ Error: No se pudo importar el módulo de validación: {e}")
        except Exception as e:
            self.log_message(f"❌ Error inesperado: {e}")
        finally:
            self.progress_bar.setVisible(False)

    def update_progress(self, value, message=""):
        """Callback para actualizar progreso"""
        self.progress_bar.setValue(value)
        if message:
            self.log_message(f"📋 {message}")
        
    def ejecutar_procesamiento(self):
        """Ejecutar proceso de procesamiento espacial"""
        # Verificar que PROC_ROOT esté configurado
        if not self.proc_root.text().strip():
            self.log_message("❌ Error: Debe configurar la carpeta de procesamiento")
            return

        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.log_message("⚙️ Iniciando procesamiento espacial...")
        self.log_message(f"📁 PROC_ROOT: {self.proc_root.text()}")
        self.log_message(f"🔧 Píxel TIN: {self.pixel_size.text()} metros")
        self.log_message(f"🎯 Tolerancia suavizado: {self.smooth_tolerance.text()} metros")
        self.log_message(f"📏 Distancia mínima vértices: {self.min_dist_vertices.text()} metros")
        
        try:
            # Importar el procesador
            from .core.processing import ProcessingProcessor
            
            # Crear procesador con parámetros de la GUI
            processor = ProcessingProcessor(
                proc_root=self.proc_root.text(),
                pixel_size=float(self.pixel_size.text()),
                suavizado_tolerance=float(self.smooth_tolerance.text()),
                min_dist_vertices=float(self.min_dist_vertices.text()),
                progress_callback=self.update_progress,
                log_callback=self.log_message
            )
            
            # Ejecutar procesamiento completo
            resultado = processor.ejecutar_procesamiento_completo()
            
            if resultado['success']:
                self.log_message("🎉 ¡Procesamiento espacial completado exitosamente!")
                self.log_message(f"📊 {resultado.get('total_archivos', 0)} archivos procesados")
                self.log_message(f"📁 Grupo creado: {resultado.get('group_name', 'N/A')}")
                self.save_settings()
            else:
                self.log_message(f"❌ Error: {resultado['message']}")
                if 'details' in resultado:
                    self.log_message("📋 Ver detalles del error arriba")
                
        except Exception as e:
            self.log_message(f"❌ Error inesperado: {e}")
        finally:
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
        self.log_message(f"🔄 Intercambiar X-Y: {'Sí' if self.swap_xy.isChecked() else 'No'}")
        self.log_message(f"📐 Paso muestreo rasters: {self.raster_sample_step.value()} píxeles")
        
        try:
            # Importar el procesador
            from .core.xml_export import XMLExportProcessor
            
            # Crear procesador con parámetros de la GUI
            processor = XMLExportProcessor(
                proc_root=self.proc_root.text(),
                swap_xy=self.swap_xy.isChecked(),
                raster_sample_step=self.raster_sample_step.value(),
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
        """Pestaña 4: Reportes PDF"""
        tab = QtWidgets.QWidget()
        layout = QVBoxLayout()
        
        # Header principal
        header_layout = QHBoxLayout()
        icon_label = QLabel("📄")
        icon_label.setStyleSheet("font-size: 24px; margin-right: 10px;")
        title_label = QLabel("REPORTES PDF")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #2E4057;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc = QLabel("Genera protocolos PDF por muro usando Atlas con la plantilla QPT")
        desc.setStyleSheet("color: gray; margin-bottom: 15px; font-size: 12px;")
        layout.addWidget(desc)
        
        # Configuración de reportes
        config_group = QtWidgets.QGroupBox("📋 Configuración de Reportes")
        config_layout = QVBoxLayout()
        
        # Info de la plantilla
        template_info = QLabel(f"📄 Plantilla: Plantilla_Protocolos_LT.qpt")
        template_info.setStyleSheet("color: #666; margin: 5px 0;")
        config_layout.addWidget(template_info)
        
        # Info de la tabla
        table_info = QLabel("📊 Fuente de datos: Tabla Base Datos")
        table_info.setStyleSheet("color: #666; margin: 5px 0;")
        config_layout.addWidget(table_info)
        
        # Formato
        format_info = QLabel("📐 Formato: A4 Vertical, 300 DPI")
        format_info.setStyleSheet("color: #666; margin: 5px 0;")
        config_layout.addWidget(format_info)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Muros a generar
        muros_group = QtWidgets.QGroupBox("🗺️ Reportes por Muro")
        muros_layout = QVBoxLayout()
        
        muros_info = QLabel("""Se generarán 3 archivos PDF filtrados por muro:

        📄 Protocolos_PRINCIPAL.pdf → Registros con Muro = 'Principal'
        📄 Protocolos_OESTE.pdf → Registros con Muro = 'Oeste'  
        📄 Protocolos_ESTE.pdf → Registros con Muro = 'Este'

        Cada PDF contiene todas las hojas del muro ordenadas por Protocolo Topográfico""")
        muros_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #f8f8f8; padding: 10px; border: 1px solid #ddd; border-radius: 3px;")
        muros_layout.addWidget(muros_info)
        
        muros_group.setLayout(muros_layout)
        layout.addWidget(muros_group)
        
        # Recursos necesarios
        recursos_group = QtWidgets.QGroupBox("📁 Recursos Necesarios")
        recursos_layout = QVBoxLayout()
        
        recursos_info = QLabel("""PLANTILLA: resources/templates/Plantilla_Protocolos_LT.qpt
        LOGOS: resources/logos/ (archivos PNG/JPG)
        FIRMAS: resources/firmas/{operador}.png (mapeo automático)
        
        Las rutas se actualizan automáticamente en la plantilla""")
        recursos_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #fff8e7; padding: 10px; border: 1px solid #F18F01; border-radius: 3px;")
        recursos_layout.addWidget(recursos_info)
        
        recursos_group.setLayout(recursos_layout)
        layout.addWidget(recursos_group)
        
        layout.addStretch()
        
        # Botón ejecutar
        self.btn_reports = QPushButton("📄 Generar Reportes PDF por Muro")
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
        self.btn_reports.clicked.connect(self.ejecutar_reportes)
        layout.addWidget(self.btn_reports)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "4. Reportes")

    def ejecutar_reportes(self):
        """Ejecutar proceso de generación de reportes PDF"""
        # Verificar que PROC_ROOT esté configurado
        if not self.proc_root.text().strip():
            self.log_message("❌ Error: Debe configurar la carpeta de procesamiento")
            return

        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.log_message("📄 Iniciando generación de reportes PDF...")
        self.log_message(f"📁 PROC_ROOT: {self.proc_root.text()}")
        
        try:
            # Importar el procesador
            from .core.pdf_reports import PDFReportsProcessor
            
            # Obtener directorio del plugin
            plugin_dir = os.path.dirname(__file__)
            
            # Crear procesador
            processor = PDFReportsProcessor(
                proc_root=self.proc_root.text(),
                plugin_dir=plugin_dir,
                progress_callback=self.update_progress,
                log_callback=self.log_message
            )
            
            # Ejecutar generación completa
            resultado = processor.ejecutar_generacion_reportes_completa()
            
            if resultado['success']:
                self.log_message("🎉 ¡Reportes PDF generados exitosamente!")
                reportes = resultado.get('reportes_generados', [])
                for reporte in reportes:
                    self.log_message(f"📄 {reporte['muro']}: {reporte['archivo']}")
                self.log_message(f"📁 Guardados en: {resultado.get('carpeta_salida', 'N/A')}")
                self.save_settings()
            else:
                self.log_message(f"❌ Error: {resultado['message']}")
                if 'recursos_faltantes' in resultado:
                    self.log_message("📋 Recursos faltantes:")
                    for recurso in resultado['recursos_faltantes']:
                        self.log_message(f"  • {recurso}")
                
        except Exception as e:
            self.log_message(f"❌ Error inesperado: {e}")
        finally:
            self.progress_bar.setVisible(False)