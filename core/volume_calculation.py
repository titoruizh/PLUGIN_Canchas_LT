# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Volume calculation module for Canchas Las Tortolas plugin
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
Módulo de cálculo de volúmenes para Canchas Las Tortolas
Adaptado del script standalone 3.2_CalcVolumen.py - VERSIÓN COMPLETA
"""

import os
from datetime import datetime
import numpy as np
from osgeo import gdal, osr
from qgis.core import (
    QgsProject, QgsMapLayer, QgsCoordinateReferenceSystem,
    QgsRasterLayer, QgsExpressionContextUtils
)
from qgis.utils import iface
import processing

class VolumeCalculationProcessor:
    """Procesador de cálculo de volúmenes completo - TODAS las funciones del script original"""
    
    def __init__(self, proc_root, num_random_points=20, min_espesor=0.001, resample_algorithm='near',
                 progress_callback=None, log_callback=None):
        """
        Inicializar procesador con parámetros de la GUI
        
        Args:
            proc_root: Carpeta raíz de procesamiento (PROC_ROOT)
            num_random_points: Número de puntos aleatorios para análisis (default 20)
            min_espesor: Espesor mínimo permitido (default 0.001)
            resample_algorithm: Algoritmo de remuestreo (default 'near')
            progress_callback: Función callback para actualizar progreso
            log_callback: Función callback para logs
        """
        self.PROC_ROOT = proc_root
        
        # Parámetros configurables desde GUI
        self.NUM_RANDOM_POINTS = num_random_points
        self.MIN_ESPESOR = min_espesor
        self.resample_algorithm = resample_algorithm
        
        # Callbacks
        self.progress_callback = progress_callback or (lambda x, msg="": None)
        self.log_callback = log_callback or (lambda msg: print(msg))
        
        # Constantes del script original
        self.DEFAULT_NODATA = -9999.0
        self.PROJ_VAR_PREFIX = "dem_work_path_"  # + nombre de la capa DEM (DEM_MP/MO/ME)

    # ===========================================
    # FUNCIONES AUXILIARES DEL SCRIPT ORIGINAL
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
            # Un archivo temporal persistente por muro
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
        """
        Duplica el DEM_MURO a un TIFF temporal persistente y reemplaza UNA sola vez
        la capa en el proyecto para que apunte al temporal.
        """
        project = QgsProject.instance()
        dem = self._get_layer_by_name(dem_layer_name)
        if not dem:
            self.log_callback(f"❌ No se encontró la capa raster '{dem_layer_name}'")
            return False

        work_path = self._get_or_make_dem_work_path(dem_layer_name)

        # Si ya apunta al temporal, no hacer nada
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
            creationOptions=[
                "TILED=YES",
                "COMPRESS=LZW",
                "BIGTIFF=YES"
            ]
        )
        gdal.Translate(work_path, ds_base, options=translate_opts)
        ds_base = None

        # Guardar simbología del raster original
        saved_renderer = None
        try:
            saved_renderer = dem.renderer().clone()
        except Exception:
            pass

        # Reemplazar la capa por la copia temporal
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

        # Restaurar simbología si se pudo
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
        """
        Pega el raster 'patch_layer' (ej. TIN de la fila, idealmente ya recortado al polígono)
        encima del DEM_MURO 'dem_layer_name', actualizando EN SITIO el mismo TIFF temporal.
        """
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

        # Abrir datasets
        ds_work = gdal.Open(work_path, gdal.GA_Update)
        if ds_work is None:
            self.log_callback(f"❌ No se pudo abrir la base de trabajo {work_path} en modo actualización")
            return False

        ds_patch = gdal.Open(patch_layer.source(), gdal.GA_ReadOnly)
        if ds_patch is None:
            self.log_callback(f"❌ No se pudo abrir el parche {patch_layer.name()}")
            ds_work = None
            return False

        # Info base
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

        # CRS base seguro
        proj_wkt = ds_work.GetProjection()
        if not proj_wkt:
            proj_wkt = self._ensure_crs_wkt_from_layer_or_project(dem)
            ds_work.SetProjection(proj_wkt)

        # NoData patch
        band_patch = ds_patch.GetRasterBand(1)
        nodata_patch = band_patch.GetNoDataValue()
        if nodata_patch is None:
            nodata_patch = self.DEFAULT_NODATA

        # Remuestrear/parchar EN MEMORIA, alineado a la base
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
            resampleAlg=self.resample_algorithm,  # Usar parámetro de la GUI
            multithread=True
        )
        ds_patch_aligned = gdal.Warp('', ds_patch, options=warp_opts)
        if ds_patch_aligned is None:
            self.log_callback(f"❌ Error al remuestrear el parche {patch_layer.name()} en memoria")
            ds_work = None
            ds_patch = None
            return False

        # Leer arrays
        base_arr = band_work.ReadAsArray().astype(np.float32)
        patch_arr = ds_patch_aligned.ReadAsArray().astype(np.float32)

        # Máscara donde el parche tiene datos válidos
        mask = patch_arr != nodata_patch
        if not np.any(mask):
            self.log_callback(f"⚠️ Parche '{patch_layer.name()}' no tiene celdas válidas dentro de la extensión de {dem_layer_name}")
        else:
            base_arr[mask] = patch_arr[mask]
            band_work.WriteArray(base_arr)
            band_work.SetNoDataValue(nodata_base)
            band_work.FlushCache()
            ds_work.FlushCache()
            self.log_callback(f"✅ Parche '{patch_layer.name()}' pegado sobre '{dem_layer_name}' (temporal)")

        # Cerrar datasets
        ds_patch_aligned = None
        ds_patch = None
        ds_work = None

        # Refrescar vista
        try:
            dem.triggerRepaint()
            if iface:
                iface.mapCanvas().refreshAllLayers()
        except Exception:
            pass

        return True

    # ===========================================
    # LÓGICA DE CÁLCULO DE VOLÚMENES/ESPESORES
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

            # Espesores absolutos y mínimo configurado desde GUI
            valid_espesores = np.abs(arr[~arr.mask])
            if valid_espesores.size > 0:
                espesor_min = max(round(np.min(valid_espesores), 4), self.MIN_ESPESOR)
                espesor_max = max(round(np.max(valid_espesores), 4), self.MIN_ESPESOR)
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

            self.log_callback(f"✔️ Volúmenes y espesores calculados para {base_name}: Corte={corte:.2f} m³, Relleno={relleno:.2f} m³, Espesor medio={espesor_medio:.4f}, Espesor mínimo={espesor_min}, Espesor máximo={espesor_max}")

        except Exception as e:
            self.log_callback(f"❌ Error al calcular volúmenes y espesores para {base_name}: {e}")
            try:
                for feature in tabla.getFeatures():
                    if feature["Foto"] == f"{base_name}.jpg" or feature["Foto"] == f"F{base_name}":
                        feature["Cut"] = None
                        feature["Fill"] = None
                        feature["Espesor"] = None
                        feature["Espesor mínimo"] = None
                        feature["Espesor máximo"] = None
                        tabla.dataProvider().changeAttributeValues({feature.id(): {
                            tabla.fields().indexFromName("Cut"): None,
                            tabla.fields().indexFromName("Fill"): None,
                            tabla.fields().indexFromName("Espesor"): None,
                            tabla.fields().indexFromName("Espesor mínimo"): None,
                            tabla.fields().indexFromName("Espesor máximo"): None,
                        }})
                        tabla.updateFeature(feature)
                        self.log_callback(f"✔️ Campos de volúmenes y espesores puestos a None en la tabla para {base_name}")
                        break
            except Exception as e2:
                self.log_callback(f"❌ Error al establecer volúmenes y espesores a None en la tabla para {base_name}: {e2}")

    def parsear_nombre_archivo(self, nombre):
        try:
            parts = nombre.split("_")
            if len(parts) != 4:
                raise ValueError("Formato de nombre incorrecto")
            fecha_raw = parts[0]
            fecha = f"{fecha_raw[4:6]}-{fecha_raw[2:4]}-20{fecha_raw[0:2]}"
            muro_raw = parts[1]
            muro_dict = {"MP": "Principal", "ME": "Este", "MO": "Oeste"}
            muro = muro_dict.get(muro_raw, muro_raw)
            sector_raw = parts[2]
            sector = f"SECTOR {sector_raw[1:]}"
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

    # ============================================================
    # MÉTODO PRINCIPAL
    # ============================================================

    def ejecutar_calculo_volumenes_completo(self):
        """
        REEMPLAZA tu método actual con este que usa la validación corregida
        """
        try:
            # Crear validador CORREGIDO
            validator = CorrectedTinValidation(self)
            
            self.progress_callback(5, "Iniciando cálculo con validación CORREGIDA...")
            self.log_callback("🔧 Cálculo de volúmenes CON VALIDACIÓN CORREGIDA...")

            # ... (mismo código de inicialización que antes) ...
            
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

            # PROCESAR CON VALIDACIÓN CORREGIDA
            total_bases = len(sorted_bases)
            bases_procesadas = 0
            validaciones_exitosas = 0

            for base in sorted_bases:
                bases_procesadas += 1
                progreso = 30 + int((bases_procesadas / total_bases) * 60)
                self.progress_callback(progreso, f"Procesando {base} con validación corregida...")

                nombre_layer = self.nombre_sin_prefijo(base)
                if nombre_layer not in poligonos_layers or nombre_layer not in triangulaciones_layers:
                    continue
                    
                poligono_layer = poligonos_layers[nombre_layer]
                tin_nuevo = triangulaciones_layers[nombre_layer]

                datos_nombre = self.parsear_nombre_archivo(nombre_layer)
                muro_code = datos_nombre["Muro_Code"]
                dem_name = dem_map.get(muro_code)
                if not dem_name or not self.initialize_dem_work(dem_name):
                    continue

                tin_base = self._get_layer_by_name(dem_name)
                if not tin_base:
                    continue

                self.log_callback(f"🔄 Procesando {base}")

                # 1) Calcular volúmenes/espesores
                self.calcular_volumenes(poligono_layer, tin_nuevo, tin_base, tabla, nombre_layer)

                # 2) PEGADO CON VALIDACIÓN CORREGIDA
                validacion_exitosa = validator.validate_tin_patch_corrected(
                    tin_nuevo, dem_name, nombre_layer, poligono_layer
                )
                
                if validacion_exitosa:
                    validaciones_exitosas += 1
                    self.log_callback(f"✅ {base}: Pegado validado correctamente")
                else:
                    self.log_callback(f"❌ {base}: ALERTA - Pegado falló")

            # Reporte final
            self.progress_callback(95, "Generando reporte corregido...")
            reporte = validator.generate_validation_report_corrected()
            
            self.progress_callback(100, "¡Proceso con validación corregida completado!")
            
            return {
                'success': True,
                'message': f'Proceso completado con validación corregida. {validaciones_exitosas}/{bases_procesadas} pegados exitosos.',
                'registros_procesados': bases_procesadas,
                'validaciones_exitosas': validaciones_exitosas,
                'reporte_validacion': reporte
            }

        except Exception as e:
            import traceback
            error_msg = f"Error durante el cálculo con validación corregida: {str(e)}"
            self.log_callback(f"❌ {error_msg}")
            return {'success': False, 'message': error_msg}

            # ========================================
            # PROCESAR CON VALIDACIÓN INTEGRADA
            # ========================================
            total_bases = len(sorted_bases)
            bases_procesadas = 0
            validaciones_exitosas = 0

            for base in sorted_bases:
                bases_procesadas += 1
                progreso = 30 + int((bases_procesadas / total_bases) * 60)
                self.progress_callback(progreso, f"Procesando {base} con validación...")

                nombre_layer = self.nombre_sin_prefijo(base)
                if nombre_layer not in poligonos_layers:
                    self.log_callback(f"⚠️ No hay capa de polígonos para {base}")
                    continue
                poligono_layer = poligonos_layers[nombre_layer]
                
                if nombre_layer not in triangulaciones_layers:
                    self.log_callback(f"⚠️ No hay capa de triangulación para {base}")
                    continue
                tin_nuevo = triangulaciones_layers[nombre_layer]

                datos_nombre = self.parsear_nombre_archivo(nombre_layer)
                muro_code = datos_nombre["Muro_Code"]
                dem_name = dem_map.get(muro_code)
                if not dem_name:
                    self.log_callback(f"⚠️ Muro code desconocido: '{muro_code}'")
                    continue

                # Asegurar DEM de trabajo
                if not self.initialize_dem_work(dem_name):
                    self.log_callback(f"❌ No se pudo preparar DEM de trabajo para {dem_name}")
                    continue

                tin_base = self._get_layer_by_name(dem_name)
                if not tin_base:
                    self.log_callback(f"⚠️ No se encontró DEM para {muro_code}")
                    continue

                fecha_str = fecha_base_map.get(base)
                self.log_callback(f"🔄 Procesando {base} (Fecha: {fecha_str.strftime('%d-%m-%Y') if fecha_str else 'N/A'})")

                # 1) Calcular volúmenes/espesores
                self.calcular_volumenes(poligono_layer, tin_nuevo, tin_base, tabla, nombre_layer)

                # 2) PEGADO CON VALIDACIÓN LIGERA
                validacion_exitosa = validator.validate_tin_patch_memory_only(
                    tin_nuevo, dem_name, nombre_layer, poligono_layer
                )
                
                if validacion_exitosa:
                    validaciones_exitosas += 1
                    self.log_callback(f"✅ {base}: Pegado validado correctamente")
                else:
                    self.log_callback(f"❌ {base}: ALERTA - Pegado falló")

                self.log_callback(f"✔️ Fila completada: {base}")

            # Generar reporte final
            self.progress_callback(95, "Generando reporte de validación...")
            reporte = validator.generate_validation_report()
            
            self.progress_callback(100, "¡Cálculo con validación completado!")

            return {
                'success': True,
                'message': f'Proceso completado. {bases_procesadas} bases procesadas, {validaciones_exitosas}/{bases_procesadas} validaciones exitosas.',
                'registros_procesados': bases_procesadas,
                'validaciones_exitosas': validaciones_exitosas,
                'reporte_validacion': reporte
            }

        except Exception as e:
            import traceback
            error_msg = f"Error durante el cálculo con validación: {str(e)}"
            error_details = traceback.format_exc()
            self.log_callback(f"❌ {error_msg}")
            self.log_callback(f"🔋 Detalles del error:\n{error_details}")
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }


class CorrectedTinValidation:
    """Validación corregida que compara estados del DEM antes/después del pegado"""
    
    def __init__(self, processor):
        self.processor = processor
        self.validation_log = []
        
    def validate_tin_patch_corrected(self, tin_layer, dem_layer_name, base_name, poligono_layer=None):
        """
        VALIDACIÓN CORREGIDA:
        1. Guarda estado del DEM ANTES del pegado
        2. Ejecuta pegado
        3. Compara DEM ANTES vs DEM DESPUÉS
        4. Si son diferentes → pegado exitoso
        """
        
        self.processor.log_callback(f"\n🔍 VALIDACIÓN CORREGIDA: {base_name} sobre {dem_layer_name}")
        
        try:
            # Obtener DEM actual
            dem = self.processor._get_layer_by_name(dem_layer_name)
            if not dem:
                return self._log_validation(base_name, dem_layer_name, False, "DEM no encontrado")
            
            # 1. GUARDAR ESTADO DEL DEM ANTES DEL PEGADO
            dem_antes = self._read_dem_data_in_memory(dem)
            if dem_antes is None:
                return self._log_validation(base_name, dem_layer_name, False, "No se pudo leer DEM inicial")
            
            self.processor.log_callback(f"📸 Estado ANTES - Media: {dem_antes['mean']:.3f}, Std: {dem_antes['std']:.3f}")
            
            # 2. CALCULAR DIFERENCIAS PARA REFERENCIA (TIN vs DEM antes del pegado)
            diff_esperadas = self._calculate_differences_in_memory(tin_layer, dem, poligono_layer)
            if diff_esperadas:
                self.processor.log_callback(f"📊 Diferencias esperadas:")
                self.processor.log_callback(f"   - Relleno: {diff_esperadas['relleno']:.3f} m³")
                self.processor.log_callback(f"   - Corte: {diff_esperadas['corte']:.3f} m³")
                self.processor.log_callback(f"   - Píxeles diferentes: {diff_esperadas['pixeles_diferentes']}")
            
            # 3. EJECUTAR EL PEGADO
            self.processor.log_callback("🔄 Ejecutando pegado...")
            pegado_ok = self.processor.overlay_patch_onto_dem(tin_layer, dem_layer_name)
            
            if not pegado_ok:
                return self._log_validation(base_name, dem_layer_name, False, "overlay_patch_onto_dem retornó False")
            
            # 4. LEER ESTADO DEL DEM DESPUÉS DEL PEGADO
            # IMPORTANTE: Refrescar la referencia del DEM después del pegado
            dem_post = self.processor._get_layer_by_name(dem_layer_name)
            if not dem_post:
                return self._log_validation(base_name, dem_layer_name, False, "DEM no encontrado después del pegado")
                
            dem_despues = self._read_dem_data_in_memory(dem_post)
            if dem_despues is None:
                return self._log_validation(base_name, dem_layer_name, False, "No se pudo leer DEM después del pegado")
            
            self.processor.log_callback(f"📸 Estado DESPUÉS - Media: {dem_despues['mean']:.3f}, Std: {dem_despues['std']:.3f}")
            
            # 5. COMPARAR ESTADOS DEL DEM (ANTES vs DESPUÉS)
            dem_comparison = self._compare_dem_states(dem_antes, dem_despues)
            
            self.processor.log_callback(f"📈 ANÁLISIS DE CAMBIOS EN EL DEM:")
            self.processor.log_callback(f"   - Hash cambió: {dem_comparison['hash_changed']}")
            self.processor.log_callback(f"   - Píxeles modificados: {dem_comparison['pixels_changed']}")
            self.processor.log_callback(f"   - % píxeles cambiados: {dem_comparison['percent_changed']:.4f}%")
            self.processor.log_callback(f"   - Diferencia máxima: {dem_comparison['max_change']:.6f}")
            self.processor.log_callback(f"   - Diferencia media: {dem_comparison['mean_abs_change']:.6f}")
            
            # 6. CRITERIOS DE VALIDACIÓN CORREGIDOS
            # El pegado es exitoso si el DEM cambió significativamente
            tolerancia_pixels = 100  # mínimo píxeles que deben cambiar
            tolerancia_cambio = 0.001  # diferencia mínima promedio en metros
            
            pegado_exitoso = (
                dem_comparison['hash_changed'] and  # El hash del DEM cambió
                dem_comparison['pixels_changed'] >= tolerancia_pixels and  # Suficientes píxeles cambiaron
                dem_comparison['mean_abs_change'] >= tolerancia_cambio  # Cambio promedio significativo
            )
            
            if pegado_exitoso:
                mensaje = f"✅ PEGADO EXITOSO: DEM modificado ({dem_comparison['pixels_changed']} píxeles, {dem_comparison['percent_changed']:.2f}%)"
                self.processor.log_callback("✅ VALIDACIÓN EXITOSA")
            else:
                mensaje = f"❌ PEGADO FALLÓ: Sin cambios significativos en DEM (cambio: {dem_comparison['mean_abs_change']:.6f}m, píxeles: {dem_comparison['pixels_changed']})"
                self.processor.log_callback("❌ VALIDACIÓN FALLIDA")
            
            # 7. LOG DETALLADO
            return self._log_validation(
                base_name, dem_layer_name, pegado_exitoso, mensaje,
                extra_data={
                    'diferencias_esperadas': diff_esperadas,
                    'dem_antes': dem_antes,
                    'dem_despues': dem_despues,
                    'dem_comparison': dem_comparison
                }
            )
            
        except Exception as e:
            self.processor.log_callback(f"❌ Error durante validación corregida: {e}")
            return self._log_validation(base_name, dem_layer_name, False, f"Error: {str(e)}")

    def _read_dem_data_in_memory(self, dem_layer):
        """Lee todos los datos de un DEM en memoria para comparación"""
        try:
            ds = gdal.Open(dem_layer.source(), gdal.GA_ReadOnly)
            if ds is None:
                return None
            
            band = ds.GetRasterBand(1)
            data = band.ReadAsArray()
            if data is None:
                return None
                
            data = data.astype(np.float32)
            nodata = band.GetNoDataValue()
            
            # Manejar NoData
            if nodata is not None:
                valid_data = data[data != nodata]
            else:
                valid_data = data[~np.isnan(data)]
            
            if len(valid_data) == 0:
                return None
            
            # Estadísticas y hash para comparación
            result = {
                'mean': np.mean(valid_data),
                'std': np.std(valid_data),
                'min': np.min(valid_data),
                'max': np.max(valid_data),
                'valid_pixels': len(valid_data),
                'total_pixels': data.size,
                'data_hash': hash(data.tobytes()),  # Para detectar cambios exactos
                'raw_data': data  # Para comparación píxel a píxel
            }
            
            ds = None
            return result
            
        except Exception as e:
            self.processor.log_callback(f"❌ Error leyendo datos del DEM: {e}")
            return None

    def _compare_dem_states(self, dem_antes, dem_despues):
        """Compara dos estados del DEM píxel por píxel"""
        try:
            data1 = dem_antes['raw_data']
            data2 = dem_despues['raw_data']
            
            if data1.shape != data2.shape:
                return {
                    'hash_changed': True,
                    'pixels_changed': -1,
                    'percent_changed': -1,
                    'max_change': -1,
                    'mean_abs_change': -1,
                    'error': 'Diferentes dimensiones'
                }
            
            # Comparación píxel por píxel
            diff = data2 - data1
            abs_diff = np.abs(diff)
            
            # Contar píxeles que cambiaron (con tolerancia mínima)
            tolerancia_pixel = 1e-6
            changed_mask = abs_diff > tolerancia_pixel
            pixels_changed = np.sum(changed_mask)
            percent_changed = (pixels_changed / data1.size) * 100
            
            # Estadísticas de cambios
            if pixels_changed > 0:
                max_change = np.max(abs_diff)
                mean_abs_change = np.mean(abs_diff[changed_mask])
            else:
                max_change = 0.0
                mean_abs_change = 0.0
            
            return {
                'hash_changed': dem_antes['data_hash'] != dem_despues['data_hash'],
                'pixels_changed': int(pixels_changed),
                'percent_changed': float(percent_changed),
                'max_change': float(max_change),
                'mean_abs_change': float(mean_abs_change),
                'total_pixels': int(data1.size)
            }
            
        except Exception as e:
            self.processor.log_callback(f"❌ Error comparando estados del DEM: {e}")
            return {
                'hash_changed': False,
                'pixels_changed': 0,
                'percent_changed': 0,
                'max_change': 0,
                'mean_abs_change': 0,
                'error': str(e)
            }

    def _calculate_differences_in_memory(self, tin_layer, dem_layer, poligono_layer=None):
        """Calcula diferencias TIN-DEM (para referencia solamente)"""
        try:
            project_crs = QgsProject.instance().crs()
            
            if not tin_layer.crs().isValid():
                tin_layer.setCrs(project_crs)
            if not dem_layer.crs().isValid():
                dem_layer.setCrs(project_crs)
                
            tin_extent = tin_layer.extent()
            
            output_diff = processing.run("qgis:rastercalculator", {
                'EXPRESSION': f'"{tin_layer.name()}@1" - "{dem_layer.name()}@1"',
                'LAYERS': [tin_layer, dem_layer],
                'CRS': project_crs.authid(),
                'EXTENT': tin_extent,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            })['OUTPUT']

            if poligono_layer and poligono_layer.featureCount() > 0:
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
                return None

            band = ds.GetRasterBand(1)
            arr = band.ReadAsArray()
            if arr is None:
                return None

            arr = arr.astype(float)
            gt = ds.GetGeoTransform()
            pixel_area = abs(gt[1] * gt[5])

            nodata = band.GetNoDataValue()
            if nodata is not None:
                arr = np.ma.masked_equal(arr, nodata)
            else:
                arr = np.ma.masked_invalid(arr)

            ds = None

            if arr.mask.all():
                return {
                    'relleno': 0.0,
                    'corte': 0.0,
                    'diff_promedio': 0.0,
                    'pixeles_diferentes': 0
                }
            
            relleno = arr[arr > 0].sum() * pixel_area if np.any(arr > 0) else 0.0
            corte = -arr[arr < 0].sum() * pixel_area if np.any(arr < 0) else 0.0
            diff_promedio = np.mean(arr[~arr.mask])
            pixeles_diferentes = np.count_nonzero(~arr.mask)
            
            return {
                'relleno': float(relleno),
                'corte': float(corte),
                'diff_promedio': float(diff_promedio),
                'pixeles_diferentes': int(pixeles_diferentes)
            }
            
        except Exception as e:
            return None

    def _log_validation(self, base_name, dem_layer_name, success, message, extra_data=None):
        """Registra el resultado de la validación"""
        
        log_entry = {
            'timestamp': datetime.now(),
            'base_name': base_name,
            'dem_layer': dem_layer_name,
            'success': success,
            'message': message
        }
        
        if extra_data:
            log_entry.update(extra_data)
            
        self.validation_log.append(log_entry)
        return success

    def generate_validation_report_corrected(self):
        """Genera reporte con la lógica corregida"""
        
        if not self.validation_log:
            return "No hay datos de validación disponibles."
            
        lines = []
        lines.append("="*80)
        lines.append("REPORTE DE VALIDACIÓN DE PEGADO DE TINS (CORREGIDO)")
        lines.append("="*80)
        lines.append(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Resumen
        total = len(self.validation_log)
        exitosos = sum(1 for log in self.validation_log if log['success'])
        fallidos = total - exitosos
        
        lines.append("RESUMEN EJECUTIVO:")
        lines.append(f"• Total validaciones: {total}")
        lines.append(f"• Pegados exitosos: {exitosos} ({exitosos/total*100:.1f}%)")
        lines.append(f"• Pegados fallidos: {fallidos} ({fallidos/total*100:.1f}%)")
        lines.append("")
        
        if exitosos == total:
            lines.append("✅ EXCELENTE: Todos los pegados fueron exitosos")
        elif fallidos > 0:
            lines.append("⚠️  ATENCIÓN: Se detectaron algunos pegados fallidos")
        lines.append("")
        
        # Detalle por validación
        lines.append("DETALLE POR ITERACIÓN:")
        lines.append("-"*80)
        
        for i, log in enumerate(self.validation_log, 1):
            lines.append(f"\n{i}. {log['base_name']} -> {log['dem_layer']}")
            lines.append(f"   Resultado: {'✅ ÉXITO' if log['success'] else '❌ FALLA'}")
            lines.append(f"   {log['message']}")
            
            if 'dem_comparison' in log:
                comp = log['dem_comparison']
                lines.append(f"   - Píxeles modificados: {comp.get('pixels_changed', 0)}")
                lines.append(f"   - % área cambiada: {comp.get('percent_changed', 0):.4f}%")
                lines.append(f"   - Diferencia máxima: {comp.get('max_change', 0):.6f} m")
                lines.append(f"   - Diferencia media: {comp.get('mean_abs_change', 0):.6f} m")
            
            lines.append("   " + "-"*40)
        
        report = "\n".join(lines)
        self.processor.log_callback(f"\n{report}")
        return report
        
class LightweightTinValidation:
    """Validación ligera que solo usa arrays en memoria - VERSIÓN INTEGRADA"""
    
    def __init__(self, processor):
        self.processor = processor
        self.validation_log = []
        
    def validate_tin_patch_memory_only(self, tin_layer, dem_layer_name, base_name, poligono_layer=None):
        """Validación completa del pegado usando solo memoria"""
        
        self.processor.log_callback(f"\n🔍 VALIDANDO PEGADO: {base_name} sobre {dem_layer_name}")
        
        try:
            # Obtener DEM actual
            dem = self.processor._get_layer_by_name(dem_layer_name)
            if not dem:
                return self._log_validation(base_name, dem_layer_name, False, "DEM no encontrado")
            
            # 1. CALCULAR DIFERENCIAS ANTES DEL PEGADO
            diff_antes = self._calculate_differences_in_memory(tin_layer, dem, poligono_layer)
            if diff_antes is None:
                return self._log_validation(base_name, dem_layer_name, False, "No se pudieron calcular diferencias iniciales")
            
            self.processor.log_callback(f"📊 ANTES del pegado:")
            self.processor.log_callback(f"   - Relleno: {diff_antes['relleno']:.3f} m³")
            self.processor.log_callback(f"   - Corte: {diff_antes['corte']:.3f} m³")
            self.processor.log_callback(f"   - Píxeles con diferencia: {diff_antes['pixeles_diferentes']}")
            
            # 2. EJECUTAR EL PEGADO
            self.processor.log_callback("🔄 Ejecutando pegado...")
            pegado_ok = self.processor.overlay_patch_onto_dem(tin_layer, dem_layer_name)
            
            if not pegado_ok:
                return self._log_validation(base_name, dem_layer_name, False, "overlay_patch_onto_dem retornó False")
            
            # 3. CALCULAR DIFERENCIAS DESPUÉS DEL PEGADO  
            dem_post = self.processor._get_layer_by_name(dem_layer_name)
            if not dem_post:
                return self._log_validation(base_name, dem_layer_name, False, "DEM no encontrado después del pegado")
                
            diff_despues = self._calculate_differences_in_memory(tin_layer, dem_post, poligono_layer)
            if diff_despues is None:
                return self._log_validation(base_name, dem_layer_name, False, "No se pudieron calcular diferencias post-pegado")
            
            self.processor.log_callback(f"📊 DESPUÉS del pegado:")
            self.processor.log_callback(f"   - Relleno: {diff_despues['relleno']:.3f} m³")
            self.processor.log_callback(f"   - Corte: {diff_despues['corte']:.3f} m³")
            self.processor.log_callback(f"   - Píxeles con diferencia: {diff_despues['pixeles_diferentes']}")
            
            # 4. VALIDAR QUE LAS DIFERENCIAS POST-PEGADO SEAN ~0
            tolerancia_volumen = 0.1  # m³
            tolerancia_diferencia = 0.001  # metros
            
            volumen_residual_relleno = abs(diff_despues['relleno'])
            volumen_residual_corte = abs(diff_despues['corte'])
            diferencia_promedio_residual = abs(diff_despues['diff_promedio'])
            
            pegado_exitoso = (
                volumen_residual_relleno <= tolerancia_volumen and
                volumen_residual_corte <= tolerancia_volumen and
                diferencia_promedio_residual <= tolerancia_diferencia
            )
            
            # 5. ANÁLISIS DE REDUCCIÓN
            reduccion_relleno = 0
            reduccion_corte = 0
            if diff_antes['relleno'] > 0:
                reduccion_relleno = ((diff_antes['relleno'] - diff_despues['relleno']) / diff_antes['relleno']) * 100
            if abs(diff_antes['corte']) > 0:
                reduccion_corte = ((abs(diff_antes['corte']) - abs(diff_despues['corte'])) / abs(diff_antes['corte'])) * 100
            
            self.processor.log_callback(f"📈 ANÁLISIS:")
            self.processor.log_callback(f"   - Reducción relleno: {reduccion_relleno:.1f}%")
            self.processor.log_callback(f"   - Reducción corte: {reduccion_corte:.1f}%")
            self.processor.log_callback(f"   - Residuo relleno: {volumen_residual_relleno:.6f} m³")
            self.processor.log_callback(f"   - Residuo corte: {volumen_residual_corte:.6f} m³")
            
            if pegado_exitoso:
                mensaje = "✅ PEGADO EXITOSO: Diferencias reducidas a ~0"
                self.processor.log_callback("✅ VALIDACIÓN EXITOSA")
            else:
                mensaje = f"❌ PEGADO FALLÓ: Residuos significativos (R:{volumen_residual_relleno:.3f}, C:{volumen_residual_corte:.3f})"
                self.processor.log_callback("❌ VALIDACIÓN FALLIDA")
            
            # 6. LOG DETALLADO
            return self._log_validation(
                base_name, dem_layer_name, pegado_exitoso, mensaje,
                extra_data={
                    'antes': diff_antes,
                    'despues': diff_despues,
                    'reduccion_relleno_pct': reduccion_relleno,
                    'reduccion_corte_pct': reduccion_corte,
                    'volumen_residual_relleno': volumen_residual_relleno,
                    'volumen_residual_corte': volumen_residual_corte
                }
            )
            
        except Exception as e:
            self.processor.log_callback(f"❌ Error durante validación: {e}")
            return self._log_validation(base_name, dem_layer_name, False, f"Error: {str(e)}")

    def _calculate_differences_in_memory(self, tin_layer, dem_layer, poligono_layer=None):
        """Calcula diferencias TIN-DEM completamente en memoria"""
        try:
            project_crs = QgsProject.instance().crs()
            
            # Asegurar CRS
            if not tin_layer.crs().isValid():
                tin_layer.setCrs(project_crs)
            if not dem_layer.crs().isValid():
                dem_layer.setCrs(project_crs)
                
            tin_extent = tin_layer.extent()
            
            # Cálculo de diferencias
            output_diff = processing.run("qgis:rastercalculator", {
                'EXPRESSION': f'"{tin_layer.name()}@1" - "{dem_layer.name()}@1"',
                'LAYERS': [tin_layer, dem_layer],
                'CRS': project_crs.authid(),
                'EXTENT': tin_extent,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            })['OUTPUT']

            # Recortar por polígono si existe
            if poligono_layer and poligono_layer.featureCount() > 0:
                output_clip = processing.run("gdal:cliprasterbymasklayer", {
                    'INPUT': output_diff,
                    'MASK': poligono_layer,
                    'CROP_TO_CUTLINE': True,
                    'KEEP_RESOLUTION': True,
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                })['OUTPUT']
            else:
                output_clip = output_diff

            # Leer datos en memoria
            ds = gdal.Open(output_clip)
            if ds is None:
                return None

            band = ds.GetRasterBand(1)
            arr = band.ReadAsArray()
            if arr is None:
                return None

            arr = arr.astype(float)
            gt = ds.GetGeoTransform()
            pixel_area = abs(gt[1] * gt[5])

            # Procesar NoData
            nodata = band.GetNoDataValue()
            if nodata is not None:
                arr = np.ma.masked_equal(arr, nodata)
            else:
                arr = np.ma.masked_invalid(arr)

            ds = None  # Cerrar dataset temporal

            # Calcular estadísticas
            if arr.mask.all():
                return {
                    'relleno': 0.0,
                    'corte': 0.0,
                    'diff_promedio': 0.0,
                    'pixeles_diferentes': 0,
                    'pixeles_totales': 0
                }
            
            relleno = arr[arr > 0].sum() * pixel_area if np.any(arr > 0) else 0.0
            corte = -arr[arr < 0].sum() * pixel_area if np.any(arr < 0) else 0.0
            diff_promedio = np.mean(arr[~arr.mask])
            pixeles_diferentes = np.count_nonzero(~arr.mask)
            
            return {
                'relleno': float(relleno),
                'corte': float(corte),
                'diff_promedio': float(diff_promedio),
                'pixeles_diferentes': int(pixeles_diferentes),
                'pixeles_totales': int(arr.size)
            }
            
        except Exception as e:
            self.processor.log_callback(f"❌ Error calculando diferencias: {e}")
            return None

    def _log_validation(self, base_name, dem_layer_name, success, message, extra_data=None):
        """Registra el resultado de la validación"""
        
        log_entry = {
            'timestamp': datetime.now(),
            'base_name': base_name,
            'dem_layer': dem_layer_name,
            'success': success,
            'message': message
        }
        
        if extra_data:
            log_entry.update(extra_data)
            
        self.validation_log.append(log_entry)
        return success

    def generate_validation_report(self):
        """Genera reporte de validación como string"""
        
        if not self.validation_log:
            return "No hay datos de validación disponibles."
            
        lines = []
        lines.append("="*80)
        lines.append("REPORTE DE VALIDACIÓN DE PEGADO DE TINS")
        lines.append("="*80)
        lines.append(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Resumen
        total = len(self.validation_log)
        exitosos = sum(1 for log in self.validation_log if log['success'])
        fallidos = total - exitosos
        
        lines.append("RESUMEN EJECUTIVO:")
        lines.append(f"• Total validaciones: {total}")
        lines.append(f"• Pegados exitosos: {exitosos} ({exitosos/total*100:.1f}%)")
        lines.append(f"• Pegados fallidos: {fallidos} ({fallidos/total*100:.1f}%)")
        lines.append("")
        
        if fallidos > 0:
            lines.append("⚠️  ATENCIÓN: Se detectaron pegados fallidos")
            lines.append("")
        
        # Detalle
        lines.append("DETALLE POR ITERACIÓN:")
        lines.append("-"*80)
        
        for i, log in enumerate(self.validation_log, 1):
            lines.append(f"\n{i}. {log['base_name']} -> {log['dem_layer']}")
            lines.append(f"   Resultado: {'✅ ÉXITO' if log['success'] else '❌ FALLA'}")
            
            if 'antes' in log and 'despues' in log:
                antes = log['antes']
                despues = log['despues']
                
                lines.append(f"   ANTES  - Relleno: {antes['relleno']:>8.2f} m³, Corte: {antes['corte']:>8.2f} m³")
                lines.append(f"   DESPUÉS- Relleno: {despues['relleno']:>8.2f} m³, Corte: {despues['corte']:>8.2f} m³")
                
                if 'reduccion_relleno_pct' in log:
                    lines.append(f"   REDUCCIÓN - Relleno: {log['reduccion_relleno_pct']:>6.1f}%, Corte: {log['reduccion_corte_pct']:>6.1f}%")
            
            lines.append("   " + "-"*40)
        
        report = "\n".join(lines)
        
        # Imprimir en log
        self.processor.log_callback(f"\n{report}")
        
        return report
