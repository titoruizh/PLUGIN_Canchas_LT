# -*- coding: utf-8 -*-
"""
Generador de pantallazos heatmap
Basado directamente en PANTALLAZOS_heatmap_final.py
"""
import os
import numpy as np
from datetime import datetime
from qgis.core import (
    QgsProject, QgsRectangle, QgsMapSettings, QgsMapRendererSequentialJob,
    QgsFeatureRequest, QgsVectorLayer, QgsFillSymbol, QgsSingleSymbolRenderer,
    QgsPointXY, QgsGeometry, QgsFeature, QgsField, QgsFields
)
from qgis.PyQt.QtGui import QColor, QImage, QPainter, QLinearGradient, QFont, QBrush
from qgis.PyQt.QtCore import QSize, QVariant
from scipy.spatial.distance import cdist
from scipy.ndimage import gaussian_filter

class HeatmapScreenshotGenerator:
    """
    Generador de pantallazos heatmap que replica exactamente el comportamiento
    del script PANTALLAZOS_heatmap_final.py
    """
    
    def __init__(self, proc_root="", progress_callback=None, log_callback=None):
        self.proc_root = proc_root
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        
        # Configuración de pantallazos
        self.screenshot_width = 1200
        self.screenshot_height = 800
        self.expansion_factor = 1.3  # Factor para expandir un poco el área de vista
        
        # Configuración del heatmap
        self.heatmap_resolution = 100  # Resolución de la grilla del heatmap
        self.heatmap_sigma = 2  # Suavizado gaussiano
        self.heatmap_alpha = 0.7  # Transparencia del heatmap (0-1)
        
        # Código de muros (para construir el código de búsqueda)
        self.muro_codes = {
            "Principal": "MP",
            "principal": "MP",
            "Este": "ME",
            "este": "ME",
            "Oeste": "MO",
            "oeste": "MO"
        }
    
    def log_message(self, message):
        """Registrar mensaje en el log"""
        if self.log_callback:
            self.log_callback(message)
    
    def update_progress(self, value, message=""):
        """Actualizar barra de progreso"""
        if self.progress_callback:
            self.progress_callback(value, message)
    
    def generar_pantallazos_heatmap(self):
        """
        Genera pantallazos heatmap para cada registro de la Tabla Base Datos
        usando exactamente la misma lógica que PANTALLAZOS_heatmap_final.py
        """
        try:
            # Crear carpetas
            if not self.proc_root:
                self.log_message("❌ Error: No se ha configurado la carpeta de procesamiento")
                return {'success': False, 'message': 'No hay carpeta de procesamiento configurada'}
            
            carpeta_aux = os.path.join(self.proc_root, "Aux Reporte")
            carpeta_pantallazos = os.path.join(carpeta_aux, "Pantallazos Heatmap")
            os.makedirs(carpeta_aux, exist_ok=True)
            os.makedirs(carpeta_pantallazos, exist_ok=True)
            self.log_message(f"📁 Carpeta de pantallazos heatmap creada: {carpeta_pantallazos}")
            
            # Obtener capas necesarias
            tabla_base_layer = None
            datos_historicos_layer = None
            poligonos_layer = None
            tif_layer = None
            
            for layer in QgsProject.instance().mapLayers().values():
                if layer.name() == "Tabla Base Datos":
                    tabla_base_layer = layer
                elif layer.name() == "DATOS HISTORICOS":
                    datos_historicos_layer = layer
                elif layer.name() == "Poligonos_Sectores":
                    poligonos_layer = layer
                elif layer.name() == "tif":
                    tif_layer = layer
            
            if not tabla_base_layer:
                self.log_message("❌ No se encontró 'Tabla Base Datos'")
                return {'success': False, 'message': 'No se encontró Tabla Base Datos'}
            
            if not datos_historicos_layer:
                self.log_message("❌ No se encontró 'DATOS HISTORICOS'")  
                return {'success': False, 'message': 'No se encontró DATOS HISTORICOS'}
                
            if not poligonos_layer:
                self.log_message("❌ No se encontró 'Poligonos_Sectores'")
                return {'success': False, 'message': 'No se encontró Poligonos_Sectores'}
                
            if not tif_layer:
                self.log_message("❌ No se encontró 'tif'")
                return {'success': False, 'message': 'No se encontró capa tif'}
            
            # Debug: ver campos disponibles
            self.log_message(f"🔍 Campos en Tabla Base Datos: {[f.name() for f in tabla_base_layer.fields()]}")
            
            # Verificar si existe la columna 'PH', si no existe, crearla
            field_names = [field.name() for field in tabla_base_layer.fields()]
            if 'PH' not in field_names:
                self.log_message("🔧 Creando columna 'PH' en Tabla Base Datos...")
                from qgis.core import QgsField
                from qgis.PyQt.QtCore import QVariant
                
                # Crear el campo PH
                new_field = QgsField('PH', QVariant.String, len=255)
                
                # Agregar el campo a la capa
                tabla_base_layer.dataProvider().addAttributes([new_field])
                tabla_base_layer.updateFields()
                self.log_message("✅ Columna 'PH' creada exitosamente")
            else:
                self.log_message("ℹ️ La columna 'PH' ya existe en la tabla")
            
            total_registros = tabla_base_layer.featureCount()
            self.log_message(f"🔍 Procesando {total_registros} registros para generar pantallazos heatmap")
            
            pantallazos_generados = 0
            pantallazos_fallidos = 0
            
            # Procesar cada feature en tabla base
            for i, feature in enumerate(tabla_base_layer.getFeatures()):
                progress = int((i + 1) / total_registros * 100)
                self.update_progress(progress, f"Generando pantallazo heatmap {i+1}/{total_registros}")
                self.log_message(f"📋 Generando pantallazo heatmap {i+1}/{total_registros}")
                
                try:
                    # Obtener datos del feature - acceso directo como en el script original
                    muro = feature["Muro"]  
                    fecha_str = feature["Fecha"]
                    
                    # Buscar campo sector con diferentes nombres posibles
                    sector = None
                    for field_name in ["Sector", "sector", "SECTOR"]:
                        try:
                            sector = feature[field_name]
                            if sector:
                                break
                        except:
                            continue
                    
                    # Buscar campo relleno con diferentes nombres posibles
                    relleno = None
                    for field_name in ["Relleno", "relleno", "RELLENO", "Tipo_Relleno", "TipoRelleno"]:
                        try:
                            relleno = feature[field_name]
                            if relleno:
                                break
                        except:
                            continue
                    
                    if not muro or not fecha_str:
                        self.log_message(f"⚠️ Registro {i+1}: faltan datos necesarios (Muro o Fecha)")
                        pantallazos_fallidos += 1
                        continue
                    
                    if not sector:
                        self.log_message(f"⚠️ Registro {i+1}: no se encontró campo Sector")
                        sector = "SIN_SECTOR"
                    
                    if not relleno:
                        self.log_message(f"⚠️ Registro {i+1}: no se encontró campo Relleno")
                        relleno = "SIN_RELLENO"
                    
                    # Generar pantallazo usando la lógica exacta del script original
                    nombre_archivo_generado = self.generar_pantallazo_heatmap_individual(
                        datos_historicos_layer, 
                        poligonos_layer,
                        tif_layer,
                        muro, 
                        sector,
                        fecha_str, 
                        relleno,
                        carpeta_pantallazos,
                        i + 1
                    )
                    
                    if nombre_archivo_generado:
                        # Actualizar el campo PH con el nombre del archivo generado
                        self.actualizar_campo_ph(tabla_base_layer, feature, nombre_archivo_generado)
                        pantallazos_generados += 1
                    else:
                        pantallazos_fallidos += 1
                        
                except Exception as e:
                    self.log_message(f"❌ Error en registro {i+1}: {str(e)}")
                    pantallazos_fallidos += 1
            
            self.log_message(f"✅ Generación de pantallazos heatmap completada")
            self.log_message(f"📷 {pantallazos_generados} pantallazos generados correctamente")
            if pantallazos_fallidos > 0:
                self.log_message(f"⚠️ {pantallazos_fallidos} pantallazos no pudieron generarse")
            
            return {
                'success': True,
                'message': 'Generación de pantallazos heatmap completada',
                'graficos_generados': pantallazos_generados,
                'graficos_fallidos': pantallazos_fallidos,
                'total_registros': total_registros,
                'carpeta_salida': carpeta_pantallazos
            }
            
        except Exception as e:
            import traceback
            self.log_message(f"❌ Error general: {str(e)}")
            self.log_message(f"📋 Detalles: {traceback.format_exc()}")
            return {
                'success': False,
                'message': f'Error en la generación de pantallazos heatmap: {str(e)}',
                'details': traceback.format_exc()
            }
    
    def actualizar_campo_ph(self, tabla_base_layer, feature, nombre_archivo):
        """
        Actualiza el campo PH del feature con el nombre del archivo generado
        """
        try:
            # Iniciar edición
            tabla_base_layer.startEditing()
            
            # Actualizar el campo PH
            field_index = tabla_base_layer.fields().indexFromName('PH')
            if field_index != -1:
                tabla_base_layer.changeAttributeValue(feature.id(), field_index, nombre_archivo)
                
            # Guardar cambios
            tabla_base_layer.commitChanges()
            self.log_message(f"📝 Campo PH actualizado para feature {feature.id()}: {nombre_archivo}")
            
        except Exception as e:
            self.log_message(f"⚠️ Error al actualizar campo PH: {str(e)}")
            tabla_base_layer.rollBack()
    
    def calculate_centroid(self, p1_este, p1_norte, p2_este, p2_norte, p3_este, p3_norte, p4_este, p4_norte):
        """Calcula el centroide de los 4 vértices (exactamente como en el script original)"""
        try:
            centroid_x = (p1_este + p2_este + p3_este + p4_este) / 4.0
            centroid_y = (p1_norte + p2_norte + p3_norte + p4_norte) / 4.0
            return centroid_x, centroid_y
        except:
            return None, None
    
    def create_heatmap_data(self, merge_layer, muro_filter, sector_filter, bbox):
        """Extrae datos históricos y calcula centroides para el heatmap (exactamente como en el script original)"""
        centroids = []
        
        # Primero, mostrar todas las columnas disponibles
        field_names = [field.name() for field in merge_layer.fields()]
        self.log_message(f"🔍 Columnas disponibles en la tabla histórica: {field_names}")
        
        # Construir filtro para la tabla
        sector_value = f"SECTOR {sector_filter}"
        filter_expression = f"\"Muro\" = '{muro_filter}' AND \"Sector\" = '{sector_value}'"
        self.log_message(f"🔍 Filtro para datos históricos: {filter_expression}")
        
        request = QgsFeatureRequest().setFilterExpression(filter_expression)
        features = list(merge_layer.getFeatures(request))
        
        self.log_message(f"📊 Encontrados {len(features)} registros históricos")
        self.log_message(f"📍 Bbox del área: X({bbox.xMinimum():.2f} - {bbox.xMaximum():.2f}), Y({bbox.yMinimum():.2f} - {bbox.yMaximum():.2f})")
        
        # Buscar columnas que contengan coordenadas (por si tienen nombres ligeramente diferentes)
        coord_columns = {}
        for field_name in field_names:
            field_upper = field_name.upper()
            if 'P1' in field_upper and 'ESTE' in field_upper:
                coord_columns['P1_ESTE'] = field_name
            elif 'P1' in field_upper and 'NORTE' in field_upper:
                coord_columns['P1_NORTE'] = field_name
            elif 'P2' in field_upper and 'ESTE' in field_upper:
                coord_columns['P2_ESTE'] = field_name
            elif 'P2' in field_upper and 'NORTE' in field_upper:
                coord_columns['P2_NORTE'] = field_name
            elif 'P3' in field_upper and 'ESTE' in field_upper:
                coord_columns['P3_ESTE'] = field_name
            elif 'P3' in field_upper and 'NORTE' in field_upper:
                coord_columns['P3_NORTE'] = field_name
            elif 'P4' in field_upper and 'ESTE' in field_upper:
                coord_columns['P4_ESTE'] = field_name
            elif 'P4' in field_upper and 'NORTE' in field_upper:
                coord_columns['P4_NORTE'] = field_name
        
        self.log_message(f"🗺️ Columnas de coordenadas encontradas: {coord_columns}")
        
        for i, feature in enumerate(features):
            try:
                # Intentar obtener las coordenadas usando los nombres encontrados
                coords = {}
                all_coords_found = True
                
                for coord_key, field_name in coord_columns.items():
                    value = feature[field_name] if field_name else None
                    coords[coord_key] = value
                    if value is None or value == '':
                        all_coords_found = False
                
                if not all_coords_found:
                    continue
                
                # Intentar convertir a números si son strings
                try:
                    p1_este = float(coords.get('P1_ESTE', 0))
                    p1_norte = float(coords.get('P1_NORTE', 0))
                    p2_este = float(coords.get('P2_ESTE', 0))
                    p2_norte = float(coords.get('P2_NORTE', 0))
                    p3_este = float(coords.get('P3_ESTE', 0))
                    p3_norte = float(coords.get('P3_NORTE', 0))
                    p4_este = float(coords.get('P4_ESTE', 0))
                    p4_norte = float(coords.get('P4_NORTE', 0))
                except (ValueError, TypeError):
                    continue
                
                # Calcular centroide
                centroid_x, centroid_y = self.calculate_centroid(
                    p1_este, p1_norte, p2_este, p2_norte,
                    p3_este, p3_norte, p4_este, p4_norte
                )
                
                if centroid_x and centroid_y:
                    # Verificar que el centroide esté dentro del área de interés (con margen más amplio)
                    margin_factor = 2.0  # Ampliar el área de búsqueda
                    x_margin = (bbox.xMaximum() - bbox.xMinimum()) * margin_factor
                    y_margin = (bbox.yMaximum() - bbox.yMinimum()) * margin_factor
                    
                    expanded_bbox = QgsRectangle(
                        bbox.xMinimum() - x_margin,
                        bbox.yMinimum() - y_margin,
                        bbox.xMaximum() + x_margin,
                        bbox.yMaximum() + y_margin
                    )
                    
                    if (expanded_bbox.xMinimum() <= centroid_x <= expanded_bbox.xMaximum() and 
                        expanded_bbox.yMinimum() <= centroid_y <= expanded_bbox.yMaximum()):
                        centroids.append((centroid_x, centroid_y))
                        
            except Exception as e:
                continue
        
        self.log_message(f"✅ Calculados {len(centroids)} centroides válidos")
        return centroids
    
    def create_heatmap_image(self, centroids, bbox, width, height):
        """Crea la imagen del heatmap a partir de los centroides (exactamente como en el script original)"""
        if not centroids:
            self.log_message("⚠️ No hay datos para el heatmap")
            return None
        
        self.log_message(f"🎨 Creando heatmap con {len(centroids)} centroides")
        
        # Crear imagen del heatmap
        heatmap_image = QImage(width, height, QImage.Format_ARGB32)
        heatmap_image.fill(QColor(0, 0, 0, 0))  # Transparente
        
        # Convertir coordenadas del mundo real a coordenadas de imagen
        x_min, x_max = bbox.xMinimum(), bbox.xMaximum()
        y_min, y_max = bbox.yMinimum(), bbox.yMaximum()
        
        # Calcular el radio de influencia en metros (adaptativo según el tamaño del área)
        area_width = x_max - x_min
        area_height = y_max - y_min
        influence_radius_meters = min(area_width, area_height) * 0.05  # 5% del área más pequeña
        
        self.log_message(f"📐 Radio de influencia: {influence_radius_meters:.2f} metros")
        
        # Crear grilla de densidad
        density_grid = np.zeros((height, width))
        
        # Para cada centroide, añadir influencia a la grilla
        for centroid_x, centroid_y in centroids:
            # Convertir coordenadas del mundo real a píxeles
            pixel_x = int((centroid_x - x_min) / (x_max - x_min) * width)
            pixel_y = int((y_max - centroid_y) / (y_max - y_min) * height)  # Invertir Y
            
            # Calcular radio de influencia en píxeles
            radius_x_pixels = int(influence_radius_meters / area_width * width)
            radius_y_pixels = int(influence_radius_meters / area_height * height)
            radius_pixels = max(min(radius_x_pixels, radius_y_pixels), 15)  # Mínimo 15 píxeles
            
            # Añadir influencia gaussiana alrededor del punto
            for dy in range(-radius_pixels, radius_pixels + 1):
                for dx in range(-radius_pixels, radius_pixels + 1):
                    px = pixel_x + dx
                    py = pixel_y + dy
                    
                    # Verificar que esté dentro de los límites
                    if 0 <= px < width and 0 <= py < height:
                        # Calcular distancia desde el centro
                        distance = np.sqrt(dx*dx + dy*dy)
                        if distance <= radius_pixels:
                            # Función gaussiana para la influencia
                            influence = np.exp(-(distance**2) / (2 * (radius_pixels/3)**2))
                            density_grid[py, px] += influence
        
        # Normalizar la grilla de densidad
        if density_grid.max() > 0:
            density_grid = density_grid / density_grid.max()
        
        # Aplicar un poco de suavizado
        density_grid = gaussian_filter(density_grid, sigma=0.8)
        
        # Renormalizar después del suavizado
        if density_grid.max() > 0:
            density_grid = density_grid / density_grid.max()
        
        self.log_message(f"📊 Rango de densidad: {density_grid.min():.3f} - {density_grid.max():.3f}")
        
        # Convertir la grilla de densidad a imagen con colores
        for y in range(height):
            for x in range(width):
                intensity = density_grid[y, x]
                
                # Solo mostrar píxeles con intensidad significativa
                if intensity > 0.05:  # Umbral del 5%
                    # Crear gradiente de colores más suave
                    if intensity < 0.2:
                        # Azul claro
                        r = 0
                        g = int(100 + 155 * (intensity / 0.2))
                        b = 255
                    elif intensity < 0.4:
                        # Azul a verde
                        t = (intensity - 0.2) / 0.2
                        r = 0
                        g = 255
                        b = int(255 * (1 - t))
                    elif intensity < 0.6:
                        # Verde a amarillo
                        t = (intensity - 0.4) / 0.2
                        r = int(255 * t)
                        g = 255
                        b = 0
                    elif intensity < 0.8:
                        # Amarillo a naranja
                        t = (intensity - 0.6) / 0.2
                        r = 255
                        g = int(255 * (1 - t * 0.5))
                        b = 0
                    else:
                        # Naranja a rojo
                        t = (intensity - 0.8) / 0.2
                        r = 255
                        g = int(127 * (1 - t))
                        b = 0
                    
                    # Calcular alpha basado en la intensidad
                    alpha = int(255 * self.heatmap_alpha * (0.3 + 0.7 * intensity))  # Mínimo 30% de alpha
                    color = QColor(r, g, b, alpha)
                    heatmap_image.setPixelColor(x, y, color)
        
        self.log_message("✅ Heatmap generado exitosamente")
        return heatmap_image
    
    def generar_pantallazo_heatmap_individual(self, datos_historicos_layer, poligonos_layer, tif_layer, muro, sector, fecha_str, relleno, carpeta_salida, num_registro):
        """
        Replica exactamente la lógica de PANTALLAZOS_heatmap_final.py
        
        Returns:
            str: Nombre del archivo generado si fue exitoso, None si hubo error
        """
        try:
            # Extraer número del sector (ej: "SECTOR 3" -> "3")
            sector_num = sector.replace("SECTOR", "").strip()
            
            # Determinar código de búsqueda para el polígono
            muro_code = self.muro_codes.get(muro)
            if not muro_code:
                self.log_message(f"❌ Error: Muro no reconocido: {muro}")
                return None
            
            search_code = f"{muro_code}_S{sector_num}"
            self.log_message(f"🔍 Buscando polígono con NAME = '{search_code}'")
            
            # Encontrar el polígono específico
            request = QgsFeatureRequest().setFilterExpression(f"\"NAME\" = '{search_code}'")
            features = list(poligonos_layer.getFeatures(request))
            
            if not features:
                self.log_message(f"❌ Error: No se encontró polígono con NAME = '{search_code}'")
                return None
            
            target_feature = features[0]
            self.log_message(f"✅ Polígono encontrado: {search_code}")
            
            # Obtener la extensión del polígono
            geometry = target_feature.geometry()
            bbox = geometry.boundingBox()
            
            # Ajustar proporciones para mantener el aspect ratio de la imagen
            aspect_ratio = self.screenshot_width / self.screenshot_height
            bbox_aspect_ratio = bbox.width() / bbox.height()
            
            if bbox_aspect_ratio > aspect_ratio:
                new_height = bbox.width() / aspect_ratio
                center_y = bbox.center().y()
                bbox = QgsRectangle(
                    bbox.xMinimum(),
                    center_y - new_height / 2,
                    bbox.xMaximum(),
                    center_y + new_height / 2
                )
            else:
                new_width = bbox.height() * aspect_ratio
                center_x = bbox.center().x()
                bbox = QgsRectangle(
                    center_x - new_width / 2,
                    bbox.yMinimum(),
                    center_x + new_width / 2,
                    bbox.yMaximum()
                )
            
            # Expandir la extensión para tener un margen alrededor
            bbox.scale(self.expansion_factor)
            
            # Crear datos del heatmap
            centroids = self.create_heatmap_data(datos_historicos_layer, muro, sector_num, bbox)
            heatmap_image = self.create_heatmap_image(centroids, bbox, self.screenshot_width, self.screenshot_height)
            
            # Crear una capa temporal solo con el polígono seleccionado
            memory_layer = QgsVectorLayer("Polygon", "temp_polygon", "memory")
            memory_layer.setCrs(poligonos_layer.crs())
            memory_provider = memory_layer.dataProvider()
            
            # Configurar los campos
            memory_provider.addAttributes(poligonos_layer.fields())
            memory_layer.updateFields()
            
            # Añadir el feature seleccionado
            memory_provider.addFeature(target_feature)
            
            # Renderizar primero la imagen de fondo completa
            base_settings = QgsMapSettings()
            base_settings.setLayers([tif_layer])
            base_settings.setBackgroundColor(QColor(255, 255, 255))
            base_settings.setOutputSize(QSize(self.screenshot_width, self.screenshot_height))
            base_settings.setExtent(bbox)
            base_settings.setDestinationCrs(tif_layer.crs())
            base_settings.setOutputDpi(96)
            
            base_render = QgsMapRendererSequentialJob(base_settings)
            base_render.start()
            base_render.waitForFinished()
            base_image = base_render.renderedImage()
            
            # Crear la máscara negra semitransparente
            mask = QImage(self.screenshot_width, self.screenshot_height, QImage.Format_ARGB32)
            mask.fill(QColor(0, 0, 0, 180))  # Negro semitransparente
            
            # Renderizar solo el polígono para usarlo como máscara
            mask_settings = QgsMapSettings()
            mask_settings.setLayers([memory_layer])
            mask_settings.setBackgroundColor(QColor(0, 0, 0, 0))  # Transparente
            mask_settings.setOutputSize(QSize(self.screenshot_width, self.screenshot_height))
            mask_settings.setExtent(bbox)
            mask_settings.setDestinationCrs(tif_layer.crs())
            mask_settings.setOutputDpi(96)
            
            # Cambiar el estilo del polígono para la máscara
            fill_symbol = QgsFillSymbol.createSimple({
                'color': '255,255,255,255',  # Relleno blanco opaco
                'outline_color': '255,255,255,0',  # Sin borde
                'outline_width': '0'
            })
            
            memory_layer.renderer().setSymbol(fill_symbol)
            
            mask_render = QgsMapRendererSequentialJob(mask_settings)
            mask_render.start()
            mask_render.waitForFinished()
            poly_mask = mask_render.renderedImage()
            
            # Aplicar la máscara
            mask_painter = QPainter(mask)
            mask_painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
            mask_painter.drawImage(0, 0, poly_mask)
            mask_painter.end()
            
            # Combinar la imagen base con la máscara
            result_image = QImage(base_image)
            painter = QPainter(result_image)
            painter.drawImage(0, 0, mask)
            
            # Añadir el heatmap si existe
            if heatmap_image:
                # Crear máscara para el heatmap (solo dentro del polígono)
                heatmap_masked = QImage(heatmap_image)
                heatmap_painter = QPainter(heatmap_masked)
                heatmap_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
                heatmap_painter.drawImage(0, 0, poly_mask)
                heatmap_painter.end()
                
                # Dibujar el heatmap enmascarado
                painter.drawImage(0, 0, heatmap_masked)
                self.log_message(f"✅ Heatmap añadido con {len(centroids)} puntos de datos")
            
            # Renderizar el borde del polígono encima
            border_symbol = QgsFillSymbol.createSimple({
                'color': '255,255,255,0',  # Relleno transparente
                'outline_color': '255,103,35,255',  # Borde naranjo
                'outline_width': '2'  # Ancho del borde
            })
            
            memory_layer.renderer().setSymbol(border_symbol)
            
            border_settings = QgsMapSettings()
            border_settings.setLayers([memory_layer])
            border_settings.setBackgroundColor(QColor(0, 0, 0, 0))
            border_settings.setOutputSize(QSize(self.screenshot_width, self.screenshot_height))
            border_settings.setExtent(bbox)
            border_settings.setDestinationCrs(tif_layer.crs())
            border_settings.setOutputDpi(96)
            
            border_render = QgsMapRendererSequentialJob(border_settings)
            border_render.start()
            border_render.waitForFinished()
            border_image = border_render.renderedImage()
            
            # Dibujar el borde encima
            painter.drawImage(0, 0, border_image)
            
            # Añadir leyenda del heatmap
            if centroids:
                # Título principal con fondo
                painter.setBrush(QColor(0, 0, 0, 180))  # Negro semitransparente
                painter.setPen(QColor(255, 255, 255, 100))  # Borde blanco sutil
                painter.drawRoundedRect(10, 20, 300, 50, 10, 10)  # Fondo redondeado para título
                
                # Configurar fuente más grande para el título
                font = QFont()
                font.setPointSize(36)  # 3 veces más grande
                font.setBold(True)
                painter.setFont(font)
                
                # Texto principal de la leyenda
                painter.setPen(QColor(255, 255, 255))  # Blanco brillante
                painter.drawText(20, 60, f"Registros Anuales: {len(centroids)}")
                
                # Crear barra de colores vertical a la derecha
                barra_x = self.screenshot_width - 70  # Posición X (70px desde el borde derecho)
                barra_y = 80  # Posición Y desde arriba
                barra_ancho = 25  # Ancho de la barra
                barra_alto = 180  # Alto de la barra
                
                # Crear gradiente vertical (de azul a rojo)
                gradient = QLinearGradient(0, barra_y, 0, barra_y + barra_alto)
                gradient.setColorAt(0.0, QColor(100, 150, 255))  # Azul (baja concentración) - arriba
                gradient.setColorAt(0.5, QColor(255, 255, 100))  # Amarillo (media) - centro
                gradient.setColorAt(1.0, QColor(255, 100, 100))  # Rojo (alta concentración) - abajo
                
                # Dibujar la barra de colores
                painter.setBrush(QBrush(gradient))
                painter.setPen(QColor(0, 0, 0, 200))  # Borde negro sutil
                painter.drawRect(barra_x, barra_y, barra_ancho, barra_alto)
                
                # Etiquetas de los extremos con fuente pequeña
                font_pequeña = QFont()
                font_pequeña.setPointSize(12)  # Fuente pequeña
                font_pequeña.setBold(True)
                painter.setFont(font_pequeña)
                
                # Fondo para las etiquetas
                painter.setBrush(QColor(0, 0, 0, 150))
                painter.setPen(QColor(255, 255, 255, 50))
                
                # Etiqueta superior (baja concentración)
                painter.drawRoundedRect(barra_x - 65, barra_y - 5, 55, 20, 5, 5)
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(barra_x - 60, barra_y + 10, "Baja")
                
                # Etiqueta inferior (alta concentración)
                painter.setBrush(QColor(0, 0, 0, 150))
                painter.setPen(QColor(255, 255, 255, 50))
                painter.drawRoundedRect(barra_x - 60, barra_y + barra_alto - 10, 50, 20, 5, 5)
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(barra_x - 55, barra_y + barra_alto + 5, "Alta")
            
            painter.end()
            
            # Generar nombre de archivo con nomenclatura: PH1{numero}{fecha}_{muro}_{sector}_{relleno}.jpg
            def procesar_fecha(fecha_str):
                """Convierte 2025-08-20 a 250820"""
                try:
                    fecha_dt = datetime.strptime(str(fecha_str), "%Y-%m-%d")
                    return fecha_dt.strftime("%y%m%d")  # 25 08 20 -> 250820
                except:
                    return str(fecha_str).replace("-", "")
            
            def procesar_muro(muro_str):
                """Convierte nombres de muro a abreviaciones"""
                muro_lower = str(muro_str).lower()
                if "principal" in muro_lower:
                    return "MP"
                elif "oeste" in muro_lower:
                    return "MO"
                elif "este" in muro_lower:
                    return "ME"
                else:
                    # Si no coincide con ninguno, usar las primeras 2 letras en mayúscula
                    return str(muro_str)[:2].upper()
            
            def procesar_sector(sector_str):
                """Convierte 'SECTOR 1' a 'S1'"""
                sector_clean = str(sector_str).upper().replace("SECTOR", "").strip()
                if sector_clean.isdigit():
                    return f"S{sector_clean}"
                else:
                    # Si no es un número, intentar extraer el número
                    import re
                    match = re.search(r'\d+', str(sector_str))
                    if match:
                        return f"S{match.group()}"
                    else:
                        return f"S{sector_clean}"
            
            def procesar_relleno(relleno_str):
                """Elimina espacios del relleno: 'Arena fina' -> 'Arenafina'"""
                return str(relleno_str).replace(" ", "").replace("-", "").replace("_", "")
            
            fecha_procesada = procesar_fecha(fecha_str)
            muro_procesado = procesar_muro(muro)
            sector_procesado = procesar_sector(sector)
            relleno_procesado = procesar_relleno(relleno)
            
            # Nomenclatura final: PH{fecha}_{muro}_{sector}_{relleno}.jpg
            # Ejemplo: PH250820_MP_S1_Arenafina.jpg
            nombre_archivo = f"PH{fecha_procesada}_{muro_procesado}_{sector_procesado}_{relleno_procesado}.jpg"
            ruta_completa = os.path.join(carpeta_salida, nombre_archivo)
            
            # Guardar la imagen resultante
            success = result_image.save(ruta_completa, "JPG", 95)
            
            if success:
                self.log_message(f"✅ Pantallazo heatmap generado: {nombre_archivo}")
                return nombre_archivo  # Retornar el nombre del archivo
            else:
                self.log_message(f"❌ Error al guardar pantallazo: {ruta_completa}")
                return None
            
        except Exception as e:
            self.log_message(f"❌ Error al generar pantallazo heatmap para registro {num_registro}: {str(e)}")
            import traceback
            self.log_message(traceback.format_exc())
            return None