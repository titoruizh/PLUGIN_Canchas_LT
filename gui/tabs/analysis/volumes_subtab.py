# -*- coding: utf-8 -*-
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                                QLabel, QGroupBox, QSpinBox, QDoubleSpinBox, 
                                QLineEdit, QComboBox)

class VolumesSubTab(QWidget):
    """
    Sub-pestaña 3.2: Volúmenes y Pantallazos (UNIFICADO)
    Encargada de la UI y ejecución del proceso incremental unificado.
    """
    
    # Señales
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    execute_signal = pyqtSignal(dict) # Envía diccionario de parámetros
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()
        
    def setupUi(self):
        layout = QVBoxLayout()
        
        # Header con icono y título
        header_layout = QHBoxLayout()
        icon_label = QLabel("📊📸")
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
        config_group = QGroupBox("⚙️ Parámetros de Cálculo Volumétrico")
        config_layout = QVBoxLayout()
        
        # Número de puntos aleatorios
        random_points_layout = QHBoxLayout()
        random_points_layout.addWidget(QLabel("Puntos aleatorios para análisis:"))
        self.num_random_points = QSpinBox()
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
        self.resample_algorithm = QComboBox()
        self.resample_algorithm.addItems(['near', 'bilinear', 'cubic', 'cubicspline'])
        self.resample_algorithm.setCurrentText('bilinear')
        self.resample_algorithm.currentTextChanged.connect(self.update_resample_tooltip)
        self.update_resample_tooltip('bilinear')
        
        resample_layout.addWidget(self.resample_algorithm)
        resample_layout.addStretch()
        config_layout.addLayout(resample_layout)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Configuración de pantallazos
        screenshot_group = QGroupBox("📸 Parámetros de Pantallazos")
        screenshot_layout = QVBoxLayout()
        
        # Dimensiones
        dimensions_layout = QHBoxLayout()
        dimensions_layout.addWidget(QLabel("Dimensiones:"))
        
        self.screenshot_width = QSpinBox()
        self.screenshot_width.setMinimum(400)
        self.screenshot_width.setMaximum(2000)
        self.screenshot_width.setValue(800)
        self.screenshot_width.setSuffix(" px")
        dimensions_layout.addWidget(self.screenshot_width)
        
        dimensions_layout.addWidget(QLabel("×"))
        
        self.screenshot_height = QSpinBox()
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
        self.expansion_factor = QDoubleSpinBox()
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
        process_group = QGroupBox("🔄 Proceso Incremental Unificado")
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
        self.btn_volume_screenshot.clicked.connect(self.emit_execute_signal)
        layout.addWidget(self.btn_volume_screenshot)
        
        self.setLayout(layout)

    def update_resample_tooltip(self, algorithm):
        """Actualiza el tooltip del algoritmo de remuestreo"""
        tooltips = {
            'near': "🔵 NEAR (Vecino más cercano) - RÁPIDO\n\n✅ VENTAJAS:\n• Más rápido computacionalmente\n• Preserva valores originales\n\n❌ DESVENTAJAS:\n• Efecto escalera",
            'bilinear': "🟢 BILINEAR - RECOMENDADO ⭐\n\n✅ VENTAJAS:\n• Equilibrio velocidad/calidad\n• Suave\n\n💡 IDEAL PARA: Análisis volumétrico",
            'cubic': "🟡 CUBIC - ALTA CALIDAD\n\n✅ VENTAJAS:\n• Visualmente superior\n\n❌ DESVENTAJAS:\n• Lento\n• Puede crear valores irreales (overshooting)",
            'cubicspline': "🔴 CUBIC SPLINE - MÁXIMA CALIDAD\n\n✅ VENTAJAS:\n• Máxima suavidad\n\n❌ DESVENTAJAS:\n• Muy lento"
        }
        self.resample_algorithm.setToolTip(tooltips.get(algorithm, "Algoritmo de remuestreo"))

    def emit_execute_signal(self):
        """Emite señal con todos los parámetros"""
        params = {
            'num_random_points': self.num_random_points.value(),
            'min_espesor': float(self.min_espesor.text()),
            'resample_algorithm': self.resample_algorithm.currentText(),
            'screenshot_width': self.screenshot_width.value(),
            'screenshot_height': self.screenshot_height.value(),
            'expansion_factor': self.expansion_factor.value(),
            'background_layer': self.background_layer.text()
        }
        self.execute_signal.emit(params)

    def ejecutar_volumenes_pantallazos(self, proc_root):
        """
        Ejecuta la lógica unificada de volúmenes y pantallazos.
        """
        if not proc_root or not proc_root.strip():
            self.log_signal.emit("❌ Error: Debe configurar la carpeta de procesamiento (PROC_ROOT)")
            return False
            
        self.progress_signal.emit(0, "Iniciando")
        
        self.log_signal.emit("📊📸 Iniciando proceso unificado de volúmenes y pantallazos...")
        self.log_signal.emit(f"📁 PROC_ROOT: {proc_root}")
        self.log_signal.emit(f"📏 Espesor mínimo: {self.min_espesor.text()}")
        self.log_signal.emit(f"🖼️ Dimensiones: {self.screenshot_width.value()}x{self.screenshot_height.value()}")
        
        try:
            # Importar procesador unificado
            from ....core.volume_screenshot import VolumeScreenshotProcessor
            
            processor = VolumeScreenshotProcessor(
                proc_root=proc_root,
                num_random_points=self.num_random_points.value(),
                min_espesor=float(self.min_espesor.text()),
                resample_algorithm=self.resample_algorithm.currentText(),
                screenshot_width=self.screenshot_width.value(),
                screenshot_height=self.screenshot_height.value(),
                expansion_factor=self.expansion_factor.value(),
                background_layer=self.background_layer.text(),
                progress_callback=lambda v, m="": self.progress_signal.emit(v, m),
                log_callback=lambda m: self.log_signal.emit(m)
            )
            
            # Ejecutar
            resultado = processor.ejecutar_calculo_volumenes_con_pantallazos()
            
            if resultado['success']:
                self.log_signal.emit("🎉 ¡Proceso unificado completado exitosamente!")
                self.log_signal.emit(f"📊 Registros procesados: {resultado.get('registros_procesados', 0)}")
                return True
            else:
                self.log_signal.emit(f"❌ Error: {resultado['message']}")
                if 'details' in resultado:
                    self.log_signal.emit("📋 Ver detalles del error arriba")
                return False
                
        except ImportError as e:
            self.log_signal.emit(f"❌ Error de importación: {e}")
            return False
        except Exception as e:
            self.log_signal.emit(f"❌ Error inesperado: {e}")
            return False
