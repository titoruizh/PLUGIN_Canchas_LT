# -*- coding: utf-8 -*-
import os
from qgis.PyQt import QtWidgets, QtCore
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                                QPushButton, QLabel, QGroupBox, QSpinBox)
from qgis.utils import iface
from datetime import datetime

class ReportsTab(QWidget):
    """
    Pestaña 4: Datos para Reporte
    Genera datos auxiliares para reportes y realiza análisis histórico.
    """
    
    # Señales
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    execute_reports_signal = pyqtSignal()  # Solicitud para ejecutar reportes
    execute_composer_signal = pyqtSignal() # Solicitud para abrir compositor
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()
        
    def setupUi(self):
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
        
        # Configuración de reportes
        config_group = QGroupBox("📋 Tablas utilizadas")
        config_layout = QVBoxLayout()
        
        # Info de la tabla base
        table_info = QLabel("📝 Tabla Base Datos: Contiene los datos actuales")
        table_info.setStyleSheet("color: #666; margin: 5px 0;")
        config_layout.addWidget(table_info)
        
        # Info de la tabla histórica
        table_hist_info = QLabel("📊 DATOS HISTORICOS: Almacena todos los datos históricos y actuales")
        table_hist_info.setStyleSheet("color: #666; margin: 5px 0;")
        config_layout.addWidget(table_hist_info)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Proceso de Fusión
        merge_group = QGroupBox("🔄 Proceso de Fusión de Datos")
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
        historical_group = QGroupBox("📈 Análisis Histórico")
        historical_layout = QVBoxLayout()
        
        # Periodo para crecimiento anual
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Periodo para cálculo de crecimiento anual:"))
        self.dias_crecimiento = QSpinBox()
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
        clasificacion_group = QGroupBox("📏 Clasificación Automática de Espesores")
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
        
        # Botón ejecutar reporte
        self.btn_reports = QPushButton("🚀 Generar Datos Reporte")
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
        self.btn_reports.clicked.connect(self.execute_reports_signal.emit)
        layout.addWidget(self.btn_reports)
        
        # Botón para abrir el compositor
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
        self.btn_open_composer.clicked.connect(self.execute_composer_signal.emit)
        layout.addWidget(self.btn_open_composer)
        
        self.setLayout(layout)

    def ejecutar_fusion_y_analisis(self, proc_root):
        """Ejecutar proceso de fusión de datos, análisis histórico y generación de gráficos"""
        
        # Paso 1: Fusionar datos
        self.log_signal.emit("🔄 Iniciando proceso completo (fusión + análisis + gráficos)...")
        
        try:
            # Importar procesadores (Lazy import para evitar ciclos)
            # Nota: Usamos rutas relativas asumiendo que este archivo está en gui/tabs/
            # y core está en ../../core
            # Pero en runtime de QGIS la importación relativa puede ser tricky si no es paquete
            # Mejor usar importación relativa desde el paquete padre
            from ...core.data_merge import DataMergeProcessor
            from ...core.historical_analysis import HistoricalAnalysisProcessor
            from ...core.bar_charts_simple import SimpleBarChartGenerator
            from ...core.time_series_charts import TimeSeriesChartGenerator
            from ...core.heatmap_screenshots import HeatmapScreenshotGenerator
            from ...core.espesor_classification import EspesorClassificationProcessor
            
            # 1. Fusión de Datos
            processor = DataMergeProcessor(
                progress_callback=self.progress_signal.emit,
                log_callback=self.log_signal.emit
            )
            
            self.log_signal.emit("📋 Paso 1: Fusión de datos históricos...")
            resultado = processor.fusionar_datos_historicos()
            
            if not resultado['success']:
                self.log_signal.emit(f"❌ Error en fusión: {resultado['message']}")
                if 'details' in resultado: self.log_signal.emit("📋 Ver detalles del error arriba")
                return False

            self.log_signal.emit("✅ Fusión de datos completada")
            self.log_signal.emit(f"📊 Registros copiados: {resultado.get('registros_copiados', 0)}")
            self.log_signal.emit(f"📊 Nuevos registros: {resultado.get('nuevos_ids', 0)}")
            self.log_signal.emit(f"📋 Total de registros en DATOS HISTORICOS: {resultado.get('total_registros', 0)}")
            self.log_signal.emit(f"📋 Total de registros en DATOS HISTORICOS: {resultado.get('total_registros', 0)}")
            
            # 1.5. Carga de Reportes de Laboratorio (Excel)
            from ...core.lab_report import LabReportLoader
            from qgis.core import QgsProject
            
            # Buscar archivo Excel
            plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            report_folder = os.path.join(plugin_dir, "update N Informe")
            excel_path = None
            if os.path.exists(report_folder):
                for f in os.listdir(report_folder):
                    if f.endswith(".xlsx") and not f.startswith("~$"):
                        excel_path = os.path.join(report_folder, f)
                        break
            
            if excel_path:
                self.log_signal.emit(f"🧪 Detectado reporte de laboratorio: {os.path.basename(excel_path)}")
                
                # Buscar capa Tabla Base Datos
                layer_base = None
                for l in QgsProject.instance().mapLayers().values():
                    if l.name() == "Tabla Base Datos":
                        layer_base = l
                        break
                
                if layer_base:
                    loader = LabReportLoader(log_callback=self.log_signal.emit)
                    success_lab, msg_lab, stats_lab = loader.load_excel_and_enrich(excel_path, layer_base)
                    if success_lab:
                        self.log_signal.emit(f"✅ {msg_lab}")
                    else:
                        self.log_signal.emit(f"⚠️ {msg_lab}")
                else:
                     self.log_signal.emit("⚠️ No se encontró capa 'Tabla Base Datos', saltando integración de laboratorio.")
            else:
                 self.log_signal.emit("ℹ️ No se encontró reporte Excel en 'update N Informe', saltando este paso.")
            
            # 2. Análisis Histórico
            self.log_signal.emit("📈 Paso 2: Iniciando análisis histórico...")
            dias = self.dias_crecimiento.value()
            self.log_signal.emit(f"⚙️ Periodo crecimiento anual: {dias} días")
            
            processor_hist = HistoricalAnalysisProcessor(
                progress_callback=self.progress_signal.emit,
                log_callback=self.log_signal.emit
            )
            
            resultado_hist = processor_hist.ejecutar_analisis_historico_completo(
                dias_crecimiento_anual=dias
            )
            
            if not resultado_hist['success']:
                self.log_signal.emit(f"❌ Error en análisis histórico: {resultado_hist['message']}")
                if 'details' in resultado_hist: self.log_signal.emit("📋 Ver detalles del error arriba")
                return False

            self.log_signal.emit("✅ Análisis histórico completado")
            
            # Resumen de intervenciones
            resultado_interv = resultado_hist.get('resultado_intervencion', {})
            self.log_signal.emit(f"📅 Análisis de intervenciones:")
            self.log_signal.emit(f"  • Registros con intervención: {resultado_interv.get('registros_actualizados', 0)}")
            
            # Resumen de crecimiento
            resultado_crec = resultado_hist.get('resultado_crecimiento', {})
            self.log_signal.emit(f"📏 Análisis de crecimiento anual:")
            self.log_signal.emit(f"  • Registros con crecimiento calculado: {resultado_crec.get('registros_actualizados', 0)}")
            
            self.log_signal.emit(f"🔄 Total de registros analizados: {resultado_hist.get('registros_totales', 0)}")
            
            # 3. Gráficos de Barras
            self.log_signal.emit("📊 Paso 3: Generando gráficos de barras por sector...")
            if not proc_root:
                self.log_signal.emit("⚠️ No se ha configurado la carpeta PROC_ROOT. No se generarán gráficos.")
            else:
                chart_generator = SimpleBarChartGenerator(
                    proc_root=proc_root,
                    progress_callback=self.progress_signal.emit,
                    log_callback=self.log_signal.emit
                )
                
                resultado_charts = chart_generator.generar_graficos_barras()
                
                if resultado_charts['success']:
                    self.log_signal.emit("✅ Generación de gráficos completada")
                    self.log_signal.emit(f"📊 Gráficos generados: {resultado_charts.get('graficos_generados', 0)}")
                    self.log_signal.emit(f"📁 Carpeta: {resultado_charts.get('carpeta_salida', '')}")
                else:
                    self.log_signal.emit(f"❌ Error en gráficos: {resultado_charts['message']}")

            # 4. Series Temporales
            self.log_signal.emit("📈 Paso 4: Generando gráficos de series temporales...")
            if not proc_root:
                self.log_signal.emit("⚠️ No se ha configurado la carpeta PROC_ROOT.")
            else:
                series_generator = TimeSeriesChartGenerator(
                    proc_root=proc_root,
                    progress_callback=self.progress_signal.emit,
                    log_callback=self.log_signal.emit
                )
                
                resultado_series = series_generator.generar_graficos_series_temporales()
                
                if resultado_series['success']:
                    self.log_signal.emit("✅ Generación de series temporales completada")
                    self.log_signal.emit(f"📈 Series generadas: {resultado_series.get('graficos_generados', 0)}")
                    self.log_signal.emit(f"📁 Carpeta: {resultado_series.get('carpeta_salida', '')}")
                else:
                    self.log_signal.emit(f"❌ Error en series temporales: {resultado_series['message']}")

            # 5. Pantallazos Heatmap
            self.log_signal.emit("📷 Paso 5: Generando pantallazos heatmap...")
            if not proc_root:
                self.log_signal.emit("⚠️ No se ha configurado la carpeta PROC_ROOT.")
            else:
                heatmap_generator = HeatmapScreenshotGenerator(
                    proc_root=proc_root,
                    progress_callback=self.progress_signal.emit,
                    log_callback=self.log_signal.emit
                )
                
                resultado_heatmap = heatmap_generator.generar_pantallazos_heatmap()
                
                if resultado_heatmap['success']:
                    self.log_signal.emit("✅ Generación de pantallazos heatmap completada")
                    self.log_signal.emit(f"📷 Heatmaps generados: {resultado_heatmap.get('graficos_generados', 0)}")
                    self.log_signal.emit(f"📁 Carpeta: {resultado_heatmap.get('carpeta_salida', '')}")
                else:
                    self.log_signal.emit(f"❌ Error en heatmap: {resultado_heatmap['message']}")

            # 6. Clasificación de Espesores
            self.log_signal.emit("📏 Paso 6: Clasificando espesores automáticamente...")
            
            processor_espesor = EspesorClassificationProcessor(
                progress_callback=self.progress_signal.emit,
                log_callback=self.log_signal.emit
            )
            
            resultado_espesor = processor_espesor.ejecutar_clasificacion_espesor()
            
            if resultado_espesor['success']:
                self.log_signal.emit("✅ Clasificación de espesores completada")
                self.log_signal.emit(f"📊 Registros procesados: {resultado_espesor.get('registros_procesados', 0)}")
            else:
                self.log_signal.emit(f"❌ Error en clasificación: {resultado_espesor['message']}")

            self.log_signal.emit("🎉 PROCESO COMPLETO FINALIZADO CON ÉXITO")
            return True

        except ImportError as e:
            self.log_signal.emit(f"❌ Error de importación: {e}")
            self.log_signal.emit("ℹ️ Verifique la instalación del plugin y sus módulos core.")
            return False
        except Exception as e:
            import traceback
            self.log_signal.emit(f"❌ Error inesperado: {e}")
            self.log_signal.emit(traceback.format_exc())
            return False

    def abrir_compositor_plantilla(self, proc_root_text):
        """Abre el compositor de impresión con la plantilla predefinida y configura Atlas"""
        try:
            from qgis.core import (
                QgsProject, QgsLayoutManager, QgsReadWriteContext, QgsPrintLayout,
                QgsMapLayer
            )
            from qgis.PyQt.QtXml import QDomDocument
            import re
            import tempfile
            
            self.log_signal.emit("🖨️ Abriendo compositor con plantilla y configurando Atlas...")
            
            # Obtener path de la plantilla (subiendo 2 niveles desde gui/tabs)
            current_dir = os.path.dirname(os.path.abspath(__file__)) # gui/tabs
            plugin_dir = os.path.dirname(os.path.dirname(current_dir)) # plugin root
            template_path = os.path.join(plugin_dir, "resources", "templates", "Plantilla_Protocolos_LT.qpt")
            
            if not os.path.exists(template_path):
                self.log_signal.emit(f"❌ Error: No se encontró la plantilla en {template_path}")
                return False
            
            template_content = ""
            
            if not proc_root_text:
                self.log_signal.emit("⚠️ PROC_ROOT no configurado, se usará la plantilla sin modificaciones")
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
            else:
                # Normalizar ruta
                proc_root_normalized = proc_root_text.replace('\\', '/')
                
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                self.log_signal.emit(f"🔄 Aplicando reemplazos de rutas con PROC_ROOT: {proc_root_normalized}")
                
                patrones_rutas = [
                    r"'[A-Z]:/[^']*?/IMAGENES/'",
                    r"'[A-Z]:/[^']*?/Planos/'",
                    r"'[A-Z]:/[^']*?/Perfiles/'",
                    r"'[A-Z]:/[^']*?/Aux Reporte/Grafico Barras/'",
                    r"'[A-Z]:/[^']*?/Aux Reporte/Grafico Series/'",
                    r"'[A-Z]:/[^']*?/Aux Reporte/Pantallazos Heatmap/'",
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
                
                for i, patron in enumerate(patrones_rutas):
                    coincidencias = len(re.findall(patron, template_content))
                    if coincidencias > 0:
                        template_content = re.sub(patron, reemplazos_rutas[i], template_content)
                        self.log_signal.emit(f"✔️ Reemplazo aplicado: {patron} -> {reemplazos_rutas[i]}")

            # Archivo temporal
            temp_qpt = os.path.join(tempfile.gettempdir(), f"Plantilla_LT_Temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.qpt")
            with open(temp_qpt, 'w', encoding='utf-8') as f:
                f.write(template_content)
                
            # Cargar DOM desde el temporal (relectura para asegurar encoding)
            with open(temp_qpt, 'r', encoding='utf-8') as f:
                final_content = f.read()
                
            doc = QDomDocument()
            doc.setContent(final_content)
            
            project = QgsProject.instance()
            layout_manager = project.layoutManager()
            layout_name = f"Reporte_Canchas_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Limpiar previo si existe (raro por timestamp)
            existing = layout_manager.layoutByName(layout_name)
            if existing: layout_manager.removeLayout(existing)
            
            layout = QgsPrintLayout(project)
            
            context = QgsReadWriteContext()
            if not layout.readLayoutXml(doc.documentElement(), doc, context):
                self.log_signal.emit("❌ Error al cargar la plantilla XML")
                return False
            
            # IMPORTANTE: Asignar nombre DESPUÉS de leer el XML, porque readLayoutXml()
            # sobrescribe el nombre con el que viene en la plantilla.
            layout.setName(layout_name)
            
            # Añadir al manager y verificar éxito
            if not layout_manager.addLayout(layout):
                self.log_signal.emit(f"❌ Error: No se pudo añadir el layout '{layout_name}' al proyecto.")
                return False
            
            # CRITICAL: Re-fetch the layout from the manager to get a stable reference.
            # After addLayout(), the manager takes ownership of the C++ object.
            # The original 'layout' Python wrapper can become stale/deleted.
            layout = layout_manager.layoutByName(layout_name)
            if not layout:
                self.log_signal.emit(f"❌ Error crítico: No se pudo recuperar el layout '{layout_name}' después de añadirlo.")
                return False
            
            # Config Atlas
            tabla_layer = None
            for layer in project.mapLayers().values():
                if layer.name() == "Tabla Base Datos" and layer.type() == QgsMapLayer.VectorLayer:
                    tabla_layer = layer
                    break
            
            if not tabla_layer:
                self.log_signal.emit("❌ Error: No se encontró la capa 'Tabla Base Datos' para el Atlas")
                return False
                
            atlas = layout.atlas()
            if atlas:
                atlas.setCoverageLayer(tabla_layer)
                atlas.setEnabled(True)
                atlas.setSortFeatures(True)
                atlas.setSortExpression('"Protocolo Topografico"')
                atlas.setSortAscending(True)
                self.log_signal.emit("✔️ Atlas configurado con 'Tabla Base Datos'")
                
            iface.openLayoutDesigner(layout)
            self.log_signal.emit("✔️ Compositor abierto exitosamente")
            
            return True
            
        except Exception as e:
            import traceback
            self.log_signal.emit(f"❌ Error al abrir el compositor: {str(e)}")
            self.log_signal.emit(traceback.format_exc())
            return False
