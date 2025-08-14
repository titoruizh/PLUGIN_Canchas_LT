# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Screenshot generation module for Canchas Las Tortolas plugin
                                 A QGIS plugin
 Plugin para procesamiento de canchas Las Tortolas - Linkapsis
                             -------------------
        begin                : 2024-08-13
        git sha              : $Format:%H$
        copyright            : (C) 2024 by Linkapsis
        email                : info@linkapsis.com
 ***************************************************************************/
"""

# -*- coding: utf-8 -*-
"""
Módulo de generación de pantallazos para Canchas Las Tortolas
Adaptado del script standalone 3.3_Pantallazos.py - VERSIÓN COMPLETA
"""

import os
from datetime import datetime
from qgis.core import (
    QgsProject, QgsRectangle, QgsFillSymbol, QgsMapSettings, QgsMapRendererSequentialJob,
    QgsMapLayer
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QSize
from qgis.utils import iface

class ScreenshotGenerationProcessor:
    """Procesador de generación de pantallazos completo - TODAS las funciones del script original"""
    
    def __init__(self, proc_root, screenshot_width=800, screenshot_height=500, expansion_factor=1.3, 
                 background_layer="tif", progress_callback=None, log_callback=None):
        """
        Inicializar procesador con parámetros de la GUI
        
        Args:
            proc_root: Carpeta raíz de procesamiento (PROC_ROOT)
            screenshot_width: Ancho de imagen en píxeles (default 800)
            screenshot_height: Alto de imagen en píxeles (default 500)
            expansion_factor: Factor de expansión alrededor del polígono (default 1.3)
            background_layer: Nombre de la capa de fondo (default "tif")
            progress_callback: Función callback para actualizar progreso
            log_callback: Función callback para logs
        """
        self.PROC_ROOT = proc_root
        self.CARPETA_PLANOS = os.path.join(proc_root, "Planos")
        
        # Parámetros configurables desde GUI
        self.PANTALLAZO_ANCHO = screenshot_width
        self.PANTALLAZO_ALTO = screenshot_height
        self.PANTALLAZO_EXPANSION = expansion_factor
        self.NOMBRE_CAPA_FONDO = background_layer
        
        # Callbacks
        self.progress_callback = progress_callback or (lambda x, msg="": None)
        self.log_callback = log_callback or (lambda msg: print(msg))

    # ============================================================
    # FUNCIONES DE PANTALLAZOS DEL SCRIPT ORIGINAL
    # ============================================================

    def generar_pantallazo(self, poligono, capa_fondo, archivo_salida):
        """
        Genera una imagen JPG del polígono y la capa de fondo, centrado y ajustado.
        """
        project = QgsProject.instance()
        layer_tree = project.layerTreeRoot()
        
        # Guardar estado de visibilidad actual
        visibility_state = {child.layer().name(): child.isVisible() 
                           for child in layer_tree.children() 
                           if hasattr(child, 'layer') and child.layer() is not None}
        
        # Validar que el polígono tiene geometrías
        if poligono.featureCount() == 0:
            self.log_callback(f"❌ Error: El polígono '{poligono.name()}' no tiene geometrías.")
            return False
        
        # Obtener geometría del polígono
        feature = next(poligono.getFeatures())
        geom = feature.geometry()
        if not geom.isGeosValid():
            self.log_callback(f"⚠️ Geometría inválida para {poligono.name()}, intentando corregir...")
            geom = geom.makeValid()
            if not geom.isGeosValid():
                self.log_callback(f"❌ Error: No se pudo corregir la geometría para {poligono.name()}")
                return False
        
        # Verificar CRS del polígono
        if not poligono.crs().isValid():
            self.log_callback(f"⚠️ CRS inválido para {poligono.name()}, asignando CRS de la capa de fondo: {capa_fondo.crs().authid()}")
            poligono.setCrs(capa_fondo.crs())
        
        # Hacer visible el grupo de polígonos
        fecha_proc = datetime.now().strftime("%y%m%d")
        group_name = f"Procesamiento_{fecha_proc}"
        group = layer_tree.findGroup(group_name)
        if group:
            poligonos_group = group.findGroup("Poligonos")
            if poligonos_group:
                poligonos_group.setItemVisibilityChecked(True)
        
        # Configurar capas visibles
        capas_visibles = [capa_fondo, poligono]
        
        # Apagar todas las capas excepto las necesarias
        for child in layer_tree.children():
            if hasattr(child, 'layer') and child.layer() is not None:
                is_visible = child.layer() in capas_visibles
                child.setItemVisibilityChecked(is_visible)
        
        # Configurar estilo del polígono
        symbol = QgsFillSymbol.createSimple({
            'outline_color': 'red',
            'outline_width': '1.5',
            'style': 'no'  # Sin relleno, solo contorno
        })
        poligono.renderer().setSymbol(symbol)
        poligono.setOpacity(1.0)
        poligono.triggerRepaint()
        
        # Refrescar canvas
        iface.mapCanvas().refreshAllLayers()
        
        # Calcular extensión del polígono
        extent = poligono.extent()
        if extent.isEmpty() or extent.width() == 0 or extent.height() == 0:
            self.log_callback(f"❌ Error: La extensión del polígono '{poligono.name()}' está vacía o inválida.")
            self._restore_visibility(layer_tree, visibility_state, poligono)
            return False
        
        # Ajustar rectángulo para mantener aspecto de la imagen
        w, h = extent.width(), extent.height()
        aspect_img = self.PANTALLAZO_ANCHO / self.PANTALLAZO_ALTO
        
        if w / h > aspect_img:
            # El polígono es más ancho que el aspecto de la imagen
            h_ajust = w / aspect_img
            rect = QgsRectangle(
                extent.xMinimum(),
                extent.center().y() - h_ajust / 2,
                extent.xMaximum(),
                extent.center().y() + h_ajust / 2
            )
        else:
            # El polígono es más alto que el aspecto de la imagen
            w_ajust = h * aspect_img
            rect = QgsRectangle(
                extent.center().x() - w_ajust / 2,
                extent.yMinimum(),
                extent.center().x() + w_ajust / 2,
                extent.yMaximum()
            )
        
        # Aplicar factor de expansión
        rect.scale(self.PANTALLAZO_EXPANSION)
        
        # Configurar renderizado
        settings = QgsMapSettings()
        settings.setLayers(capas_visibles[::-1])  # Invertir orden para que fondo esté abajo
        settings.setBackgroundColor(QColor(255, 255, 255, 0))  # Fondo blanco transparente
        settings.setOutputSize(QSize(self.PANTALLAZO_ANCHO, self.PANTALLAZO_ALTO))
        settings.setExtent(rect)
        settings.setDestinationCrs(capa_fondo.crs())
        settings.setOutputDpi(96)
        
        # Renderizar imagen
        render = QgsMapRendererSequentialJob(settings)
        render.start()
        render.waitForFinished()
        img = render.renderedImage()
        
        if img.isNull():
            self.log_callback(f"❌ Error: La imagen renderizada para {poligono.name()} está vacía.")
            self._restore_visibility(layer_tree, visibility_state, poligono)
            return False
        
        # Guardar imagen
        success = img.save(archivo_salida, "jpg")
        if success:
            self.log_callback(f"✔️ Pantallazo exportado para {poligono.name()}: {archivo_salida}")
        else:
            self.log_callback(f"❌ Error al guardar imagen para {poligono.name()}: {archivo_salida}")
        
        # Restaurar estado original
        self._restore_visibility(layer_tree, visibility_state, poligono)
        
        return success

    def _restore_visibility(self, layer_tree, visibility_state, poligono):
        """Restaurar el estado de visibilidad original de las capas"""
        # Restaurar visibilidad de todas las capas
        for child in layer_tree.children():
            if hasattr(child, 'layer') and child.layer() is not None:
                original_visibility = visibility_state.get(child.layer().name(), True)
                child.setItemVisibilityChecked(original_visibility)
        
        # Restaurar estilo original del polígono
        poligono.renderer().setSymbol(poligono.renderer().symbol().clone())
        poligono.setOpacity(1.0)
        poligono.triggerRepaint()
        
        # Refrescar canvas
        iface.mapCanvas().refreshAllLayers()

    def generar_todos_pantallazos(self, poligonos_layers, capa_fondo):
        """
        Genera pantallazos para todas las capas de polígonos al final del procesamiento.
        """
        self.log_callback("✔️ Iniciando generación de pantallazos...")
        
        # Asegurar que existe la carpeta de planos
        if not os.path.exists(self.CARPETA_PLANOS):
            os.makedirs(self.CARPETA_PLANOS)
            self.log_callback(f"📁 Carpeta creada: {self.CARPETA_PLANOS}")
        
        total_poligonos = len(poligonos_layers)
        poligonos_procesados = 0
        exitosos = 0
        
        for base in sorted(poligonos_layers):
            poligonos_procesados += 1
            progreso = int((poligonos_procesados / total_poligonos) * 90) + 5  # 5-95%
            self.progress_callback(progreso, f"Generando pantallazo {base}...")
            
            poligono_layer = poligonos_layers[base]
            nombre_imagen = f"P{base}.jpg"  # Agregar prefijo "P" al nombre de la imagen
            archivo_salida = os.path.join(self.CARPETA_PLANOS, nombre_imagen)
            
            success = self.generar_pantallazo(poligono_layer, capa_fondo, archivo_salida)
            if success:
                exitosos += 1
        
        self.log_callback(f"✔️ Generación de pantallazos completada: {exitosos}/{total_poligonos} exitosos.")
        return exitosos, total_poligonos

    # ============================================================
    # MÉTODO PRINCIPAL
    # ============================================================

    def ejecutar_generacion_pantallazos_completa(self):
        """Ejecutar todo el proceso de generación de pantallazos - MÉTODO PRINCIPAL"""
        try:
            self.progress_callback(5, "Iniciando generación de pantallazos...")
            self.log_callback("📸 Iniciando generación de pantallazos...")

            # Asegurar que existe la carpeta de planos
            if not os.path.exists(self.CARPETA_PLANOS):
                os.makedirs(self.CARPETA_PLANOS)
                self.log_callback(f"📁 Carpeta creada: {self.CARPETA_PLANOS}")

            # Verificar que existe el grupo de procesamiento
            self.progress_callback(10, "Verificando grupos de procesamiento...")
            project = QgsProject.instance()
            fecha_proc = datetime.now().strftime("%y%m%d")
            group_name = f"Procesamiento_{fecha_proc}"
            root = project.layerTreeRoot()
            group = root.findGroup(group_name)
            if not group:
                return {
                    'success': False,
                    'message': f'Grupo "{group_name}" no encontrado. Debe ejecutar el procesamiento espacial primero.'
                }

            # Verificar subgrupo de polígonos
            self.progress_callback(15, "Verificando subgrupo de polígonos...")
            poligonos_group = group.findGroup("Poligonos")
            if not poligonos_group:
                return {
                    'success': False,
                    'message': 'Subgrupo "Poligonos" no encontrado.'
                }

            # Obtener capas de polígonos
            self.progress_callback(20, "Obteniendo capas de polígonos...")
            poligonos_layers = {l.name(): l.layer() for l in poligonos_group.findLayers() 
                               if l.layer().type() == QgsMapLayer.VectorLayer}

            self.log_callback("Capas en Poligonos: " + str(list(poligonos_layers.keys())))

            if not poligonos_layers:
                return {
                    'success': False,
                    'message': 'No se encontraron capas de polígonos para procesar.'
                }

            # Buscar capa de fondo
            self.progress_callback(25, f"Buscando capa de fondo '{self.NOMBRE_CAPA_FONDO}'...")
            capa_fondo = None
            for layer in project.mapLayers().values():
                if layer.name().lower() == self.NOMBRE_CAPA_FONDO.lower():
                    capa_fondo = layer
                    break
            
            if not capa_fondo:
                return {
                    'success': False,
                    'message': f'Capa de fondo "{self.NOMBRE_CAPA_FONDO}" no encontrada.'
                }

            self.log_callback(f"✔️ Capa de fondo encontrada: {capa_fondo.name()}")

            # Generar pantallazos
            self.progress_callback(30, "Generando pantallazos...")
            exitosos, total = self.generar_todos_pantallazos(poligonos_layers, capa_fondo)

            self.progress_callback(100, "¡Pantallazos generados!")

            return {
                'success': True,
                'message': f'Pantallazos generados exitosamente: {exitosos}/{total}.',
                'pantallazos_exitosos': exitosos,
                'total_pantallazos': total,
                'carpeta_salida': self.CARPETA_PLANOS
            }

        except Exception as e:
            import traceback
            error_msg = f"Error durante la generación de pantallazos: {str(e)}"
            error_details = traceback.format_exc()
            self.log_callback(f"❌ {error_msg}")
            self.log_callback(f"📋 Detalles del error:\n{error_details}")
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }