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
        """Ejecutar todo el proceso de cálculo de volúmenes - MÉTODO PRINCIPAL"""
        try:
            self.progress_callback(5, "Iniciando cálculo de volúmenes...")
            self.log_callback("📊 Iniciando cálculo de volúmenes y espesores...")

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

            # Verificar subgrupos
            self.progress_callback(15, "Verificando subgrupos...")
            poligonos_group = group.findGroup("Poligonos")
            triangulaciones_group = group.findGroup("Triangulaciones")
            if not poligonos_group or not triangulaciones_group:
                return {
                    'success': False,
                    'message': 'Subgrupos "Poligonos" o "Triangulaciones" no encontrados.'
                }

            # Obtener capas de los subgrupos
            self.progress_callback(20, "Obteniendo capas de subgrupos...")
            poligonos_layers = {l.name(): l.layer() for l in poligonos_group.findLayers() if l.layer().type() == QgsMapLayer.VectorLayer}
            triangulaciones_layers = {l.name(): l.layer() for l in triangulaciones_group.findLayers() if l.layer().type() == QgsMapLayer.RasterLayer}

            self.log_callback("Capas en Poligonos: " + str(list(poligonos_layers.keys())))
            self.log_callback("Capas en Triangulaciones: " + str(list(triangulaciones_layers.keys())))

            # Mapeo de DEMs
            dem_map = {"MP": "DEM_MP", "MO": "DEM_MO", "ME": "DEM_ME"}

            # Buscar tabla base de datos
            self.progress_callback(25, "Buscando tabla base de datos...")
            tabla = None
            for layer in project.mapLayers().values():
                if layer.name() == "Tabla Base Datos":
                    tabla = layer
                    break
            if not tabla:
                return {
                    'success': False,
                    'message': 'Tabla "Tabla Base Datos" no encontrada. Debe crear la tabla base primero.'
                }

            # Construir mapa base->fecha desde la tabla (lógica del script original)
            self.progress_callback(30, "Construyendo orden cronológico...")
            fecha_base_map = {}
            for feature in tabla.getFeatures():
                foto = feature["Foto"]
                fecha_str = feature["Fecha"]
                if foto and fecha_str:
                    base_name = os.path.splitext(foto)[0].lstrip("F")  # normaliza 'Fxxxx.jpg' a 'xxxx'
                    fecha = self.parsear_fecha(fecha_str)
                    if fecha:
                        fecha_base_map[base_name] = fecha
                    else:
                        self.log_callback(f"⚠️ Fecha inválida para {base_name}: {fecha_str}. Se omitirá en el ordenamiento.")

            sorted_bases = sorted(
                fecha_base_map.keys(),
                key=lambda x: fecha_base_map.get(x, datetime.min),
                reverse=False
            )
            self.log_callback(f"📅 Orden cronológico de procesamiento: {sorted_bases}")

            if not sorted_bases:
                return {
                    'success': False,
                    'message': 'No se encontraron registros válidos en la tabla para procesar.'
                }

            # Procesar cada base en orden cronológico
            total_bases = len(sorted_bases)
            bases_procesadas = 0

            for base in sorted_bases:
                bases_procesadas += 1
                progreso = 30 + int((bases_procesadas / total_bases) * 60)
                self.progress_callback(progreso, f"Procesando {base}...")

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
                    self.log_callback(f"⚠️ Muro code desconocido en {base}: '{muro_code}'")
                    continue

                # Asegurar DEM de trabajo para este muro
                if not self.initialize_dem_work(dem_name):
                    self.log_callback(f"❌ No se pudo preparar DEM de trabajo para {dem_name}")
                    continue

                # Buscar DEM actual (ya debe apuntar al temporal)
                tin_base = self._get_layer_by_name(dem_name)
                if not tin_base:
                    self.log_callback(f"⚠️ No se encontró DEM para el muro {muro_code} ({base})")
                    continue

                fecha_str = fecha_base_map.get(base)
                self.log_callback(f"🔄 Procesando {base} (Fecha: {fecha_str.strftime('%d-%m-%Y') if fecha_str else 'N/A'})")

                # 1) Calcular volúmenes/espesores contra el DEM_MURO actualizado
                self.calcular_volumenes(poligono_layer, tin_nuevo, tin_base, tabla, nombre_layer)

                # 2) Pegar el TIN de esta fila sobre el DEM_MURO correspondiente
                pegado_ok = self.overlay_patch_onto_dem(tin_nuevo, dem_name)
                if not pegado_ok:
                    self.log_callback(f"⚠️ No se pudo pegar el TIN '{tin_nuevo.name()}' sobre {dem_name} para {base}")

                self.log_callback(f"✔️ Fila completada para {base} (DEM actualizado: {dem_name})")

            self.progress_callback(100, "¡Cálculo de volúmenes completado!")
            self.log_callback("✔️ Procesamiento de volúmenes, espesores y pegados incrementales completado para todas las capas.")

            return {
                'success': True,
                'message': f'Cálculo de volúmenes completado exitosamente. {bases_procesadas} registros procesados.',
                'registros_procesados': bases_procesadas,
                'dem_actualizados': list(set(self.parsear_nombre_archivo(self.nombre_sin_prefijo(base))["Muro_Code"] 
                                            for base in sorted_bases if self.parsear_nombre_archivo(self.nombre_sin_prefijo(base))["Muro_Code"]))
            }

        except Exception as e:
            import traceback
            error_msg = f"Error durante el cálculo de volúmenes: {str(e)}"
            error_details = traceback.format_exc()
            self.log_callback(f"❌ {error_msg}")
            self.log_callback(f"📋 Detalles del error:\n{error_details}")
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }