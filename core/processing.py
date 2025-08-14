# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Processing module for Canchas Las Tortolas plugin
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
Módulo de procesamiento espacial para Canchas Las Tortolas
Adaptado del script standalone 2_Procesamiento.py - VERSIÓN COMPLETA
"""

import os
from datetime import datetime
from qgis.core import (
    QgsVectorLayer, QgsRasterLayer, QgsProject, QgsProcessingFeedback,
    QgsCoordinateReferenceSystem, QgsPointXY, QgsGeometry, QgsField, QgsFeature, QgsRaster
)
from PyQt5.QtCore import QVariant
import processing
import pandas as pd
import math

class ProcessingProcessor:
    """Procesador de procesamiento espacial completo - TODAS las funciones del script original"""
    
    def __init__(self, proc_root, pixel_size=0.1, suavizado_tolerance=1.0, min_dist_vertices=2.0, 
                 progress_callback=None, log_callback=None):
        """
        Inicializar procesador con parámetros de la GUI
        
        Args:
            proc_root: Carpeta raíz de procesamiento (PROC_ROOT)
            pixel_size: Tamaño de píxel para TIN (default 0.1)
            suavizado_tolerance: Tolerancia para suavizado ASC (default 1.0)
            min_dist_vertices: Distancia mínima entre vértices (default 2.0)
            progress_callback: Función callback para actualizar progreso
            log_callback: Función callback para logs
        """
        self.PROC_ROOT = proc_root
        self.DIR_CSV_PROC = os.path.join(proc_root, "CSV-ASC")
        self.GPKG_PROC = os.path.join(proc_root, "Levantamientos.gpkg")
        
        # Parámetros configurables desde GUI
        self.PIXEL_SIZE = pixel_size
        self.SUAVIZADO_TOLERANCE_ASC = suavizado_tolerance
        self.MIN_DIST_VERTICES_ASC = min_dist_vertices
        
        # Callbacks
        self.progress_callback = progress_callback or (lambda x, msg="": None)
        self.log_callback = log_callback or (lambda msg: print(msg))
        
        # Constantes del script original
        self.NOMBRE_CAPA = "Levantamientos"
        self.DELIMITER = ";"
        self.X_FIELD = "field_3"
        self.Y_FIELD = "field_2"
        self.Z_FIELD = "field_4"
        self.CRS = "EPSG:32719"
        self.SKIP_LINES = 1
        self.USE_HEADER = "No"

    # =========================
    # FUNCIONES PRINCIPALES DEL SCRIPT ORIGINAL
    # =========================

    def get_or_create_group(self, project, group_name):
        root = project.layerTreeRoot()
        group = root.findGroup(group_name)
        if not group:
            group = root.insertGroup(0, group_name)
        else:
            if root.children().index(group) != 0:
                cloned_group = group.clone()
                root.removeChildNode(group)
                root.insertChildNode(0, cloned_group)
                group = cloned_group
        group.setItemVisibilityChecked(False)  # Apagar el grupo
        group.setExpanded(False)  # Contraer el grupo
        return group

    def get_or_create_subgroup(self, parent_group, subgroup_name):
        subgroup = parent_group.findGroup(subgroup_name)
        if not subgroup:
            subgroup = parent_group.insertGroup(0, subgroup_name)
        else:
            if parent_group.children().index(subgroup) != 0:
                cloned_subgroup = subgroup.clone()
                parent_group.removeChildNode(subgroup)
                parent_group.insertChildNode(0, cloned_subgroup)
                subgroup = cloned_subgroup
        subgroup.setItemVisibilityChecked(False)  # Apagar el subgrupo
        subgroup.setExpanded(False)  # Contraer el subgrupo
        return subgroup

    def cargar_capa_procesada(self, gpkg_path, layer_name):
        uri = f"{gpkg_path}|layername={layer_name}"
        capa = QgsVectorLayer(uri, layer_name, "ogr")
        if not capa.isValid():
            self.log_callback(f"❌ Error: No se pudo cargar la capa procesada desde {gpkg_path}")
            return None
        return capa

    def generar_concave_hull(self, capa_puntos):
        params = {
            'INPUT': capa_puntos,
            'KNEIGHBORS': 15,
            'FIELD': '',
            'OUTPUT': 'memory:concave_hull'
        }
        try:
            result = processing.run("qgis:knearestconcavehull", params)
            fixed_poligono = processing.run("qgis:fixgeometries", {
                'INPUT': result['OUTPUT'],
                'OUTPUT': 'memory:fixgeometries'
            })['OUTPUT']
            return fixed_poligono
        except Exception as e:
            self.log_callback(f"❌ Error al generar Concave Hull: {e}")
            return None

    def generar_tin_recortado(self, puntos_layer, poligono, base, csv_path, triangulaciones_group):
        try:
            interpolation_string = f"{puntos_layer.source()}::~::1::~::-1::~::0"
            tin_params = {
                'INTERPOLATION_DATA': interpolation_string,
                'METHOD': 0,
                'EXTENT': puntos_layer.extent(),
                'PIXEL_SIZE': self.PIXEL_SIZE,  # Usar parámetro de la GUI
                'OUTPUT': 'memory:tin'
            }
            result = processing.run("qgis:tininterpolation", tin_params, feedback=QgsProcessingFeedback())
            output_path = result['OUTPUT']
            tin_layer_name = base
            tin_layer = QgsRasterLayer(output_path, tin_layer_name)
            if not tin_layer.isValid():
                self.log_callback(f"❌ Raster TIN inválido para {csv_path}")
                return
            
            extent = puntos_layer.extent()
            target_extent = f"{extent.xMinimum()},{extent.xMaximum()},{extent.yMinimum()},{extent.yMaximum()} [{self.CRS}]"
            clip_params = {
                'INPUT': output_path,
                'MASK': poligono,
                'SOURCE_CRS': QgsCoordinateReferenceSystem(self.CRS),
                'TARGET_CRS': QgsCoordinateReferenceSystem(self.CRS),
                'NODATA': None,
                'ALPHA_BAND': False,
                'CROP_TO_CUTLINE': True,
                'KEEP_RESOLUTION': True,
                'SET_RESOLUTION': False,
                'X_RESOLUTION': None,
                'Y_RESOLUTION': None,
                'DATA_TYPE': 0,
                'MULTITHREADING': False,
                'OPTIONS': '',
                'EXTRA': '',
                'TARGET_EXTENT': target_extent,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            }
            try:
                clip_result = processing.run("gdal:cliprasterbymasklayer", clip_params)
                clipped_tin_path = clip_result['OUTPUT']
                clipped_tin_layer = QgsRasterLayer(clipped_tin_path, base)
                if clipped_tin_layer.isValid():
                    project = QgsProject.instance()
                    project.addMapLayer(clipped_tin_layer, False)
                    node = triangulaciones_group.addLayer(clipped_tin_layer)
                    node.setItemVisibilityChecked(False)  # Apagar la capa
                    node.setExpanded(False)  # Contraer las bandas
                    self.log_callback(f"📐 TIN recortado agregado a Triangulaciones (apagado y contraído): {clipped_tin_layer.name()}")
                else:
                    self.log_callback(f"❌ Raster TIN recortado inválido para {csv_path}")
            except Exception as e:
                self.log_callback(f"❌ Error al recortar TIN para {csv_path}: {e}")
        except Exception as e:
            self.log_callback(f"❌ Error al generar TIN para {csv_path}: {e}")

    def obtener_valor_raster(self, raster_layer, punto, max_radio=1.0, pasos=10):
        prov = raster_layer.dataProvider()
        val = prov.identify(punto, QgsRaster.IdentifyFormatValue).results().get(1)
        if val is not None:
            return val
        # Buscar alrededor si no hay valor
        radios = [max_radio * (i + 1) / pasos for i in range(pasos)]
        angulos = [2 * math.pi * i / 8 for i in range(8)]
        for radio in radios:
            for ang in angulos:
                px = punto.x() + radio * math.cos(ang)
                py = punto.y() + radio * math.sin(ang)
                val = prov.identify(QgsPointXY(px, py), QgsRaster.IdentifyFormatValue).results().get(1)
                if val is not None:
                    return val
        return None

    def procesar_asc(self, asc_path, base, project, puntos_group, poligonos_group, triangulaciones_group):
        """
        Nuevo flujo ASC:
        - Carga el raster ASC y lo agrega solo a Triangulaciones.
        - Vectoriza, suaviza y extrae 4 vértices extremos, agregando el polígono suavizado
          al grupo Poligonos y los puntos extremos (con cota desde raster) al grupo Puntos.
        - Usa el nombre base del archivo para todas las capas.
        """
        if not os.path.exists(asc_path):
            self.log_callback(f"❌ No existe ASC procesado: {asc_path}")
            return
        
        # 1. Cargar raster ASC y agregar SOLO a Triangulaciones
        asc_layer_obj = QgsRasterLayer(asc_path, base)
        if asc_layer_obj.isValid():
            project.addMapLayer(asc_layer_obj, False)
            node = triangulaciones_group.addLayer(asc_layer_obj)
            node.setItemVisibilityChecked(False)  # Apagar la capa
            node.setExpanded(False)  # Contraer las bandas
            self.log_callback(f"🗺️ ASC agregado a Triangulaciones (apagado y contraído): {base}")
        else:
            self.log_callback(f"❌ ASC inválido: {asc_path}")
            return

        # 2. Vectorizar raster ASC a polígono
        result = processing.run("gdal:polygonize", {
            'INPUT': asc_layer_obj.dataProvider().dataSourceUri(),
            'BAND': 1,
            'FIELD': 'DN',
            'EIGHT_CONNECTEDNESS': False,
            'EXTRA': '',
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })
        vector_path = result['OUTPUT']
        poly_layer = QgsVectorLayer(vector_path, f"{base}_poly_raw", "ogr")
        no_data_value = asc_layer_obj.dataProvider().sourceNoDataValue(1)
        ids_eliminar = [f.id() for f in poly_layer.getFeatures() if f['DN'] == no_data_value or f['DN'] is None]
        if ids_eliminar:
            poly_layer.dataProvider().deleteFeatures(ids_eliminar)
            poly_layer.updateExtents()

        # 3. Disolver polígonos en uno solo
        dissolve_result = processing.run("native:dissolve", {
            'INPUT': poly_layer,
            'FIELD': [],
            'OUTPUT': 'memory:Poligono_Raster_Unido'
        })
        poligono_unido = dissolve_result['OUTPUT']

        # 4. Suavizar polígono usando parámetro de la GUI
        result_suavizado = processing.run("qgis:simplifygeometries", {
            'INPUT': poligono_unido,
            'METHOD': 0,     # Distance method
            'TOLERANCE': self.SUAVIZADO_TOLERANCE_ASC,  # Usar parámetro de la GUI
            'OUTPUT': 'memory:Poligono_Suavizado'
        })
        suavizado_layer = result_suavizado['OUTPUT']
        suavizado_layer.setName(base)
        project.addMapLayer(suavizado_layer, False)
        node = poligonos_group.addLayer(suavizado_layer)
        node.setItemVisibilityChecked(False)  # Apagar la capa
        self.log_callback(f"✔️ Polígono suavizado agregado a Poligonos (apagado): {base}")

        # 5. Extraer 4 vértices extremos y obtener cota desde raster
        def punto_distinto(base_pts, otros, min_dist=self.MIN_DIST_VERTICES_ASC):  # Usar parámetro de la GUI
            for pt in base_pts:
                if all(((pt.x()-o.x())**2 + (pt.y()-o.y())**2)**0.5 >= min_dist for o in otros):
                    return pt
            return base_pts[0]  # Si todos están cerca, devuelve el primero

        feature = next(suavizado_layer.getFeatures())
        geom = feature.geometry()
        if geom.isMultipart():
            polygon = geom.asMultiPolygon()[0][0]
        else:
            polygon = geom.asPolygon()[0]
        vertices = [QgsPointXY(pt) for pt in polygon]

        left_candidates = sorted(vertices, key=lambda p: p.x())
        left = punto_distinto(left_candidates, [], self.MIN_DIST_VERTICES_ASC)
        right_candidates = sorted(vertices, key=lambda p: -p.x())
        right = punto_distinto(right_candidates, [left], self.MIN_DIST_VERTICES_ASC)
        top_candidates = sorted(vertices, key=lambda p: -p.y())
        top = punto_distinto(top_candidates, [left, right], self.MIN_DIST_VERTICES_ASC)
        bottom_candidates = sorted(vertices, key=lambda p: p.y())
        bottom = punto_distinto(bottom_candidates, [left, right, top], self.MIN_DIST_VERTICES_ASC)
        extremos = [left, right, top, bottom]

        # Crear capa de puntos con campos estándar
        fields = [
            QgsField("field_1", QVariant.Int),
            QgsField("field_2", QVariant.Double),
            QgsField("field_3", QVariant.Double),
            QgsField("field_4", QVariant.Double),
            QgsField("field_5", QVariant.String),
        ]
        puntos_layer = QgsVectorLayer(
            "Point?crs=" + suavizado_layer.crs().authid(), base, "memory"
        )
        pr = puntos_layer.dataProvider()
        pr.addAttributes(fields)
        puntos_layer.updateFields()

        for idx, extremo in enumerate(extremos, 1):
            z = self.obtener_valor_raster(asc_layer_obj, extremo, max_radio=1.0)
            f = QgsFeature(puntos_layer.fields())
            # Limitar a 3 decimales
            f.setGeometry(QgsGeometry.fromPointXY(extremo))
            f.setAttribute("field_1", idx)
            f.setAttribute("field_2", round(extremo.y(), 3))  # Y
            f.setAttribute("field_3", round(extremo.x(), 3))  # X
            f.setAttribute("field_4", round(z, 3) if z is not None else -9999)  # Z
            f.setAttribute("field_5", base)
            pr.addFeature(f)
            self.log_callback(f"Extremo {idx}: ({round(extremo.x(),3)}, {round(extremo.y(),3)}, cota: {round(z,3) if z is not None else 'No encontrada'})")

        puntos_layer.updateExtents()
        project.addMapLayer(puntos_layer, False)
        node = puntos_group.addLayer(puntos_layer)
        node.setItemVisibilityChecked(False)  # Apagar la capa
        self.log_callback(f"✔️ Capa de puntos extremos agregada a Puntos (apagado): {base}")

    def procesar_csv(self, csv_path, base, project, puntos_group, poligonos_group, triangulaciones_group):
        uri = f"file:///{csv_path}?type=csv&delimiter={self.DELIMITER}&skipLines={self.SKIP_LINES}&useHeader={self.USE_HEADER}&maxFields=10000&detectTypes=yes&xField={self.X_FIELD}&yField={self.Y_FIELD}&zField={self.Z_FIELD}&crs={self.CRS}&spatialIndex=no&subsetIndex=no&watchFile=no"
        puntos_layer = QgsVectorLayer(uri, base, "delimitedtext")
        if not puntos_layer.isValid():
            self.log_callback(f"❌ Error: No se pudo cargar la capa de puntos desde {csv_path}")
            self.log_callback(f"   URI: {uri}")
            return

        # Agregar capa de puntos al subgrupo Puntos
        project.addMapLayer(puntos_layer, False)
        node = puntos_group.addLayer(puntos_layer)
        node.setItemVisibilityChecked(False)  # Apagar la capa
        self.log_callback(f"📍 Puntos agregados a la capa '{base}' en el grupo 'Puntos' (apagado)")

        # Generar Concave Hull y procesar si hay suficientes puntos
        if puntos_layer.featureCount() > 2:
            poligono = self.generar_concave_hull(puntos_layer)
            if poligono and poligono.featureCount() > 0:
                poligono.setName(base)
                project.addMapLayer(poligono, False)
                node = poligonos_group.addLayer(poligono)
                node.setItemVisibilityChecked(False)  # Apagar la capa
                self.log_callback(f"🗺️ ConcaveHull agregado a Poligonos (apagado): {base}")

                # Generar y recortar TIN
                self.generar_tin_recortado(puntos_layer, poligono, base, csv_path, triangulaciones_group)
            else:
                self.log_callback(f"❌ No se pudo generar ConcaveHull para CSV: {csv_path}")
        else:
            self.log_callback(f"❌ CSV no tiene suficientes puntos para ConcaveHull y TIN: {csv_path}")

    def generar_resumen_final(self, puntos_group, poligonos_group, triangulaciones_group, capa):
        """Generar resumen final del procesamiento - copiado del script original"""
        def contar_capas_en_subgrupo(subgroup, nombre):
            capas = [child.layer().name() for child in subgroup.children() if hasattr(child, 'layer') and child.layer() is not None]
            self.log_callback(f"Subgrupo '{nombre}': {len(capas)} capas")
            return set(capas)

        capas_puntos = contar_capas_en_subgrupo(puntos_group, "Puntos")
        capas_poligonos = contar_capas_en_subgrupo(poligonos_group, "Poligonos")
        capas_triangulaciones = contar_capas_en_subgrupo(triangulaciones_group, "Triangulaciones")

        # Listar filas esperadas según la capa Levantamientos
        nombres_esperados = set()
        for feat in capa.getFeatures():
            if feat["Procesado"] and feat["Validar info"]:
                base, ext = os.path.splitext(feat["NombreArchivo"])
                nombres_esperados.add(base)

        def debug_subgrupo(nombre_subgrupo, capas, nombres_esperados):
            faltantes = nombres_esperados - capas
            if faltantes:
                self.log_callback(f"⚠️ Faltan en '{nombre_subgrupo}': {faltantes}")
            else:
                self.log_callback(f"✔️ Todos los nombres presentes en '{nombre_subgrupo}'")

        debug_subgrupo("Puntos", capas_puntos, nombres_esperados)
        debug_subgrupo("Poligonos", capas_poligonos, nombres_esperados)
        debug_subgrupo("Triangulaciones", capas_triangulaciones, nombres_esperados)

    # =========================
    # MÉTODO PRINCIPAL
    # =========================

    def ejecutar_procesamiento_completo(self):
        """Ejecutar todo el proceso de procesamiento espacial - MÉTODO PRINCIPAL"""
        try:
            self.progress_callback(5, "Iniciando procesamiento espacial...")
            self.log_callback("⚙️ Generando grupo visual Procesamiento_Fecha en QGIS...")
            
            # Cargar capa procesada
            self.progress_callback(10, "Cargando capa de levantamientos procesada...")
            capa = self.cargar_capa_procesada(self.GPKG_PROC, self.NOMBRE_CAPA)
            if not capa:
                return {
                    'success': False,
                    'message': 'No se pudo cargar la capa de levantamientos procesada'
                }

            # Crear grupos
            self.progress_callback(20, "Creando estructura de grupos...")
            project = QgsProject.instance()
            fecha_proc = datetime.now().strftime("%y%m%d")
            group_name = f"Procesamiento_{fecha_proc}"
            group = self.get_or_create_group(project, group_name)
            puntos_group = self.get_or_create_subgroup(group, "Puntos")
            poligonos_group = self.get_or_create_subgroup(group, "Poligonos")
            triangulaciones_group = self.get_or_create_subgroup(group, "Triangulaciones")

            # Obtener archivos a procesar (igual que el script original)
            archivos_procesar = []
            for feat in capa.getFeatures():
                if feat["Procesado"] and feat["Validar info"]:
                    archivos_procesar.append({
                        'nombre': feat["NombreArchivo"],
                        'base': os.path.splitext(feat["NombreArchivo"])[0],
                        'ext': os.path.splitext(feat["NombreArchivo"])[1]
                    })

            total_archivos = len(archivos_procesar)
            if total_archivos == 0:
                return {
                    'success': False,
                    'message': 'No hay archivos procesados y validados para procesar'
                }

            self.log_callback(f"📊 Procesando {total_archivos} archivos...")
            archivos_procesados = 0

            # Procesar cada archivo (lógica del script original)
            for archivo in archivos_procesar:
                archivos_procesados += 1
                progreso = 20 + int((archivos_procesados / total_archivos) * 60)
                self.progress_callback(progreso, f"Procesando {archivo['nombre']}...")

                if archivo['ext'].lower() == ".asc":
                    asc_path = os.path.join(self.DIR_CSV_PROC, archivo['nombre'])
                    self.procesar_asc(asc_path, archivo['base'], project, puntos_group, poligonos_group, triangulaciones_group)
                elif archivo['ext'].lower() == ".csv":
                    csv_path = os.path.join(self.DIR_CSV_PROC, archivo['nombre'])
                    self.procesar_csv(csv_path, archivo['base'], project, puntos_group, poligonos_group, triangulaciones_group)

            # Apagar la capa Levantamientos (igual que el script original)
            self.progress_callback(85, "Organizando capas...")
            root = project.layerTreeRoot()
            levantamientos_node = root.findLayer(capa.id())
            if levantamientos_node:
                levantamientos_node.setItemVisibilityChecked(False)
                self.log_callback(f"✔️ Capa '{self.NOMBRE_CAPA}' apagada")
            else:
                self.log_callback(f"⚠️ No se encontró la capa '{self.NOMBRE_CAPA}' para apagar")

            self.log_callback("⚙️ Subgrupos creados: Puntos, Poligonos y Triangulaciones (todos apagados y contraídos)")

            # Generar resumen final (igual que el script original)
            self.progress_callback(90, "Generando resumen...")
            self.generar_resumen_final(puntos_group, poligonos_group, triangulaciones_group, capa)

            self.progress_callback(100, "¡Procesamiento completado!")
            self.log_callback("✅ Fin generación de grupo visual")

            return {
                'success': True,
                'message': f'Procesamiento completado exitosamente. {total_archivos} archivos procesados.',
                'total_archivos': total_archivos,
                'group_name': group_name
            }

        except Exception as e:
            import traceback
            error_msg = f"Error durante el procesamiento: {str(e)}"
            error_details = traceback.format_exc()
            self.log_callback(f"❌ {error_msg}")
            self.log_callback(f"📋 Detalles del error:\n{error_details}")
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }