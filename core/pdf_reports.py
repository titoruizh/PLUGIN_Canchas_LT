# -*- coding: utf-8 -*-
"""
Módulo de generación de reportes PDF para Canchas Las Tortolas
Genera protocolos por muro usando Atlas de QGIS
"""

import os
from datetime import datetime
from qgis.core import (
    QgsProject, QgsLayoutManager, QgsReadWriteContext, QgsPrintLayout,
    QgsLayoutExporter, QgsMapLayer, QgsVectorLayer
)
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtCore import QFileInfo

class PDFReportsProcessor:
    """Procesador de reportes PDF con Atlas por muro"""
    
    def __init__(self, proc_root, plugin_dir, progress_callback=None, log_callback=None):
        """
        Inicializar procesador de reportes
        
        Args:
            proc_root: Carpeta raíz de procesamiento (PROC_ROOT)
            plugin_dir: Directorio del plugin (para resources)
            progress_callback: Función callback para actualizar progreso
            log_callback: Función callback para logs
        """
        self.PROC_ROOT = proc_root
        self.plugin_dir = plugin_dir
        self.CARPETA_REPORTES = os.path.join(proc_root, "Protocolos")
        
        # Callbacks
        self.progress_callback = progress_callback or (lambda x, msg="": None)
        self.log_callback = log_callback or (lambda msg: print(msg))
        
        # Rutas de recursos
        self.templates_dir = os.path.join(plugin_dir, "resources", "templates")
        self.logos_dir = os.path.join(plugin_dir, "resources", "logos")
        self.firmas_dir = os.path.join(plugin_dir, "resources", "firmas")
        
        # Plantilla
        self.template_path = os.path.join(self.templates_dir, "Plantilla_Protocolos_LT.qpt")
        
        # Muros a procesar
        self.muros_config = {
            "Principal": {"filtro": "Muro = 'Principal'", "archivo": "Protocolos_PRINCIPAL.pdf"},
            "Oeste": {"filtro": "Muro = 'Oeste'", "archivo": "Protocolos_OESTE.pdf"},
            "Este": {"filtro": "Muro = 'Este'", "archivo": "Protocolos_ESTE.pdf"}
        }

    def verificar_recursos(self):
        """Verificar que existan los recursos necesarios"""
        recursos_faltantes = []
        
        # Verificar plantilla
        if not os.path.exists(self.template_path):
            recursos_faltantes.append(f"Plantilla: {self.template_path}")
        
        # Verificar carpetas
        for carpeta, nombre in [(self.logos_dir, "logos"), (self.firmas_dir, "firmas")]:
            if not os.path.exists(carpeta):
                recursos_faltantes.append(f"Carpeta {nombre}: {carpeta}")
        
        return recursos_faltantes

    def obtener_firma_operador(self, operador):
        """Obtener ruta de firma para operador específico"""
        if not operador:
            operador = "default"
        
        # Limpiar nombre del operador para archivo
        operador_limpio = operador.replace(" ", "_").replace(".", "").lower()
        firma_path = os.path.join(self.firmas_dir, f"{operador_limpio}.png")
        
        # Si no existe, usar default
        if not os.path.exists(firma_path):
            firma_path = os.path.join(self.firmas_dir, "default.png")
        
        return firma_path

    def actualizar_rutas_composicion(self, layout):
        """Actualizar rutas relativas en la composición cargada"""
        try:
            # Buscar todos los elementos de imagen en el layout
            for item in layout.items():
                # Si es un elemento de imagen
                if hasattr(item, 'picturePath'):
                    ruta_actual = item.picturePath()
                    
                    # Si contiene referencias a logo
                    if 'logo' in ruta_actual.lower():
                        # Buscar archivo de logo en carpeta logos
                        for archivo in os.listdir(self.logos_dir):
                            if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                                nueva_ruta = os.path.join(self.logos_dir, archivo)
                                item.setPicturePath(nueva_ruta)
                                self.log_callback(f"✔️ Logo actualizado: {nueva_ruta}")
                                break
                    
                    # Si contiene referencias a firma
                    elif 'firma' in ruta_actual.lower():
                        # Esta se actualizará dinámicamente por operador
                        pass
            
            return True
        except Exception as e:
            self.log_callback(f"❌ Error al actualizar rutas de composición: {e}")
            return False

    def configurar_atlas_por_muro(self, layout, tabla_layer, muro_nombre):
        """Configurar Atlas para filtrar por muro específico"""
        try:
            atlas = layout.atlas()
            if not atlas:
                self.log_callback("❌ Error: La composición no tiene Atlas configurado")
                return False
            
            # Configurar capa de cobertura
            atlas.setCoverageLayer(tabla_layer)
            
            # Verificar que se estableció
            if atlas.coverageLayer() != tabla_layer:
                self.log_callback("❌ Error: No se pudo establecer la capa de cobertura")
                return False
            
            # Configurar filtro por muro usando el nombre directamente
            filtro_expression = f'"Muro" = \'{muro_nombre}\''
            atlas.setFilterFeatures(True)
            atlas.setFilterExpression(filtro_expression)
            
            # Configurar orden
            atlas.setSortFeatures(True)
            atlas.setSortExpression('"Protocolo Topografico"')
            atlas.setSortAscending(True)
            
            # Habilitar Atlas
            atlas.setEnabled(True)
            
            # Verificar configuración final
            self.log_callback(f"✔️ Atlas configurado:")
            self.log_callback(f"  • Capa: {atlas.coverageLayer().name()}")
            self.log_callback(f"  • Filtro: {atlas.filterExpression()}")
            self.log_callback(f"  • Ordenamiento: {atlas.sortExpression()}")
            self.log_callback(f"  • Habilitado: {atlas.enabled()}")
            
            # Test: contar features que cumplen el filtro
            feature_count = 0
            for feature in tabla_layer.getFeatures():
                if feature.attribute('Muro') == muro_nombre:
                    feature_count += 1
            
            self.log_callback(f"🔍 Features encontradas para '{muro_nombre}': {feature_count}")
            
            return True
            
        except Exception as e:
            self.log_callback(f"❌ Error al configurar Atlas: {e}")
            import traceback
            self.log_callback(f"📋 Traceback: {traceback.format_exc()}")
            return False

    def actualizar_firmas_dinamicamente(self, layout, tabla_layer):
        """Actualizar firmas según operador en cada iteración del Atlas"""
        try:
            # Esto se debe hacer durante la exportación
            # por ahora configuramos la firma por defecto
            for item in layout.items():
                if hasattr(item, 'picturePath'):
                    ruta_actual = item.picturePath()
                    if 'firma' in ruta_actual.lower():
                        firma_default = os.path.join(self.firmas_dir, "default.png")
                        if os.path.exists(firma_default):
                            item.setPicturePath(firma_default)
            return True
        except Exception as e:
            self.log_callback(f"❌ Error al actualizar firmas: {e}")
            return False

    def configurar_pagina_a4_vertical(self, layout):
        """Configurar el layout para A4 vertical"""
        try:
            # Obtener configuración de página
            page_collection = layout.pageCollection()
            if page_collection.pageCount() > 0:
                page = page_collection.page(0)
                
                # Configurar A4 vertical (210x297mm)
                page.setPageSize('A4')
                # Si necesitas forzar orientación:
                # page.setPageSize(QgsLayoutSize(210, 297, QgsUnitTypes.LayoutMillimeters))
                
                self.log_callback("✔️ Página configurada a A4 vertical")
                return True
            return False
        except Exception as e:
            self.log_callback(f"❌ Error al configurar página: {e}")
            return False


    def exportar_pdf_por_muro(self, muro_nombre, config_muro, layout, output_path):
        """Exportar PDF para un muro específico usando Atlas"""
        try:
            atlas = layout.atlas()
            if not atlas or not atlas.enabled():
                self.log_callback(f"❌ Atlas no habilitado para {muro_nombre}")
                return False
            
            # Verificar que hay features para procesar
            tabla_layer = atlas.coverageLayer()
            if not tabla_layer:
                self.log_callback(f"❌ No hay capa de cobertura para {muro_nombre}")
                return False
            
            # Contar features que cumplen el filtro
            expression = atlas.filterExpression()
            request = tabla_layer.getFeatures()
            features_filtradas = []
            
            for feature in request:
                # Verificar si la feature cumple el filtro del muro
                muro_feature = feature.attribute('Muro')
                if muro_feature == muro_nombre:
                    features_filtradas.append(feature)
            
            feature_count = len(features_filtradas)
            self.log_callback(f"📊 {muro_nombre}: {feature_count} registros encontrados para Atlas")
            
            if feature_count == 0:
                self.log_callback(f"⚠️ No hay registros para {muro_nombre}")
                return False
            
            # Configurar exportador para Atlas
            exporter = QgsLayoutExporter(layout)
            
            # USAR exportToPdfs (plural) para Atlas - todas las hojas en un PDF
            export_settings = QgsLayoutExporter.PdfExportSettings()
            export_settings.dpi = 300
            export_settings.rasterizeWholeImage = False
            export_settings.forceVectorOutput = True
            export_settings.exportMetadata = True
            
            # Exportar con Atlas (esto genera múltiples páginas en un solo PDF)
            # DESPUÉS:
            result = exporter.exportToPdf(atlas, output_path, export_settings)

            # Verificar si el archivo se creó correctamente (más confiable)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                self.log_callback(f"✔️ PDF con {feature_count} hojas exportado exitosamente: {output_path}")
                file_size_mb = round(os.path.getsize(output_path) / (1024*1024), 2)
                self.log_callback(f"📄 Tamaño del archivo: {file_size_mb} MB")
                return True
            else:
                self.log_callback(f"❌ Error en exportación Atlas PDF para {muro_nombre}")
                self.log_callback(f"🔍 Código retorno QGIS: {result}")
                self.log_callback(f"🔍 Archivo existe: {os.path.exists(output_path)}")
                return False
                
        except Exception as e:
            self.log_callback(f"❌ Error al exportar PDF con Atlas para {muro_nombre}: {e}")
            import traceback
            self.log_callback(f"📋 Traceback: {traceback.format_exc()}")
            return False

    def ejecutar_generacion_reportes_completa(self):
        """Ejecutar todo el proceso de generación de reportes PDF"""
        try:
            self.progress_callback(5, "Iniciando generación de reportes...")
            self.log_callback("📄 Iniciando generación de reportes PDF por muro...")

            # Verificar recursos
            recursos_faltantes = self.verificar_recursos()
            if recursos_faltantes:
                return {
                    'success': False,
                    'message': f'Recursos faltantes: {", ".join(recursos_faltantes)}',
                    'recursos_faltantes': recursos_faltantes
                }

            # Crear carpeta de reportes
            if not os.path.exists(self.CARPETA_REPORTES):
                os.makedirs(self.CARPETA_REPORTES)
                self.log_callback(f"📁 Carpeta creada: {self.CARPETA_REPORTES}")

            # Buscar tabla base de datos
            self.progress_callback(10, "Buscando tabla base de datos...")
            project = QgsProject.instance()
            tabla_layer = None
            for layer in project.mapLayers().values():
                if layer.name() == "Tabla Base Datos" and layer.type() == QgsMapLayer.VectorLayer:
                    tabla_layer = layer
                    break
            
            if not tabla_layer:
                return {
                    'success': False,
                    'message': 'Tabla "Tabla Base Datos" no encontrada. Debe crear la tabla base primero.'
                }

            # Verificar que la tabla tenga registros
            if tabla_layer.featureCount() == 0:
                return {
                    'success': False,
                    'message': 'La tabla "Tabla Base Datos" está vacía.'
                }

            self.log_callback(f"✔️ Tabla encontrada con {tabla_layer.featureCount()} registros")

            # Obtener layout manager
            layout_manager = project.layoutManager()
            
            # Procesar cada muro
            reportes_generados = []
            total_muros = len(self.muros_config)
            
            for idx, (muro_nombre, config) in enumerate(self.muros_config.items(), 1):
                progreso_muro = 20 + int((idx / total_muros) * 70)
                self.progress_callback(progreso_muro, f"Generando reporte para muro {muro_nombre}...")
                
                self.log_callback(f"🔄 Procesando muro: {muro_nombre}")
                
                try:
                    # PASO 1: Cargar plantilla (como abres la composición)
                    self.progress_callback(progreso_muro, f"Cargando plantilla para {muro_nombre}...")
                    
                    # Leer el archivo QPT
                    with open(self.template_path, 'r', encoding='utf-8') as f:
                        template_content = f.read()
                    
                    doc = QDomDocument()
                    doc.setContent(template_content)

                    # PASO 2: Crear layout y agregarlo al proyecto (CLAVE!)
                    layout_name = f"Reporte_{muro_nombre}_{datetime.now().strftime('%H%M%S')}"
                    layout = QgsPrintLayout(project)
                    layout.setName(layout_name)
                    
                    # Cargar desde documento
                    context = QgsReadWriteContext()
                    if not layout.readLayoutXml(doc.documentElement(), doc, context):
                        self.log_callback(f"❌ Error al cargar plantilla para {muro_nombre}")
                        continue
                    
                    # AGREGAR AL PROYECTO (esto es lo que faltaba!)
                    layout_manager.addLayout(layout)
                    self.log_callback(f"✔️ Layout agregado al proyecto: {layout_name}")
                    
                    # PASO 3: Configurar página A4 vertical
                    self.configurar_pagina_a4_vertical(layout)
                    
                    # PASO 4: Actualizar rutas de recursos (logo)
                    self.actualizar_rutas_composicion(layout)
                    
                    # PASO 5: Configurar Atlas usando la función mejorada
                    if not self.configurar_atlas_por_muro(layout, tabla_layer, muro_nombre):
                        self.log_callback(f"❌ No se pudo configurar Atlas para {muro_nombre}")
                        # Remover layout del proyecto
                        layout_manager.removeLayout(layout)
                        continue

                    # PASO 6: Exportar PDF usando la función mejorada
                    output_path = os.path.join(self.CARPETA_REPORTES, config["archivo"])

                    if self.exportar_pdf_por_muro(muro_nombre, config, layout, output_path):
                        reportes_generados.append({
                            'muro': muro_nombre,
                            'archivo': config["archivo"],
                            'path': output_path
                        })
                    else:
                        self.log_callback(f"❌ No se pudo exportar PDF para {muro_nombre}")
                    
                    # PASO 8: Limpiar - remover layout del proyecto
                    layout_manager.removeLayout(layout)
                    self.log_callback(f"🧹 Layout removido del proyecto: {layout_name}")
                    
                except Exception as e:
                    self.log_callback(f"❌ Error procesando {muro_nombre}: {e}")
                    # Asegurar limpieza en caso de error
                    try:
                        if 'layout' in locals():
                            layout_manager.removeLayout(layout)
                    except:
                        pass
                    continue

            # =====================================================
            # RESUMEN DETALLADO AL FINAL
            # =====================================================
            self.progress_callback(100, "¡Reportes generados!")

            # Recopilar estadísticas detalladas
            resumen_muros = []
            total_reportes_exitosos = 0

            for muro_nombre, config in self.muros_config.items():
                # Contar registros por muro
                feature_count = 0
                for feature in tabla_layer.getFeatures():
                    if feature.attribute('Muro') == muro_nombre:
                        feature_count += 1
                
                # Verificar si se generó el reporte
                output_path = os.path.join(self.CARPETA_REPORTES, config["archivo"])
                reporte_generado = os.path.exists(output_path) and os.path.getsize(output_path) > 0
                
                if reporte_generado:
                    total_reportes_exitosos += 1
                    file_size_mb = round(os.path.getsize(output_path) / (1024*1024), 2)
                    resumen_muros.append(f"  • {muro_nombre}: {feature_count} registros ✔️ ({file_size_mb} MB)")
                else:
                    if feature_count == 0:
                        resumen_muros.append(f"  • {muro_nombre}: {feature_count} registros (omitido) ⚠️")
                    else:
                        resumen_muros.append(f"  • {muro_nombre}: {feature_count} registros (error) ❌")

            # Mostrar resumen
            self.log_callback("\n" + "="*50)
            if total_reportes_exitosos > 0:
                self.log_callback(f"✔️ Reportes generados exitosamente ({total_reportes_exitosos}/{len(self.muros_config)} muros):")
            else:
                self.log_callback("❌ No se generó ningún reporte:")

            for linea in resumen_muros:
                self.log_callback(linea)

            self.log_callback(f"📁 Carpeta de salida: {self.CARPETA_REPORTES}")
            self.log_callback("="*50)
            # =====================================================

            if reportes_generados:
                return {
                    'success': True,
                    'message': f'Reportes PDF generados exitosamente: {len(reportes_generados)}/3 muros.',
                    'reportes_generados': reportes_generados,
                    'carpeta_salida': self.CARPETA_REPORTES
                }
            else:
                return {
                    'success': False,
                    'message': 'No se pudo generar ningún reporte PDF.'
                }

        except Exception as e:
            import traceback
            error_msg = f"Error durante la generación de reportes: {str(e)}"
            error_details = traceback.format_exc()
            self.log_callback(f"❌ {error_msg}")
            self.log_callback(f"📋 Detalles del error:\n{error_details}")
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }