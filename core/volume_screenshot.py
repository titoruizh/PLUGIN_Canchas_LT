# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Volume calculation and screenshot generation module for Canchas Las Tortolas plugin
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
Módulo unificado de cálculo de volúmenes y generación de pantallazos para Canchas Las Tortolas
Combina funcionalidades de volume_calculation.py y screenshot_generation.py con diferencias DEM
"""

import os
import tempfile
from datetime import datetime
import numpy as np
from osgeo import gdal, osr
from qgis.core import (
    QgsProject, QgsMapLayer, QgsCoordinateReferenceSystem, QgsRasterLayer, 
    QgsExpressionContextUtils, QgsRectangle, QgsMapSettings, QgsMapRendererSequentialJob,
    QgsRasterShader, QgsColorRampShader, QgsSingleBandPseudoColorRenderer,
    QgsRasterBandStats
)
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QSize
from qgis.utils import iface
import processing

class VolumeScreenshotProcessor:
    """Procesador unificado de cálculo de volúmenes y generación de pantallazos con diferencias DEM"""
    
    def __init__(self, proc_root, num_random_points=20, min_espesor=0.01, resample_algorithm='bilinear',
                 screenshot_width=800, screenshot_height=500, expansion_factor=1.3, 
                 background_layer="tif", percentile_high=95, percentile_low=1, 
                 max_expected_thickness=None, enable_outlier_filtering=True,
                 progress_callback=None, log_callback=None):
        """
        Inicializar procesador unificado
        
        Args:
            proc_root: Carpeta raíz de procesamiento (PROC_ROOT)
            num_random_points: Número de puntos aleatorios para análisis (default 20)
            min_espesor: Espesor mínimo permitido (default 0.01)
            resample_algorithm: Algoritmo de remuestreo (default 'bilinear' - recomendado para análisis volumétrico)
            screenshot_width: Ancho de imagen en píxeles (default 800)
            screenshot_height: Alto de imagen en píxeles (default 500)
            expansion_factor: Factor de expansión alrededor del área (default 1.3)
            background_layer: Nombre de la capa de fondo (default "tif")
            percentile_high: Percentil alto para limitar espesor máximo (default 99)
            percentile_low: Percentil bajo para ajustar espesor mínimo (default 1)
            max_expected_thickness: Límite absoluto de espesor en metros (default None = sin límite)
            enable_outlier_filtering: Activar filtrado de outliers por percentiles (default True)
            progress_callback: Función callback para actualizar progreso
            log_callback: Función callback para logs
        """
        self.PROC_ROOT = proc_root
        self.CARPETA_PLANOS = os.path.join(proc_root, "Planos")
        self.CARPETA_PERFILES = os.path.join(proc_root, "Perfiles")  # Nueva carpeta para perfiles topográficos
        
        # Parámetros de cálculo volumétrico
        self.NUM_RANDOM_POINTS = num_random_points
        self.MIN_ESPESOR = min_espesor
        self.resample_algorithm = resample_algorithm
        
        # Parámetros de filtrado de outliers
        self.PERCENTILE_HIGH = percentile_high
        self.PERCENTILE_LOW = percentile_low
        self.MAX_EXPECTED_THICKNESS = max_expected_thickness
        self.ENABLE_OUTLIER_FILTERING = enable_outlier_filtering
        
        # Parámetros de pantallazos
        self.PANTALLAZO_ANCHO = screenshot_width
        self.PANTALLAZO_ALTO = screenshot_height
        self.PANTALLAZO_EXPANSION = expansion_factor
        self.NOMBRE_CAPA_FONDO = background_layer
        
        # Callbacks
        self.progress_callback = progress_callback or (lambda x, msg="": None)
        self.log_callback = log_callback or (lambda msg: print(msg))
        
        # Constantes del procesamiento
        self.DEFAULT_NODATA = -9999.0
        self.PROJ_VAR_PREFIX = "dem_work_path_"
        
        # Lista para archivos temporales
        self.temp_files = []

    # ===========================================
    # FUNCIONES AUXILIARES DE VOLUME_CALCULATION
    # ===========================================

    def _get_layer_by_name(self, name):
        proj = QgsProject.instance()
        for lyr in proj.mapLayers().values():
            if lyr.name() == name:
                return lyr
        return None

    def _get_or_make_dem_work_path(self, dem_layer_name):
        project = QgsProject.instance()
        scope = QgsExpressionContextUtils.projectScope(project)
        key = self.PROJ_VAR_PREFIX + dem_layer_name
        work_path = scope.variable(key)
        if not work_path:
            base_tmp = f"{dem_layer_name}_work.tif"
            work_path = os.path.join(os.path.expandvars(os.getenv("TEMP") or os.getenv("TMP") or ""), base_tmp)
            QgsExpressionContextUtils.setProjectVariable(project, key, work_path)
        return work_path

    def _ensure_crs_wkt_from_layer_or_project(self, layer):
        ds = gdal.Open(layer.source(), gdal.GA_ReadOnly)
        proj_wkt = ds.GetProjection()
        if not proj_wkt:
            proj_qgis = QgsProject.instance().crs().authid()
            epsg_code = 32719
            if proj_qgis and proj_qgis.lower().startswith("epsg:"):
                try:
                    epsg_code = int(proj_qgis.split(":")[1])
                except Exception:
                    pass
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(epsg_code)
            proj_wkt = srs.ExportToWkt()
            self.log_callback(f"⚠️ CRS no definido en {layer.name()}, asignando EPSG:{epsg_code}")
        ds = None
        return proj_wkt

    def initialize_dem_work(self, dem_layer_name):
        """Duplica el DEM_MURO a un TIFF temporal persistente"""
        project = QgsProject.instance()
        dem = self._get_layer_by_name(dem_layer_name)
        if not dem:
            self.log_callback(f"❌ No se encontró la capa raster '{dem_layer_name}'")
            return False

        work_path = self._get_or_make_dem_work_path(dem_layer_name)

        if os.path.abspath(dem.source()) == os.path.abspath(work_path):
            return True

        ds_base = gdal.Open(dem.source(), gdal.GA_ReadOnly)
        if ds_base is None:
            self.log_callback(f"❌ No se pudo abrir el dataset base para {dem_layer_name}")
            return False

        band = ds_base.GetRasterBand(1)
        nodata_base = band.GetNoDataValue()
        if nodata_base is None:
            nodata_base = self.DEFAULT_NODATA

        translate_opts = gdal.TranslateOptions(
            format='GTiff',
            outputType=gdal.GDT_Float32,
            noData=nodata_base,
            creationOptions=["TILED=YES", "COMPRESS=LZW", "BIGTIFF=YES"]
        )
        gdal.Translate(work_path, ds_base, options=translate_opts)
        ds_base = None

        saved_renderer = None
        try:
            saved_renderer = dem.renderer().clone()
        except Exception:
            pass

        root = project.layerTreeRoot()
        node = root.findLayer(dem.id())
        parent = node.parent() if node else None

        project.removeMapLayer(dem.id())

        dem_work = QgsRasterLayer(work_path, dem_layer_name, "gdal")
        if not dem_work.isValid():
            self.log_callback(f"❌ Error al cargar la capa temporal de trabajo para {dem_layer_name}")
            return False

        project.addMapLayer(dem_work, False)
        if parent:
            parent.addLayer(dem_work)
        else:
            root.addLayer(dem_work)

        if saved_renderer:
            try:
                dem_work.setRenderer(saved_renderer)
            except Exception:
                pass

        try:
            dem_work.triggerRepaint()
            if iface:
                iface.mapCanvas().refreshAllLayers()
        except Exception:
            pass

        self.log_callback(f"✅ {dem_layer_name} ahora trabaja sobre temporal: {work_path}")
        return True

    def overlay_patch_onto_dem(self, patch_layer, dem_layer_name):
        """Pega el raster patch_layer encima del DEM_MURO dem_layer_name"""
        dem = self._get_layer_by_name(dem_layer_name)
        if not dem or not patch_layer:
            self.log_callback(f"❌ Capas necesarias no encontradas. dem='{dem_layer_name}' ok={bool(dem)}, patch='{patch_layer.name() if patch_layer else None}'")
            return False

        work_path = self._get_or_make_dem_work_path(dem_layer_name)
        if os.path.abspath(dem.source()) != os.path.abspath(work_path):
            if not self.initialize_dem_work(dem_layer_name):
                return False
            dem = self._get_layer_by_name(dem_layer_name)
            if not dem or os.path.abspath(dem.source()) != os.path.abspath(work_path):
                self.log_callback(f"❌ No se pudo preparar la base de trabajo para {dem_layer_name}")
                return False

        ds_work = gdal.Open(work_path, gdal.GA_Update)
        if ds_work is None:
            self.log_callback(f"❌ No se pudo abrir la base de trabajo {work_path} en modo actualización")
            return False

        ds_patch = gdal.Open(patch_layer.source(), gdal.GA_ReadOnly)
        if ds_patch is None:
            self.log_callback(f"❌ No se pudo abrir el parche {patch_layer.name()}")
            ds_work = None
            return False

        gt = ds_work.GetGeoTransform()
        px_size_x = gt[1]
        px_size_y = abs(gt[5])
        width = ds_work.RasterXSize
        height = ds_work.RasterYSize
        x_min = gt[0]
        y_max = gt[3]
        x_max = x_min + px_size_x * width
        y_min = y_max - px_size_y * height

        band_work = ds_work.GetRasterBand(1)
        nodata_base = band_work.GetNoDataValue()
        if nodata_base is None:
            nodata_base = self.DEFAULT_NODATA
            band_work.SetNoDataValue(nodata_base)

        proj_wkt = ds_work.GetProjection()
        if not proj_wkt:
            proj_wkt = self._ensure_crs_wkt_from_layer_or_project(dem)
            ds_work.SetProjection(proj_wkt)

        band_patch = ds_patch.GetRasterBand(1)
        nodata_patch = band_patch.GetNoDataValue()
        if nodata_patch is None:
            nodata_patch = self.DEFAULT_NODATA

        warp_opts = gdal.WarpOptions(
            format='MEM',
            xRes=px_size_x,
            yRes=px_size_y,
            outputBounds=[x_min, y_min, x_max, y_max],
            targetAlignedPixels=True,
            dstSRS=proj_wkt,
            width=width,
            height=height,
            srcNodata=nodata_patch,
            dstNodata=nodata_patch,
            resampleAlg=self.resample_algorithm,
            multithread=True
        )
        ds_patch_aligned = gdal.Warp('', ds_patch, options=warp_opts)
        if ds_patch_aligned is None:
            self.log_callback(f"❌ Error al remuestrear el parche {patch_layer.name()} en memoria")
            ds_work = None
            ds_patch = None
            return False

        base_arr = band_work.ReadAsArray().astype(np.float32)
        patch_arr = ds_patch_aligned.ReadAsArray().astype(np.float32)

        # Máscara mejorada para evitar valores extremos durante el pegado
        mask = (patch_arr != nodata_patch) & (np.abs(patch_arr) < 1000) & (~np.isnan(patch_arr)) & (~np.isinf(patch_arr))
        if not np.any(mask):
            self.log_callback(f"⚠️ Parche '{patch_layer.name()}' no tiene celdas válidas dentro de la extensión de {dem_layer_name}")
        else:
            # Logging para debugging del pegado
            pixeles_validos = np.count_nonzero(mask)
            rango_patch = f"{np.min(patch_arr[mask]):.2f} a {np.max(patch_arr[mask]):.2f}"
            self.log_callback(f"🔧 Pegando {pixeles_validos} píxeles válidos (rango: {rango_patch}) sobre '{dem_layer_name}'")
            
            base_arr[mask] = patch_arr[mask]
            band_work.WriteArray(base_arr)
            band_work.SetNoDataValue(nodata_base)
            band_work.FlushCache()
            ds_work.FlushCache()
            self.log_callback(f"✅ Parche '{patch_layer.name()}' pegado correctamente sobre '{dem_layer_name}'")

        ds_patch_aligned = None
        ds_patch = None
        ds_work = None

        try:
            # Forzar recarga completa de la capa desde disco
            dem.dataProvider().reloadData()
            dem.triggerRepaint()
            if iface:
                iface.mapCanvas().refresh()
                iface.mapCanvas().refreshAllLayers()
        except Exception:
            pass

        return True

    # ===========================================
    # FUNCIONES DE CÁLCULO VOLUMÉTRICO
    # ===========================================

    def parsear_fecha(self, fecha_str):
        try:
            return datetime.strptime(fecha_str, "%d-%m-%Y")
        except ValueError as e:
            self.log_callback(f"⚠️ Error al parsear fecha '{fecha_str}': {e}")
            return None

    def nombre_sin_prefijo(self, nombre):
        return nombre[1:] if nombre.startswith("F") else nombre

    def calcular_volumenes(self, poligono_layer, tin, base, tabla, base_name):
        """
        Calcula volúmenes y espesores y actualiza la tabla
        
        Aplica filtrado de outliers por percentiles para evitar espesores máximos irreales:
        - Utiliza percentil alto (default P99) para limitar espesor máximo
        - Utiliza percentil bajo (default P1) para ajustar espesor mínimo  
        - Opcionalmente aplica límite absoluto (max_expected_thickness)
        - Registra estadísticas detalladas de filtrado en logs
        """
        try:
            project_crs = QgsProject.instance().crs()
            if not tin.crs().isValid():
                self.log_callback(f"⚠️ CRS inválido para TIN {tin.name()}, asignando CRS del proyecto: {project_crs.authid()}")
                tin.setCrs(project_crs)
            if not base.crs().isValid():
                self.log_callback(f"⚠️ CRS inválido para base DEM {base.name()}, asignando CRS del proyecto: {project_crs.authid()}")
                base.setCrs(project_crs)
            if tin.crs() != base.crs():
                self.log_callback(f"⚠️ CRS diferentes entre TIN ({tin.crs().authid()}) y base DEM ({base.crs().authid()}), alineando al CRS del proyecto")
                tin.setCrs(project_crs)
                base.setCrs(project_crs)
            
            tin_extent = tin.extent()
            base_extent = base.extent()
            if tin_extent.isEmpty() or base_extent.isEmpty():
                self.log_callback(f"❌ Error: Extensión vacía para {base_name} (TIN: {tin_extent.isEmpty()}, Base: {base_extent.isEmpty()})")
                return
            
            output_diff = processing.run("qgis:rastercalculator", {
                'EXPRESSION': f'"{tin.name()}@1" - "{base.name()}@1"',
                'LAYERS': [tin, base],
                'CRS': project_crs.authid(),
                'EXTENT': tin_extent,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            })['OUTPUT']

            if poligono_layer.featureCount() > 0:
                output_clip = processing.run("gdal:cliprasterbymasklayer", {
                    'INPUT': output_diff,
                    'MASK': poligono_layer,
                    'CROP_TO_CUTLINE': True,
                    'KEEP_RESOLUTION': True,
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                })['OUTPUT']
            else:
                output_clip = output_diff

            ds = gdal.Open(output_clip)
            if ds is None:
                self.log_callback(f"❌ Error: No se pudo abrir el ráster recortado para {base_name}")
                return

            band = ds.GetRasterBand(1)
            arr = band.ReadAsArray()
            if arr is None:
                self.log_callback(f"❌ Error: No se pudo leer el array de datos para {base_name}")
                return

            arr = arr.astype(float)
            gt = ds.GetGeoTransform()
            pixel_area = abs(gt[1] * gt[5])

            nodata = band.GetNoDataValue()
            if nodata is not None:
                arr = np.ma.masked_equal(arr, nodata)
            else:
                arr = np.ma.masked_invalid(arr)

            valid_espesores = np.abs(arr[~arr.mask])
            if valid_espesores.size > 0:
                # Valores originales (sin filtros)
                original_min = np.min(valid_espesores)
                original_max = np.max(valid_espesores)
                
                # Aplicar filtrado de outliers si está habilitado
                if self.ENABLE_OUTLIER_FILTERING and valid_espesores.size > 10:  # Mínimo 10 píxeles para percentiles
                    # Calcular percentiles para filtrar outliers
                    p_high = np.percentile(valid_espesores, self.PERCENTILE_HIGH)
                    p_low = np.percentile(valid_espesores, self.PERCENTILE_LOW)
                    
                    # Contar outliers para reporte
                    outliers_high = np.sum(valid_espesores > p_high)
                    outliers_low = np.sum(valid_espesores < p_low)
                    
                    # Aplicar límites por percentiles
                    candidate_max = min(original_max, p_high)
                    candidate_min = max(original_min, p_low)
                    
                    # Aplicar límite absoluto si está configurado
                    if self.MAX_EXPECTED_THICKNESS is not None:
                        candidate_max = min(candidate_max, self.MAX_EXPECTED_THICKNESS)
                    
                    # Calcular espesores finales
                    espesor_min = max(round(candidate_min, 4), self.MIN_ESPESOR)
                    espesor_max = max(round(candidate_max, 4), self.MIN_ESPESOR)
                    
                    # Log detallado del filtrado
                    self.log_callback(f"📊 Filtrado de outliers para {base_name}:")
                    self.log_callback(f"   🔢 Píxeles válidos: {valid_espesores.size}")
                    self.log_callback(f"   📈 Rango original: {original_min:.4f}m - {original_max:.4f}m")
                    self.log_callback(f"   🎯 Percentiles P{self.PERCENTILE_LOW}/P{self.PERCENTILE_HIGH}: {p_low:.4f}m - {p_high:.4f}m")
                    self.log_callback(f"   🚫 Outliers eliminados: {outliers_low + outliers_high} píxeles ({outliers_low} bajos, {outliers_high} altos)")
                    self.log_callback(f"   ✅ Rango filtrado: {espesor_min:.4f}m - {espesor_max:.4f}m")
                    
                    if original_max != espesor_max:
                        reduccion = ((original_max - espesor_max) / original_max) * 100
                        self.log_callback(f"   📉 Espesor máximo reducido en {reduccion:.1f}% ({original_max:.4f}m → {espesor_max:.4f}m)")
                
                else:
                    # Sin filtrado: usar valores originales
                    espesor_min = max(round(original_min, 4), self.MIN_ESPESOR)
                    espesor_max = max(round(original_max, 4), self.MIN_ESPESOR)
                    
                    if not self.ENABLE_OUTLIER_FILTERING:
                        self.log_callback(f"⚠️ Filtrado de outliers deshabilitado para {base_name}")
                    else:
                        self.log_callback(f"⚠️ Pocos píxeles ({valid_espesores.size}) para filtrado de percentiles en {base_name}")
            else:
                espesor_min = None
                espesor_max = None

            if arr.mask.all():
                corte = 0.0
                relleno = 0.0
                espesor_medio = 0.0
            else:
                relleno = arr[arr > 0].sum() * pixel_area if np.any(arr > 0) else 0.0
                corte = -arr[arr < 0].sum() * pixel_area if np.any(arr < 0) else 0.0
                volumen_neto = relleno - corte
                area_analisada = np.count_nonzero(~arr.mask) * pixel_area if isinstance(arr, np.ma.MaskedArray) else arr.size * pixel_area
                espesor_medio = volumen_neto / area_analisada if area_analisada > 0 else 0.0

            try:
                for feature in tabla.getFeatures():
                    if feature["Foto"] == f"{base_name}.jpg" or feature["Foto"] == f"F{base_name}":
                        feature["Cut"] = round(float(corte), 2) if corte is not None else None
                        feature["Fill"] = round(float(relleno), 2) if relleno is not None else None
                        feature["Espesor"] = round(float(espesor_medio), 4) if espesor_medio is not None else None
                        feature["Espesor mínimo"] = espesor_min
                        feature["Espesor máximo"] = espesor_max
                        tabla.dataProvider().changeAttributeValues({feature.id(): {
                            tabla.fields().indexFromName("Cut"): feature["Cut"],
                            tabla.fields().indexFromName("Fill"): feature["Fill"],
                            tabla.fields().indexFromName("Espesor"): feature["Espesor"],
                            tabla.fields().indexFromName("Espesor mínimo"): feature["Espesor mínimo"],
                            tabla.fields().indexFromName("Espesor máximo"): feature["Espesor máximo"],
                        }})
                        tabla.updateFeature(feature)
                        self.log_callback(f"✔️ Campos de volúmenes y espesores actualizados en la tabla para {base_name}")
                        break
                else:
                    self.log_callback(f"⚠️ No se encontró feature con Foto=F{base_name} para actualizar volúmenes y espesores")
            except Exception as e:
                self.log_callback(f"❌ Error al actualizar volúmenes y espesores en la tabla para {base_name}: {e}")

            self.log_callback(f"✔️ Volúmenes y espesores calculados para {base_name}: Corte={corte:.2f} m³, Relleno={relleno:.2f} m³, Espesor medio={espesor_medio:.4f}m, Espesor mínimo={espesor_min}m, Espesor máximo={espesor_max}m")

        except Exception as e:
            self.log_callback(f"❌ Error al calcular volúmenes y espesores para {base_name}: {e}")

    def parsear_nombre_archivo(self, nombre):
        try:
            parts = nombre.split("_")
            if len(parts) < 4:
                raise ValueError("Formato de nombre incorrecto - faltan componentes")
            
            fecha_raw = parts[0]
            fecha = f"{fecha_raw[4:6]}-{fecha_raw[2:4]}-20{fecha_raw[0:2]}"
            muro_raw = parts[1].upper()  # Convertir a mayúsculas
            muro_dict = {"MP": "Principal", "ME": "Este", "MO": "Oeste"}
            muro = muro_dict.get(muro_raw, muro_raw)
            sector_raw = parts[2]
            sector = f"SECTOR {sector_raw[1:]}"
            
            # Si hay más de 4 componentes, combinar los restantes como relleno
            if len(parts) > 4:
                relleno = "_".join(parts[3:])  # Combinar todos los componentes restantes
            else:
                relleno = parts[3]
            
            return {
                "Protocolo Topografico": "",
                "Fecha": fecha,
                "Muro": muro,
                "Sector": sector,
                "Relleno": relleno,
                "Muro_Code": muro_raw
            }
        except Exception as e:
            self.log_callback(f"❌ Error al parsear nombre {nombre}: {e}")
            return {
                "Protocolo Topografico": "",
                "Fecha": nombre,
                "Muro": "",
                "Sector": "",
                "Relleno": "",
                "Muro_Code": ""
            }

    # ===========================================
    # FUNCIONES DE PANTALLAZOS CON DIFERENCIAS DEM
    # ===========================================

    def calculate_difference(self, tin_layer, dem_base_layer, output_name):
        """Calcula la diferencia entre tin_layer y dem_base_layer usando QgsRasterCalculator."""
        if not tin_layer or not dem_base_layer:
            self.log_callback(f"❌ Error: Capa TIN o DEM base no encontrada para {output_name}")
            return None
        
        entries = []
        entry_tin = QgsRasterCalculatorEntry()
        entry_tin.ref = 'tin@1'
        entry_tin.raster = tin_layer
        entry_tin.bandNumber = 1
        entries.append(entry_tin)
        
        entry_base = QgsRasterCalculatorEntry()
        entry_base.ref = 'base@1'
        entry_base.raster = dem_base_layer
        entry_base.bandNumber = 1
        entries.append(entry_base)
        
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"temp_diff_{output_name}_{os.getpid()}.tif")
        self.temp_files.append(output_path)
        
        calc = QgsRasterCalculator(
            'tin@1 - base@1',
            output_path,
            'GTiff',
            tin_layer.extent(),
            tin_layer.width(),
            tin_layer.height(),
            entries
        )
        result = calc.processCalculation()
        
        if result == 0:
            diff_layer = QgsRasterLayer(output_path, f"Diff_{output_name}")
            if diff_layer.isValid():
                self.log_callback(f"✅ Diferencia calculada: {output_name}")
                return diff_layer
            else:
                self.log_callback(f"❌ Error: No se pudo cargar la capa de diferencia {output_name}")
                return None
        else:
            self.log_callback(f"❌ Error en cálculo de diferencia para {output_name}: Código {result}")
            return None

    def generar_pantallazo_diferencia_dem(self, diff_layer, capa_fondo, archivo_salida, punto_inicio_perfil=None, punto_fin_perfil=None):
        """Genera pantallazo de diferencia DEM con simbología adaptativa de corte/relleno
        
        Args:
            punto_inicio_perfil: QgsPointXY opcional para inicio de línea de perfil
            punto_fin_perfil: QgsPointXY opcional para fin de línea de perfil
        """
        from PyQt5.QtGui import QPainter, QPen
        from PyQt5.QtCore import Qt, QLineF, QPointF
        
        project = QgsProject.instance()
        layer_tree = project.layerTreeRoot()
        visibility_state = {child.layer().name(): child.isVisible() 
                           for child in layer_tree.children() 
                           if hasattr(child, 'layer') and child.layer() is not None}
        
        if diff_layer.type() != QgsMapLayer.RasterLayer:
            self.log_callback(f"❌ Error: La capa '{diff_layer.name()}' no es un raster.")
            return False
        if capa_fondo.type() != QgsMapLayer.RasterLayer:
            self.log_callback(f"❌ Error: La capa de fondo '{capa_fondo.name()}' no es un raster.")
            return False
        
        if not diff_layer.crs().isValid():
            self.log_callback(f"⚠️ CRS inválido para '{diff_layer.name()}', asignando CRS de fondo: {capa_fondo.crs().authid()}")
            diff_layer.setCrs(capa_fondo.crs())
        
        extent = diff_layer.extent()
        if extent.isEmpty() or extent.width() == 0 or extent.height() == 0:
            self.log_callback(f"❌ Error: La extensión de '{diff_layer.name()}' está vacía o inválida.")
            return False
        
        # Aplicar simbología adaptativa de corte/relleno
        original_renderer = diff_layer.renderer().clone()
        self.log_callback(f"⚙️ Aplicando simbología adaptativa para corte/relleno en {diff_layer.name()}...")
        
        # Obtener estadísticas del raster
        stats = diff_layer.dataProvider().bandStatistics(1, QgsRasterBandStats.All)
        min_val = stats.minimumValue
        max_val = stats.maximumValue
        
        # Crear simbología adaptativa
        shader = QgsRasterShader()
        color_ramp = QgsColorRampShader()
        color_ramp.setColorRampType(QgsColorRampShader.Interpolated)
        color_ramp.setClassificationMode(QgsColorRampShader.Continuous)
        
        # Usar la nueva función de colores adaptativos
        color_list = self._create_adaptive_color_ramp(min_val, max_val)
        
        color_ramp.setColorRampItemList(color_list)
        shader.setRasterShaderFunction(color_ramp)
        renderer = QgsSingleBandPseudoColorRenderer(diff_layer.dataProvider(), 1, shader)
        diff_layer.setRenderer(renderer)
        diff_layer.setOpacity(0.85)  # Aumentar opacidad para colores más intensos
        diff_layer.triggerRepaint()

        capas_visibles = [capa_fondo, diff_layer]
        for child in layer_tree.children():
            if hasattr(child, 'layer') and child.layer() is not None:
                child.setItemVisibilityChecked(child.layer() in capas_visibles)
        iface.mapCanvas().refreshAllLayers()
        
        # Ajustar rectángulo para mantener aspecto
        w, h = extent.width(), extent.height()
        aspect_img = self.PANTALLAZO_ANCHO / self.PANTALLAZO_ALTO
        if w / h > aspect_img:
            h_ajust = w / aspect_img
            rect = QgsRectangle(
                extent.xMinimum(),
                extent.center().y() - h_ajust / 2,
                extent.xMaximum(),
                extent.center().y() + h_ajust / 2
            )
        else:
            w_ajust = h * aspect_img
            rect = QgsRectangle(
                extent.center().x() - w_ajust / 2,
                extent.yMinimum(),
                extent.center().x() + w_ajust / 2,
                extent.yMaximum()
            )
        rect.scale(self.PANTALLAZO_EXPANSION)
        
        settings = QgsMapSettings()
        settings.setLayers(capas_visibles[::-1])
        settings.setBackgroundColor(QColor(255, 255, 255, 0))
        settings.setOutputSize(QSize(self.PANTALLAZO_ANCHO, self.PANTALLAZO_ALTO))
        settings.setExtent(rect)
        settings.setDestinationCrs(diff_layer.crs())
        settings.setOutputDpi(96)
        
        render = QgsMapRendererSequentialJob(settings)
        render.start()
        render.waitForFinished()
        img = render.renderedImage()
        if img.isNull():
            self.log_callback(f"❌ Error: La imagen renderizada para {diff_layer.name()} está vacía.")
            self._restore_visibility_dem(layer_tree, visibility_state, diff_layer, original_renderer)
            return False
        
        # NUEVO: Dibujar línea de perfil (geometría de línea)
        if punto_inicio_perfil:
            painter = QPainter(img)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Configurar pen: NEGRO SÓLIDO, discontinuo denso, FINO
            pen = QPen(QColor(0, 0, 0, 255))  # Negro sólido 100% opaco
            pen.setWidth(2)  # Más fino: 2px
            pen.setStyle(Qt.DashLine)  # Línea discontinua
            pen.setDashPattern([4, 2])  # Patrón más denso
            painter.setPen(pen)
            
            map_extent = settings.extent()
            
            # Verificar si es una geometría QgsGeometry (línea central)
            try:
                if hasattr(punto_inicio_perfil, 'asPolyline'):
                    # Es una geometría de línea - dibujar todos los segmentos
                    vertices = punto_inicio_perfil.asPolyline()
                    if len(vertices) >= 2:
                        for i in range(len(vertices) - 1):
                            p1 = vertices[i]
                            p2 = vertices[i + 1]
                            
                            # Convertir coordenadas a píxeles
                            x1_rel = (p1.x() - map_extent.xMinimum()) / map_extent.width()
                            y1_rel = (map_extent.yMaximum() - p1.y()) / map_extent.height()
                            px1 = x1_rel * self.PANTALLAZO_ANCHO
                            py1 = y1_rel * self.PANTALLAZO_ALTO
                            
                            x2_rel = (p2.x() - map_extent.xMinimum()) / map_extent.width()
                            y2_rel = (map_extent.yMaximum() - p2.y()) / map_extent.height()
                            px2 = x2_rel * self.PANTALLAZO_ANCHO
                            py2 = y2_rel * self.PANTALLAZO_ALTO
                            
                            painter.drawLine(QPointF(px1, py1), QPointF(px2, py2))
                elif punto_fin_perfil:
                    # Son dos puntos QgsPointXY (fallback a línea recta)
                    x1_rel = (punto_inicio_perfil.x() - map_extent.xMinimum()) / map_extent.width()
                    y1_rel = (map_extent.yMaximum() - punto_inicio_perfil.y()) / map_extent.height()
                    px1 = x1_rel * self.PANTALLAZO_ANCHO
                    py1 = y1_rel * self.PANTALLAZO_ALTO
                    
                    x2_rel = (punto_fin_perfil.x() - map_extent.xMinimum()) / map_extent.width()
                    y2_rel = (map_extent.yMaximum() - punto_fin_perfil.y()) / map_extent.height()
                    px2 = x2_rel * self.PANTALLAZO_ANCHO
                    py2 = y2_rel * self.PANTALLAZO_ALTO
                    
                    painter.drawLine(QPointF(px1, py1), QPointF(px2, py2))
            except Exception as e:
                # Si falla, no dibujar línea
                pass
            
            # Agregar leyenda en esquina inferior derecha
            try:
                from PyQt5.QtGui import QFont
                from PyQt5.QtCore import QRectF
                
                # Configurar fuente
                font = QFont("Arial", 10, QFont.Bold)
                painter.setFont(font)
                
                # Texto de leyenda
                texto_leyenda = "–––––– Perfil Topográfico"
                metrics = painter.fontMetrics()
                text_rect = metrics.boundingRect(texto_leyenda)
                text_width = text_rect.width()
                text_height = text_rect.height()
                
                # Posición: esquina inferior derecha con margen
                margin = 15
                text_x = self.PANTALLAZO_ANCHO - text_width - margin
                text_y = self.PANTALLAZO_ALTO - text_height - margin
                
                # Dibujar rectángulo de fondo blanco semi-transparente
                padding = 8
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(255, 255, 255, 220))
                painter.drawRect(
                    int(text_x - padding), 
                    int(text_y - padding), 
                    int(text_width + 2*padding), 
                    int(text_height + 2*padding)
                )
                
                # Dibujar texto negro
                painter.setPen(QColor(0, 0, 0, 255))
                painter.drawText(
                    int(text_x), 
                    int(text_y + metrics.ascent()), 
                    texto_leyenda
                )
                
            except Exception as e:
                self.log_callback(f"⚠️ Error dibujando leyenda en pantallazo: {e}")
            
            painter.end()
            
            self.log_callback(f"📏 Línea de perfil con etiqueta agregada al pantallazo")
        
        success = img.save(archivo_salida, "jpg")
        if success:
            self.log_callback(f"✅ Pantallazo de diferencia DEM exportado: {archivo_salida}")
        else:
            self.log_callback(f"❌ Error al guardar imagen para {diff_layer.name()}: {archivo_salida}")
        
        self._restore_visibility_dem(layer_tree, visibility_state, diff_layer, original_renderer)
        return success

    def _create_adaptive_color_ramp(self, min_val, max_val):
        """
        Crea una rampa de colores adaptativa basada en los valores reales de corte/relleno
        La escala se reinicia en cada iteración usando los máximos específicos encontrados
        """
        color_list = []
        
        self.log_callback(f"🎨 Creando escala adaptativa: Corte máximo {min_val:.2f}m, Relleno máximo {max_val:.2f}m")
        
        # Tolerancia mínima para considerar cambios significativos
        min_threshold = 0.01
        
        # === CORTE (valores negativos) - Degradado rojo intenso ===
        if min_val < -min_threshold:
            # Rojo muy intenso para el corte máximo real (sin límites artificiales)
            color_list.append(QgsColorRampShader.ColorRampItem(min_val, QColor(220, 0, 0, 255), f"Corte máximo ({min_val:.2f}m)"))
            
            # Gradiente intermedio del 75% del corte máximo
            cut_75 = min_val * 0.75
            color_list.append(QgsColorRampShader.ColorRampItem(cut_75, QColor(255, 50, 50, 220), f"Corte 75% ({cut_75:.2f}m)"))
            
            # Gradiente intermedio del 50% del corte máximo
            cut_50 = min_val * 0.5
            color_list.append(QgsColorRampShader.ColorRampItem(cut_50, QColor(255, 100, 100, 180), f"Corte 50% ({cut_50:.2f}m)"))
            
            # Gradiente intermedio del 25% del corte máximo
            cut_25 = min_val * 0.25
            color_list.append(QgsColorRampShader.ColorRampItem(cut_25, QColor(255, 150, 150, 140), f"Corte 25% ({cut_25:.2f}m)"))
            
            # Transición hacia el cero
            color_list.append(QgsColorRampShader.ColorRampItem(-min_threshold, QColor(255, 200, 200, 100), "Corte mínimo"))
        
        # === SIN CAMBIO - Zona neutra muy sutil ===
        color_list.append(QgsColorRampShader.ColorRampItem(0, QColor(255, 255, 255, 30), "Sin cambio"))
        
        # === RELLENO (valores positivos) - Degradado verde intenso ===
        if max_val > min_threshold:
            # Transición desde el cero
            color_list.append(QgsColorRampShader.ColorRampItem(min_threshold, QColor(200, 255, 200, 100), "Relleno mínimo"))
            
            # Gradiente intermedio del 25% del relleno máximo
            fill_25 = max_val * 0.25
            color_list.append(QgsColorRampShader.ColorRampItem(fill_25, QColor(150, 255, 150, 140), f"Relleno 25% ({fill_25:.2f}m)"))
            
            # Gradiente intermedio del 50% del relleno máximo
            fill_50 = max_val * 0.5
            color_list.append(QgsColorRampShader.ColorRampItem(fill_50, QColor(100, 255, 100, 180), f"Relleno 50% ({fill_50:.2f}m)"))
            
            # Gradiente intermedio del 75% del relleno máximo
            fill_75 = max_val * 0.75
            color_list.append(QgsColorRampShader.ColorRampItem(fill_75, QColor(50, 200, 50, 220), f"Relleno 75% ({fill_75:.2f}m)"))
            
            # Verde muy intenso para el relleno máximo real (sin límites artificiales)
            color_list.append(QgsColorRampShader.ColorRampItem(max_val, QColor(0, 160, 0, 255), f"Relleno máximo ({max_val:.2f}m)"))
        
        return color_list
    
    def _restore_visibility_dem(self, layer_tree, visibility_state, diff_layer, original_renderer):
        """Restaura el estado de visibilidad original"""
        for child in layer_tree.children():
            if hasattr(child, 'layer') and child.layer() is not None:
                original_visibility = visibility_state.get(child.layer().name(), True)
                child.setItemVisibilityChecked(original_visibility)
        diff_layer.setRenderer(original_renderer)
        diff_layer.triggerRepaint()
        iface.mapCanvas().refreshAllLayers()

    def cleanup_temp_files(self):
        """Elimina archivos temporales creados durante el proceso."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    self.log_callback(f"🗑️ Archivo temporal eliminado: {os.path.basename(temp_file)}")
            except Exception as e:
                self.log_callback(f"⚠️ No se pudo eliminar archivo temporal {temp_file}: {str(e)}")
        self.temp_files.clear()

    # ===========================================
    # FUNCIONES DE PERFILES TOPOGRÁFICOS
    # ===========================================
    
    def calcular_linea_perfil(self, tabla_feature):
        """
        Calcula la línea de perfil a lo largo del lado más largo de la cancha usando P1-P4.
        
        P1 = Oeste (min X), P2 = Este (max X), P3 = Norte (max Y), P4 = Sur (min Y)
        
        Encuentra los dos pares de puntos OPUESTOS más cortos y une sus puntos medios.
        
        Returns:
            tuple: (punto_inicio, punto_fin) como QgsPointXY
        """
        from qgis.core import QgsPointXY
        
        # Extraer coordenadas de P1-P4
        p1_e, p1_n = tabla_feature["P1_ESTE"], tabla_feature["P1_NORTE"]  # Oeste
        p2_e, p2_n = tabla_feature["P2_ESTE"], tabla_feature["P2_NORTE"]  # Este
        p3_e, p3_n = tabla_feature["P3_ESTE"], tabla_feature["P3_NORTE"]  # Norte
        p4_e, p4_n = tabla_feature["P4_ESTE"], tabla_feature["P4_NORTE"]  # Sur
        
        if None in [p1_e, p1_n, p2_e, p2_n, p3_e, p3_n, p4_e, p4_n]:
            self.log_callback("⚠️ Coordenadas P1-P4 incompletas, no se puede generar perfil")
            return None, None
        
        p1 = QgsPointXY(p1_e, p1_n)
        p2 = QgsPointXY(p2_e, p2_n)
        p3 = QgsPointXY(p3_e, p3_n)
        p4 = QgsPointXY(p4_e, p4_n)
        
        # Calcular todas las distancias entre pares de puntos
        dist_p1_p2 = p1.distance(p2)  # Oeste-Este
        dist_p1_p3 = p1.distance(p3)  # Oeste-Norte
        dist_p1_p4 = p1.distance(p4)  # Oeste-Sur
        dist_p2_p3 = p2.distance(p3)  # Este-Norte
        dist_p2_p4 = p2.distance(p4)  # Este-Sur
        dist_p3_p4 = p3.distance(p4)  # Norte-Sur
        
        # Identificar los tres posibles pares OPUESTOS:
        # Par 1: P1-P2 y P3-P4 (lados Este-Oeste opuestos)
        # Par 2: P1-P3 y P2-P4 (diagonal 1)
        # Par 3: P1-P4 y P2-P3 (diagonal 2)
        
        promedio_par1 = (dist_p1_p2 + dist_p3_p4) / 2
        promedio_par2 = (dist_p1_p3 + dist_p2_p4) / 2
        promedio_par3 = (dist_p1_p4 + dist_p2_p3) / 2
        
        self.log_callback(f"📐 Promedios pares: Par1(P1-P2/P3-P4)={promedio_par1:.2f}m, Par2(P1-P3/P2-P4)={promedio_par2:.2f}m, Par3(P1-P4/P2-P3)={promedio_par3:.2f}m")
        
        # El par con menor promedio son los lados MÁS CORTOS
        # El perfil debe unir los puntos medios de ese par
        if promedio_par1 <= promedio_par2 and promedio_par1 <= promedio_par3:
            # Par más corto: P1-P2 y P3-P4
            mid1 = QgsPointXY((p1_e + p2_e)/2, (p1_n + p2_n)/2)
            mid2 = QgsPointXY((p3_e + p4_e)/2, (p3_n + p4_n)/2)
            self.log_callback(f"📏 Perfil longitudinal: entre medios de P1-P2 y P3-P4")
        elif promedio_par2 <= promedio_par3:
            # Par más corto: P1-P3 y P2-P4
            mid1 = QgsPointXY((p1_e + p3_e)/2, (p1_n + p3_n)/2)
            mid2 = QgsPointXY((p2_e + p4_e)/2, (p2_n + p4_n)/2)
            self.log_callback(f"📏 Perfil longitudinal: entre medios de P1-P3 y P2-P4")
        else:
            # Par más corto: P1-P4 y P2-P3
            mid1 = QgsPointXY((p1_e + p4_e)/2, (p1_n + p4_n)/2)
            mid2 = QgsPointXY((p2_e + p3_e)/2, (p2_n + p3_n)/2)
            self.log_callback(f"📏 Perfil longitudinal: entre medios de P1-P4 y P2-P3")
        
        return (mid1, mid2)
    
    def calcular_linea_central_poligono(self, nombre_cancha, punto_inicio_fallback, punto_fin_fallback):
        """
        Busca y retorna la línea central pre-generada del subgrupo 'Eje Central'.
        Si no existe, usa línea recta como fallback.
        
        Args:
            nombre_cancha: Nombre de la cancha para buscar la línea central
            punto_inicio_fallback: Punto de inicio si no se encuentra la línea
            punto_fin_fallback: Punto de fin si no se encuentra la línea
            
        Returns:
            QgsGeometry: Línea central como geometría, o línea recta si no existe
        """
        from qgis.core import QgsProject, QgsGeometry
        
        # Buscar la línea central en el grupo Procesamiento_*/Eje Central
        root = QgsProject.instance().layerTreeRoot()
        linea_central_geom = None
        
        # Buscar en grupos Procesamiento_*
        for group in root.children():
            if group.name().startswith("Procesamiento_"):
                # Buscar subgrupo "Eje Central"
                for subgroup in group.children():
                    if hasattr(subgroup, 'name') and subgroup.name() == "Eje Central":
                        # Buscar capa con el nombre de la cancha
                        for layer_node in subgroup.children():
                            if hasattr(layer_node, 'layer'):
                                layer = layer_node.layer()
                                if layer and layer.name() == nombre_cancha:
                                    # Obtener la geometría de la línea central
                                    for feature in layer.getFeatures():
                                        linea_central_geom = feature.geometry()
                                        break
                                    if linea_central_geom:
                                        break
                        if linea_central_geom:
                            break
                if linea_central_geom:
                    break
        
        # Si encontramos la línea central, usarla
        if linea_central_geom and not linea_central_geom.isEmpty():
            self.log_callback(f"✅ Línea central cargada desde 'Eje Central' ({nombre_cancha})")
            return linea_central_geom
        
        # Fallback: línea recta entre puntos medios
        self.log_callback(f"⚠️ No se encontró línea central para {nombre_cancha}, usando línea recta")
        return QgsGeometry.fromPolylineXY([punto_inicio_fallback, punto_fin_fallback])
    
    
    def muestrear_perfil(self, dem_layer, tin_layer, punto_inicio, punto_fin, num_puntos=100):
        """
        Muestrea valores de DEM y TIN a lo largo de una línea de perfil.
        
        Returns:
            tuple: (distancias, valores_dem, valores_tin)
        """
        from qgis.core import QgsPointXY, QgsRaster
        
        distancias = []
        valores_dem = []
        valores_tin = []
        
        # Calcular longitud total
        longitud_total = punto_inicio.distance(punto_fin)
        
        for i in range(num_puntos):
            # Interpolación lineal a lo largo de la línea
            t = i / (num_puntos - 1)  # 0 a 1
            x = punto_inicio.x() + t * (punto_fin.x() - punto_inicio.x())
            y = punto_inicio.y() + t * (punto_fin.y() - punto_inicio.y())
            punto = QgsPointXY(x, y)
            
            # Distancia desde inicio
            dist = punto_inicio.distance(punto)
            
            # Muestrear DEM
            result_dem = dem_layer.dataProvider().identify(
                punto, QgsRaster.IdentifyFormatValue
            )
            val_dem = result_dem.results().get(1)
            
            # Muestrear TIN
            result_tin = tin_layer.dataProvider().identify(
                punto, QgsRaster.IdentifyFormatValue
            )
            val_tin = result_tin.results().get(1)
            
            # Agregar solo si ambos valores son válidos
            if val_dem is not None and val_tin is not None:
                distancias.append(dist)
                valores_dem.append(val_dem)
                valores_tin.append(val_tin)
        
        # Log de diagnóstico
        longitud_linea = punto_inicio.distance(punto_fin)
        puntos_validos = len(distancias)
        self.log_callback(f"📏 Perfil: Longitud línea={longitud_linea:.2f}m, Puntos válidos={puntos_validos}/{num_puntos}")
        
        # Normalizar distancias para que siempre empiecen en 0
        distancias_array = np.array(distancias)
        if len(distancias_array) > 0:
            distancia_original_inicio = distancias_array[0]
            distancias_array = distancias_array - distancias_array[0]
            if distancia_original_inicio > 1.0:  # Si el primer punto válido está muy lejos del inicio
                self.log_callback(f"⚠️ Primer punto válido a {distancia_original_inicio:.2f}m del inicio (posible problema de cobertura)")
        
        return (distancias_array, np.array(valores_dem), np.array(valores_tin))
    
    def muestrear_perfil_linea(self, dem_layer, tin_layer, linea_geom, num_puntos=100):
        """
        Muestrea valores de DEM y TIN a lo largo de una geometría de línea.
        Útil para perfiles que siguen la curvatura de polígonos.
        """
        from qgis.core import QgsPointXY, QgsRaster
        import numpy as np
        
        distancias = []
        valores_dem = []
        valores_tin = []
        
        longitud_total = linea_geom.length()
        if longitud_total == 0:
            return (np.array([]), np.array([]), np.array([]))
        
        for i in range(num_puntos):
            distancia = (i / (num_puntos - 1)) * longitud_total
            punto_geom = linea_geom.interpolate(distancia)
            if punto_geom.isEmpty():
                continue
                
            punto = punto_geom.asPoint()
            punto_xy = QgsPointXY(punto)
            
            result_dem = dem_layer.dataProvider().identify(punto_xy, QgsRaster.IdentifyFormatValue)
            val_dem = result_dem.results().get(1)
            
            result_tin = tin_layer.dataProvider().identify(punto_xy, QgsRaster.IdentifyFormatValue)
            val_tin = result_tin.results().get(1)
            
            if val_dem is not None and val_tin is not None:
                distancias.append(distancia)
                valores_dem.append(val_dem)
                valores_tin.append(val_tin)
        
        puntos_validos = len(distancias)
        self.log_callback(f"📏 Perfil (línea central): Longitud={longitud_total:.2f}m, Puntos válidos={puntos_validos}/{num_puntos}")
        
        distancias_array = np.array(distancias)
        if len(distancias_array) > 0:
            distancias_array = distancias_array - distancias_array[0]
        
        return (distancias_array, np.array(valores_dem), np.array(valores_tin))
    
    def muestrear_perfil_poligono(self, dem_layer, tin_layer, poligono_layer, nombre_cancha, num_puntos=100):
        """
        Muestrea valores de DEM y TIN a lo largo del eje central del polígono de la cancha.
        Esto permite seguir la geometría real de canchas curvas/arqueadas.
        
        Args:
            dem_layer: Capa DEM
            tin_layer: Capa TIN
            poligono_layer: Capa vectorial del polígono de la cancha
            nombre_cancha: Nombre de la cancha para buscar el feature
            num_puntos: Número de puntos a muestrear
        
        Returns:
            tuple: (distancias, valores_dem, valores_tin)
        """
        from qgis.core import QgsPointXY, QgsRaster, QgsGeometry
        import numpy as np
        
        # Buscar el polígono de esta cancha
        poligono_geom = None
        for feature in poligono_layer.getFeatures():
            if feature.id() or True:  # Buscar por nombre si es posible
                poligono_geom = feature.geometry()
                break
        
        if not poligono_geom:
            self.log_callback(f"⚠️ No se encontró polígono para {nombre_cancha}")
            return (np.array([]), np.array([]), np.array([]))
        
        # Obtener el skeleton/eje central del polígono
        # Usaremos una aproximación: línea entre centroides de mitades del polígono
        bbox = poligono_geom.boundingBox()
        centroid = poligono_geom.centroid().asPoint()
        
        # Normalizar geometría (buffer con distancia 0 para limpiar)
        boundary = poligono_geom.buffer(0, 5).boundary()
        
        # Muestrear puntos a lo largo del perímetro y encontrar el eje central
        # Por simplicidad, usaremos la línea del polígono densificada
        densified = poligono_geom.densifyByCount(num_puntos)
        
        distancias = []
        valores_dem = []
        valores_tin = []
        
        # Obtener vértices del polígono densificado
        vertices = []
        for vertex in densified.vertices():
            vertices.append(QgsPointXY(vertex))
        
        if len(vertices) < 2:
            return (np.array([]), np.array([]), np.array([]))
        
        # Calcular centroide móvil a lo largo del polígono
        # Tomar puntos del centro del polígono
        distancia_acum = 0
        punto_anterior = vertices[0]
        
        for i, punto in enumerate(vertices):
            if i > 0:
                distancia_acum += punto_anterior.distance(punto)
            
            # Muestrear DEM y TIN en este punto
            result_dem = dem_layer.dataProvider().identify(
                punto, QgsRaster.IdentifyFormatValue
            )
            val_dem = result_dem.results().get(1)
            
            result_tin = tin_layer.dataProvider().identify(
                punto, QgsRaster.IdentifyFormatValue
            )
            val_tin = result_tin.results().get(1)
            
            if val_dem is not None and val_tin is not None:
                distancias.append(distancia_acum)
                valores_dem.append(val_dem)
                valores_tin.append(val_tin)
            
            punto_anterior = punto
        
        # Log de diagnóstico
        puntos_validos = len(distancias)
        longitud_total = distancia_acum if distancia_acum > 0 else 0
        self.log_callback(f"📏 Perfil (polígono): Longitud total={longitud_total:.2f}m, Puntos válidos={puntos_validos}/{len(vertices)}")
        
        # Normalizar distancias para que empiecen en 0
        distancias_array = np.array(distancias)
        if len(distancias_array) > 0:
            distancia_original_inicio = distancias_array[0]
            distancias_array = distancias_array - distancias_array[0]
            if distancia_original_inicio > 1.0:
                self.log_callback(f"⚠️ Primer punto válido a {distancia_original_inicio:.2f}m del inicio")
        
        return (distancias_array, np.array(valores_dem), np.array(valores_tin))
    
    def generar_grafico_perfil(self, distancias, valores_dem, valores_tin, archivo_salida, nombre_cancha):
        """
        Genera gráfico de perfil topográfico con áreas de corte/relleno coloreadas.
        
        Args:
            distancias: Array de distancias reales del perfil
            valores_dem: Array de valores del DEM
            valores_tin: Array de valores del TIN
            archivo_salida: Ruta donde guardar el gráfico
            nombre_cancha: Nombre de la cancha (no se usa en el título)
        """
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plotear líneas principales con nuevas etiquetas
        ax.plot(distancias, valores_dem, color='#1f77b4', linewidth=2.5, label='Terreno', zorder=3)
        ax.plot(distancias, valores_tin, color='#ff7f0e', linewidth=2.5, label='Cancha Levantada', zorder=3)
        
        # Rellenar áreas de corte y relleno
        for i in range(len(distancias) - 1):
            if valores_tin[i] > valores_dem[i]:
                # Relleno (verde tenue)
                ax.fill_between(
                    [distancias[i], distancias[i+1]],
                    [valores_dem[i], valores_dem[i+1]],
                    [valores_tin[i], valores_tin[i+1]],
                    color='green', alpha=0.3, zorder=1
                )
            else:
                # Corte (rojo tenue)
                ax.fill_between(
                    [distancias[i], distancias[i+1]],
                    [valores_dem[i], valores_dem[i+1]],
                    [valores_tin[i], valores_tin[i+1]],
                    color='red', alpha=0.3, zorder=1
                )
        
        # Configuración del gráfico (sin título)
        ax.set_xlabel('Distancia (m)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Cota (m)', fontsize=12, fontweight='bold')
        # Título removido según solicitud del usuario
        
        ax.legend(loc='best', fontsize=10, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Ajustar layout
        plt.tight_layout()
        
        # Guardar
        plt.savefig(archivo_salida, dpi=150, bbox_inches='tight')
        plt.close()
        
        self.log_callback(f"✅ Perfil topográfico generado: {archivo_salida}")
    
    def actualizar_campo_perfil(self, tabla, feature, nombre_archivo):
        """
        Actualiza el campo Perfil del feature con el nombre del archivo generado
        
        Args:
            tabla: QgsVectorLayer de la tabla base
            feature: QgsFeature a actualizar
            nombre_archivo: Nombre del archivo (sin extensión .jpg)
        """
        try:
            tabla.startEditing()
            
            # Obtener índice del campo Perfil
            field_index = tabla.fields().indexFromName('Perfil')
            if field_index == -1:
                self.log_callback("⚠️ Campo 'Perfil' no encontrado en la tabla")
                tabla.rollBack()
                return
            
            # Actualizar el valor
            tabla.changeAttributeValue(feature.id(), field_index, nombre_archivo)
            tabla.commitChanges()
            self.log_callback(f"📝 Campo Perfil actualizado: {nombre_archivo}")
            
        except Exception as e:
            tabla.rollBack()
            self.log_callback(f"⚠️ Error al actualizar campo Perfil: {str(e)}")


    # ===========================================
    # MÉTODO PRINCIPAL UNIFICADO
    # ===========================================

    def ejecutar_calculo_volumenes_con_pantallazos(self):
        """
        Método principal unificado que ejecuta el flujo incremental:
        1. Orden cronológico
        2. Cálculo volumen (TIN nuevo vs DEM muro)
        3. Pantallazos de diferencia DEM 
        4. Pegado incremental
        5. Actualización para siguiente fila
        """
        try:
            self.progress_callback(5, "Iniciando cálculo volumétrico con pantallazos...")
            self.log_callback("🔧 Cálculo volumétrico con generación de pantallazos...")

            # Asegurar carpeta de salida
            if not os.path.exists(self.CARPETA_PLANOS):
                os.makedirs(self.CARPETA_PLANOS)
                self.log_callback(f"📁 Carpeta creada: {self.CARPETA_PLANOS}")

            project = QgsProject.instance()
            fecha_proc = datetime.now().strftime("%y%m%d")
            group_name = f"Procesamiento_{fecha_proc}"
            root = project.layerTreeRoot()
            group = root.findGroup(group_name)
            if not group:
                return {'success': False, 'message': f'Grupo "{group_name}" no encontrado.'}

            poligonos_group = group.findGroup("Poligonos")
            triangulaciones_group = group.findGroup("Triangulaciones")
            if not poligonos_group or not triangulaciones_group:
                return {'success': False, 'message': 'Subgrupos no encontrados.'}

            poligonos_layers = {l.name(): l.layer() for l in poligonos_group.findLayers() if l.layer().type() == QgsMapLayer.VectorLayer}
            triangulaciones_layers = {l.name(): l.layer() for l in triangulaciones_group.findLayers() if l.layer().type() == QgsMapLayer.RasterLayer}

            dem_map = {"MP": "DEM_MP", "MO": "DEM_MO", "ME": "DEM_ME"}

            tabla = None
            for layer in project.mapLayers().values():
                if layer.name() == "Tabla Base Datos":
                    tabla = layer
                    break
            if not tabla:
                return {'success': False, 'message': 'Tabla no encontrada.'}

            # Buscar capa de fondo para pantallazos
            capa_fondo = None
            for layer in project.mapLayers().values():
                if layer.name().lower() == self.NOMBRE_CAPA_FONDO.lower():
                    capa_fondo = layer
                    break
            if not capa_fondo:
                self.log_callback(f"⚠️ Capa de fondo '{self.NOMBRE_CAPA_FONDO}' no encontrada, pantallazos sin fondo")

            # Orden cronológico
            fecha_base_map = {}
            for feature in tabla.getFeatures():
                foto = feature["Foto"]
                fecha_str = feature["Fecha"]
                if foto and fecha_str:
                    base_name = os.path.splitext(foto)[0].lstrip("F")
                    fecha = self.parsear_fecha(fecha_str)
                    if fecha:
                        fecha_base_map[base_name] = fecha

            sorted_bases = sorted(fecha_base_map.keys(), key=lambda x: fecha_base_map.get(x, datetime.min))

            if not sorted_bases:
                return {'success': False, 'message': 'No se encontraron registros válidos.'}
            
            # Asegurar que existe la carpeta de perfiles
            os.makedirs(self.CARPETA_PERFILES, exist_ok=True)
            
            # Verificar/crear columna Perfil en la tabla
            field_names = [field.name() for field in tabla.fields()]
            if 'Perfil' not in field_names:
                self.log_callback("🔧 Creando columna 'Perfil' en Tabla Base Datos...")
                tabla.startEditing()
                from PyQt5.QtCore import QVariant
                from qgis.core import QgsField
                new_field = QgsField('Perfil', QVariant.String, len=255)
                tabla.dataProvider().addAttributes([new_field])
                tabla.updateFields()
                tabla.commitChanges()
                self.log_callback("✅ Columna 'Perfil' creada exitosamente")
            else:
                self.log_callback("ℹ️ La columna 'Perfil' ya existe en la tabla")

            # PROCESAR FLUJO INCREMENTAL
            total_bases = len(sorted_bases)
            bases_procesadas = 0
            pantallazos_exitosos = 0
            temp_diff_layers = []

            for base in sorted_bases:
                bases_procesadas += 1
                progreso = 30 + int((bases_procesadas / total_bases) * 60)
                self.progress_callback(progreso, f"Procesando {base}...")

                nombre_layer = self.nombre_sin_prefijo(base)
                if nombre_layer not in poligonos_layers or nombre_layer not in triangulaciones_layers:
                    self.log_callback(f"⚠️ Capas no encontradas para {base}")
                    continue
                    
                poligono_layer = poligonos_layers[nombre_layer]
                tin_nuevo = triangulaciones_layers[nombre_layer]

                datos_nombre = self.parsear_nombre_archivo(nombre_layer)
                muro_code = datos_nombre["Muro_Code"].upper()  # Convertir a mayúsculas
                dem_name = dem_map.get(muro_code)
                if not dem_name or not self.initialize_dem_work(dem_name):
                    self.log_callback(f"⚠️ No se pudo inicializar DEM para {muro_code}")
                    continue

                tin_base = self._get_layer_by_name(dem_name)
                if not tin_base:
                    self.log_callback(f"⚠️ No se encontró DEM para {muro_code}")
                    continue

                # Forzar recarga de datos de la base antes de calcular (importante para procesamiento incremental)
                try:
                    tin_base.dataProvider().reloadData()
                    tin_base.triggerRepaint()
                except Exception:
                    pass

                fecha_str = fecha_base_map.get(base)
                self.log_callback(f"🔄 Procesando {base} (Fecha: {fecha_str.strftime('%d-%m-%Y') if fecha_str else 'N/A'})")

                # 1) CALCULAR VOLÚMENES Y ESPESORES
                self.calcular_volumenes(poligono_layer, tin_nuevo, tin_base, tabla, nombre_layer)

                # 2) GENERAR PANTALLAZO DE DIFERENCIA DEM y PERFIL
                if capa_fondo:
                    # Calcular línea de perfil (recta como fallback)
                    punto_inicio_perfil, punto_fin_perfil = None, None
                    linea_perfil_geom = None
                    
                    # Buscar feature en tabla para P1-P4
                    for feat in tabla.getFeatures():
                        foto_field = feat["Foto"]
                        if foto_field and (base in foto_field or f"F{base}" == foto_field):
                            punto_inicio_perfil, punto_fin_perfil = self.calcular_linea_perfil(feat)
                            
                            # Intentar calcular línea central desde polígono
                            if punto_inicio_perfil and punto_fin_perfil:
                                linea_perfil_geom = self.calcular_linea_central_poligono(
                                    nombre_layer, punto_inicio_perfil, punto_fin_perfil
                                )
                            break
                    
                    # Calcular diferencia TIN nuevo vs DEM muro
                    diff_layer = self.calculate_difference(tin_nuevo, tin_base, nombre_layer)
                    if diff_layer:
                        # Generar pantallazo CON línea de perfil (central o recta)
                        archivo_pantallazo = os.path.join(self.CARPETA_PLANOS, f"P{nombre_layer}.jpg")
                        
                        try:
                            if self.generar_pantallazo_diferencia_dem(diff_layer, capa_fondo, archivo_pantallazo, 
                                                                       linea_perfil_geom, None):
                                pantallazos_exitosos += 1
                                self.log_callback(f"✅ Pantallazo generado: {nombre_layer}")
                            
                            temp_diff_layers.append(diff_layer)
                            
                        except Exception as e:
                            self.log_callback(f"❌ Error generando pantallazo para {nombre_layer}: {e}")
                
                # 2.5) GENERAR PERFIL TOPOGRÁFICO
                try:
                    # Crear carpeta si no existe
                    if not os.path.exists(self.CARPETA_PERFILES):
                        os.makedirs(self.CARPETA_PERFILES)
                        self.log_callback(f"📁 Carpeta creada: {self.CARPETA_PERFILES}")
                    
                    # Obtener feature de la tabla para extraer P1-P4
                    tabla_feature = None
                    for feat in tabla.getFeatures():
                        foto_field = feat["Foto"]
                        if foto_field and (base in foto_field or f"F{base}" == foto_field):
                            tabla_feature = feat
                            break
                    
                    if tabla_feature:
                        # Calcular línea de perfil (recta como fallback)
                        punto_inicio, punto_fin = self.calcular_linea_perfil(tabla_feature)
                        
                        # Intentar obtener línea central del polígono
                        linea_perfil_geom = None
                        if punto_inicio and punto_fin:
                            linea_perfil_geom = self.calcular_linea_central_poligono(
                                nombre_layer, punto_inicio, punto_fin
                            )
                        
                        if punto_inicio and punto_fin:
                            # Muestrear valores - usar línea central si está disponible
                            if linea_perfil_geom and not linea_perfil_geom.isEmpty():
                                # Usar línea central del polígono (sigue curvatura)
                                distancias, vals_dem, vals_tin = self.muestrear_perfil_linea(
                                    tin_base, tin_nuevo, linea_perfil_geom
                                )
                            else:
                                # Fallback a línea recta
                                distancias, vals_dem, vals_tin = self.muestrear_perfil(
                                    tin_base, tin_nuevo, punto_inicio, punto_fin
                                )
                            
                            if len(distancias) > 0:
                                # Generar gráfico
                                archivo_perfil = os.path.join(self.CARPETA_PERFILES, f"PERFIL_{base}.jpg")
                                self.generar_grafico_perfil(
                                    distancias, vals_dem, vals_tin, archivo_perfil, base
                                )
                                
                                # Actualizar campo Perfil en la tabla
                                nombre_perfil = f"PERFIL_{base}"  # Sin extensión
                                self.actualizar_campo_perfil(tabla, tabla_feature, nombre_perfil)
                            else:
                                self.log_callback(f"⚠️ Sin datos válidos para perfil de {base}")
                    else:
                        self.log_callback(f"⚠️ No se encontró feature en tabla para {base}, perfil omitido")
                        
                except Exception as e:
                    self.log_callback(f"⚠️ Error generando perfil para {base}: {e}")
                    # No detener el proceso, continuar

                # 3) PEGADO INCREMENTAL (TIN nuevo se pega sobre DEM muro)
                self.overlay_patch_onto_dem(tin_nuevo, dem_name)

                # 4) ACTUALIZACIÓN AUTOMÁTICA (DEM muro se actualiza para siguiente fila)
                self.log_callback(f"✔️ Fila completada: {base}")

            # Limpieza
            self.progress_callback(95, "Limpiando archivos temporales...")
            
            # Remover capas temporales de diferencias del proyecto
            for layer in temp_diff_layers:
                if layer and layer.isValid():
                    QgsProject.instance().removeMapLayer(layer.id())
            
            # Limpiar archivos temporales del sistema
            self.cleanup_temp_files()
            
            self.progress_callback(100, "¡Proceso completado!")

            return {
                'success': True,
                'message': f'Proceso volumétrico con pantallazos completado. {bases_procesadas} bases procesadas, {pantallazos_exitosos} pantallazos generados.',
                'registros_procesados': bases_procesadas,
                'pantallazos_exitosos': pantallazos_exitosos,
                'carpeta_planos': self.CARPETA_PLANOS
            }

        except Exception as e:
            import traceback
            error_msg = f"Error durante el cálculo volumétrico con pantallazos: {str(e)}"
            error_details = traceback.format_exc()
            self.log_callback(f"❌ {error_msg}")
            self.log_callback(f"🔋 Detalles del error:\n{error_details}")
            
            # Limpieza en caso de error
            self.cleanup_temp_files()
            
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }
