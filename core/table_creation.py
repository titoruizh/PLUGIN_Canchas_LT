# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Table creation module for Canchas Las Tortolas plugin
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
Módulo de creación de tabla base para Canchas Las Tortolas
Adaptado del script standalone 3.1_Tabla.py - VERSIÓN COMPLETA
"""

import os
from datetime import datetime
import random
import math
import numpy as np
import processing
from qgis.core import (
    QgsProject, QgsField, QgsFields, QgsVectorLayer, QgsFeature,
    QgsPointXY, QgsGeometry, QgsWkbTypes, QgsMapLayer
)
from PyQt5.QtCore import QVariant
from qgis.utils import iface

class TableCreationProcessor:
    """Procesador de creación de tabla base completo - TODAS las funciones del script original"""
    
    def __init__(self, proc_root, protocolo_topografico_inicio=1, progress_callback=None, log_callback=None):
        """
        Inicializar procesador con parámetros de la GUI
        
        Args:
            proc_root: Carpeta raíz de procesamiento (PROC_ROOT)
            protocolo_topografico_inicio: Número inicial para protocolo (default 1)
            progress_callback: Función callback para actualizar progreso
            log_callback: Función callback para logs
        """
        self.PROC_ROOT = proc_root
        self.protocolo_topografico_inicio = protocolo_topografico_inicio
        
        # Callbacks
        self.progress_callback = progress_callback or (lambda x, msg="": None)
        self.log_callback = log_callback or (lambda msg: print(msg))
        
        # Constantes del script original
        self.NOMBRE_CAPA_LEVANTAMIENTOS = "Levantamientos"

    # ============================================================
    # FUNCIONES DE UTILIDAD DEL SCRIPT ORIGINAL
    # ============================================================
    
    def parsear_nombre_archivo(self, nombre):
        """
        Parsea el nombre del archivo y extrae metadata relevante.
        Espera nombres del tipo: fecha_muro_sector_relleno[_componentes_adicionales]
        Maneja nombres con 4 o más componentes, combinando los extras en el relleno.
        """
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

    def crear_tabla_base_datos(self):
        """
        Crea la capa de memoria 'Tabla Base Datos' con todos los campos necesarios en el orden especificado.
        Se agrega la columna 'N° Capas' al final.
        """
        fields = QgsFields()
        fields.append(QgsField("Protocolo Topografico", QVariant.String))
        fields.append(QgsField("Muro", QVariant.String))
        fields.append(QgsField("N° Laboratorio", QVariant.String))
        fields.append(QgsField("Fecha", QVariant.String))
        fields.append(QgsField("Sector", QVariant.String))
        fields.append(QgsField("Relleno", QVariant.String))
        for p in ["P1", "P2", "P3", "P4"]:
            fields.append(QgsField(f"{p}_ESTE", QVariant.Double))
            fields.append(QgsField(f"{p}_NORTE", QVariant.Double))
            fields.append(QgsField(f"{p}_COTA", QVariant.Double))
        fields.append(QgsField("Foto", QVariant.String))
        fields.append(QgsField("Plano", QVariant.String))
        fields.append(QgsField("Control Topográfico", QVariant.Bool))
        fields.append(QgsField("Operador", QVariant.String))
        fields.append(QgsField("Area", QVariant.Double))
        fields.append(QgsField("Cut", QVariant.Double))
        fields.append(QgsField("Fill", QVariant.Double))
        fields.append(QgsField("Espesor", QVariant.Double))
        fields.append(QgsField("Ancho", QVariant.Double))
        fields.append(QgsField("Largo", QVariant.Double))
        fields.append(QgsField("Espesor mínimo", QVariant.Double))
        fields.append(QgsField("Espesor máximo", QVariant.Double))
        fields.append(QgsField("Disciplina", QVariant.String))
        fields.append(QgsField("N° Capas", QVariant.String))  # Nueva columna al final

        tabla = QgsVectorLayer("None", "Tabla Base Datos", "memory")
        tabla.dataProvider().addAttributes(fields)
        tabla.updateFields()

        self.log_callback("✔️ Campos creados en 'Tabla Base Datos': " + str([field.name() for field in tabla.fields()]))

        return tabla

    def punto_mas_cercano(self, layer_pts, extremo):
        """
        Busca el punto más cercano a 'extremo' en la capa de puntos dada.
        """
        nearest = None
        min_dist = float("inf")
        for f in layer_pts.getFeatures():
            pt = f.geometry().asPoint()
            dist = extremo.distance(pt)
            if dist < min_dist:
                min_dist = dist
                nearest = f
        return nearest

    def analizar_poligono_tin(self, poligono_layer, tin_nuevo, tin_base, base):
        """
        Analiza el polígono y calcula área, ancho, largo.
        """
        poly_geom = next(poligono_layer.getFeatures()).geometry()
        extent = poly_geom.boundingBox()
        xmin, xmax, ymin, ymax = extent.xMinimum(), extent.xMaximum(), extent.yMinimum(), extent.yMaximum()

        tin_nuevo_extent = tin_nuevo.extent()
        tin_base_extent = tin_base.extent()
        if not extent.intersects(tin_nuevo_extent) or not extent.intersects(tin_base_extent):
            self.log_callback(f"❌ Los extents no se superponen para {base}")
            return None

        area_m2 = round(poly_geom.area(), 3)
        bbox = poly_geom.boundingBox()
        largo_bbox = round(max(bbox.width(), bbox.height()), 3)

        try:
            result = processing.run("qgis:minimumboundinggeometry", {
                'INPUT': poligono_layer,
                'TYPE': 3,
                'OUTPUT': 'memory:'
            })
            min_rect_layer = result['OUTPUT']
            min_rect_geom = next(min_rect_layer.getFeatures()).geometry()
            points = min_rect_geom.asPolygon()[0]

            def distancia(p1, p2):
                return math.hypot(p1.x() - p2.x(), p1.y() - p2.y())

            lados = [(i, distancia(points[i], points[i+1])) for i in range(4)]
            idx_largo = max(lados, key=lambda t: t[1])[0]
            p_start = points[idx_largo]
            p_end = points[(idx_largo+1)%4]
            vector_largo = QgsPointXY(p_end.x()-p_start.x(), p_end.y()-p_start.y())
            longitud = distancia(p_start, p_end)

            n_transectas = 50
            anchos = []
            for i in range(n_transectas+1):
                frac = i / n_transectas
                x_c = p_start.x() + vector_largo.x() * frac
                y_c = p_start.y() + vector_largo.y() * frac
                dx = -vector_largo.y()
                dy = vector_largo.x()
                norm = math.hypot(dx, dy)
                if norm == 0:
                    continue
                dx /= norm
                dy /= norm
                length_test = 10 * longitud
                p1t = QgsPointXY(x_c - dx * length_test, y_c - dy * length_test)
                p2t = QgsPointXY(x_c + dx * length_test, y_c + dy * length_test)
                line = QgsGeometry.fromPolylineXY([p1t, p2t])
                inter = poly_geom.intersection(line)
                if inter and not inter.isEmpty() and inter.type() == QgsWkbTypes.LineGeometry:
                    if inter.isMultipart():
                        lines = inter.asMultiPolyline()
                        for seg in lines:
                            if len(seg) >= 2:
                                anch = distancia(seg[0], seg[-1])
                                anchos.append(anch)
                    else:
                        line_points = inter.asPolyline()
                        if len(line_points) >= 2:
                            anch = distancia(line_points[0], line_points[-1])
                            anchos.append(anch)

            ancho_medio = round(sum(anchos) / len(anchos), 3) if anchos else None

            return {
                "Area": area_m2,
                "Ancho": ancho_medio,
                "Largo": largo_bbox
            }
        except Exception as e:
            self.log_callback(f"❌ Error al calcular dimensiones para {base}: {e}")
            return {
                "Area": area_m2,
                "Ancho": None,
                "Largo": largo_bbox
            }

    def obtener_info_levantamientos(self, nombre_archivo_base):
        """
        Busca el operador (responsable), método y N° Capas del levantamiento para el archivo base en la capa de levantamientos.
        Devuelve un diccionario con: operador, metodo, ncapas
        """
        project = QgsProject.instance()
        capa_levantamientos = None
        for l in project.mapLayers().values():
            if l.name() == self.NOMBRE_CAPA_LEVANTAMIENTOS:
                capa_levantamientos = l
                break
        if capa_levantamientos is None:
            return {"operador": "", "metodo": "", "ncapas": ""}
        
        idx_nombre = capa_levantamientos.fields().indexFromName("NombreArchivo")
        idx_operador = capa_levantamientos.fields().indexFromName("Responsable")
        idx_metodo = capa_levantamientos.fields().indexFromName("Método")
        idx_ncapas = capa_levantamientos.fields().indexFromName("N° Capas")
        
        for f in capa_levantamientos.getFeatures():
            nombre_archivo = f[idx_nombre]
            if nombre_archivo:
                base_archivo, _ = os.path.splitext(nombre_archivo)
                if base_archivo == nombre_archivo_base:
                    return {
                        "operador": f[idx_operador],
                        "metodo": f[idx_metodo],
                        "ncapas": f[idx_ncapas]
                    }
        return {"operador": "", "metodo": "", "ncapas": ""}

    def extraer_vertices_extremos(self, layer_pts, poligono_layer, nombre_base, nombre_foto, tabla_resultados, 
                                 operador_value, metodo_value, ncapas_value, tin_nuevo, tin_base, campo_cota, protocolo_topografico_val):
        """
        Extrae los vértices extremos del polígono y los agrega a la tabla de resultados.
        El valor 'protocolo_topografico_val' es un número incremental inicializado por el usuario.
        """
        try:
            poly_geom = next(poligono_layer.getFeatures()).geometry()
            if poly_geom.isMultipart():
                polygon = poly_geom.asMultiPolygon()[0][0]
            else:
                polygon = poly_geom.asPolygon()[0]

            vertices = [QgsPointXY(pt) for pt in polygon]

            left = min(vertices, key=lambda p: p.x())
            right = max(vertices, key=lambda p: p.x())
            top = max(vertices, key=lambda p: p.y())
            bottom = min(vertices, key=lambda p: p.y())

            extremos = {
                "P1": left,
                "P2": right,
                "P3": top,
                "P4": bottom
            }

            datos_extremos = {}
            for p, extremo in extremos.items():
                nearest = self.punto_mas_cercano(layer_pts, extremo)
                if nearest:
                    geom = nearest.geometry().asPoint()
                    este = round(geom.x(), 3)
                    norte = round(geom.y(), 3)
                    cota = round(nearest[campo_cota], 3) if nearest[campo_cota] is not None else None
                    datos_extremos[p] = (este, norte, cota)
                else:
                    datos_extremos[p] = (None, None, None)

            resultados_analisis = self.analizar_poligono_tin(poligono_layer, tin_nuevo, tin_base, nombre_base)

            datos_nombre = self.parsear_nombre_archivo(nombre_base)

            try:
                f = QgsFeature(tabla_resultados.fields())
                f.setAttribute("Protocolo Topografico", str(protocolo_topografico_val))  # Asignar número incremental
                f.setAttribute("Muro", datos_nombre["Muro"])
                f.setAttribute("N° Laboratorio", "")
                f.setAttribute("Fecha", datos_nombre["Fecha"])
                f.setAttribute("Sector", datos_nombre["Sector"])
                f.setAttribute("Relleno", datos_nombre["Relleno"])

                for p, (este, norte, cota) in datos_extremos.items():
                    f.setAttribute(f"{p}_ESTE", este)
                    f.setAttribute(f"{p}_NORTE", norte)
                    f.setAttribute(f"{p}_COTA", cota)

                f.setAttribute("Foto", f"F{nombre_foto}")
                f.setAttribute("Plano", f"P{nombre_foto}")
                f.setAttribute("Control Topográfico", True)
                f.setAttribute("Operador", operador_value)
                f.setAttribute("Cut", None)
                f.setAttribute("Fill", None)
                f.setAttribute("Espesor", None)
                f.setAttribute("Disciplina", metodo_value if metodo_value is not None else "")
                if resultados_analisis:
                    f.setAttribute("Area", resultados_analisis["Area"])
                    f.setAttribute("Ancho", resultados_analisis["Ancho"])
                    f.setAttribute("Largo", resultados_analisis["Largo"])
                    f.setAttribute("Espesor mínimo", None)
                    f.setAttribute("Espesor máximo", None)
                else:
                    f.setAttribute("Area", None)
                    f.setAttribute("Ancho", None)
                    f.setAttribute("Largo", None)
                    f.setAttribute("Espesor mínimo", None)
                    f.setAttribute("Espesor máximo", None)

                f.setAttribute("N° Capas", ncapas_value if ncapas_value is not None else "")

                tabla_resultados.dataProvider().addFeature(f)
                self.log_callback(f"✔️ Feature agregado a la tabla para {nombre_base}")
            except Exception as e:
                self.log_callback(f"❌ Error al establecer atributos para {nombre_base}: {e}")
                return

        except Exception as e:
            self.log_callback(f"❌ Error procesando vértices para {nombre_base}: {e}")
            return

    def actualizar_tabla_plano(self, tabla, base, nombre_imagen):
        """
        Actualiza el campo 'Plano' en la tabla para la fila correspondiente al archivo base.
        """
        try:
            for feature in tabla.getFeatures():
                if feature["Foto"] == f"F{base}":
                    feature["Plano"] = f"P{base}"
                    tabla.dataProvider().changeAttributeValues({feature.id(): {tabla.fields().indexFromName("Plano"): f"P{base}"}})
                    tabla.updateFeature(feature)
                    self.log_callback(f"✔️ Campo 'Plano' actualizado para {base}")
                    break
            else:
                self.log_callback(f"⚠️ No se encontró feature con Foto=F{base} en la tabla")
        except Exception as e:
            self.log_callback(f"❌ Error al actualizar campo 'Plano' para {base}: {e}")

    # ============================================================
    # MÉTODO PRINCIPAL
    # ============================================================

    def ejecutar_creacion_tabla_completa(self):
        """Ejecutar todo el proceso de creación de tabla - MÉTODO PRINCIPAL"""
        try:
            self.progress_callback(5, "Iniciando creación de tabla base...")
            self.log_callback("📋 Iniciando creación de Tabla Base Datos...")

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
            puntos_group = group.findGroup("Puntos")
            poligonos_group = group.findGroup("Poligonos")
            triangulaciones_group = group.findGroup("Triangulaciones")
            if not puntos_group or not poligonos_group or not triangulaciones_group:
                return {
                    'success': False,
                    'message': 'Subgrupos "Puntos", "Poligonos" o "Triangulaciones" no encontrados.'
                }

            # Obtener capas de los subgrupos
            self.progress_callback(20, "Obteniendo capas de subgrupos...")
            puntos_layers = {l.name(): l.layer() for l in puntos_group.findLayers() if l.layer().type() == QgsMapLayer.VectorLayer}
            poligonos_layers = {l.name(): l.layer() for l in poligonos_group.findLayers() if l.layer().type() == QgsMapLayer.VectorLayer}
            triangulaciones_layers = {l.name(): l.layer() for l in triangulaciones_group.findLayers() if l.layer().type() == QgsMapLayer.RasterLayer}

            self.log_callback("Capas en Puntos: " + str(list(puntos_layers.keys())))
            self.log_callback("Capas en Poligonos: " + str(list(poligonos_layers.keys())))
            self.log_callback("Capas en Triangulaciones: " + str(list(triangulaciones_layers.keys())))

            if not poligonos_layers:
                return {
                    'success': False,
                    'message': 'No se encontraron capas de polígonos para procesar.'
                }

            # Mapeo de DEMs
            dem_map = {"MP": "DEM_MP", "MO": "DEM_MO", "ME": "DEM_ME"}

            # Crear tabla base
            self.progress_callback(30, "Creando estructura de tabla...")
            tabla = self.crear_tabla_base_datos()

            # Procesar cada capa
            protocolo_val = self.protocolo_topografico_inicio
            total_capas = len(poligonos_layers)
            capas_procesadas = 0

            for base in sorted(poligonos_layers):
                capas_procesadas += 1
                progreso = 30 + int((capas_procesadas / total_capas) * 50)
                self.progress_callback(progreso, f"Procesando {base}...")

                poligono_layer = poligonos_layers[base]
                
                # Verificar que existan capas correspondientes
                if base not in puntos_layers:
                    self.log_callback(f"⚠️ No hay capa de puntos para {base}")
                    continue
                if base not in triangulaciones_layers:
                    self.log_callback(f"⚠️ No hay capa de triangulación para {base}")
                    continue
                
                puntos_layer = puntos_layers[base]
                tin_nuevo = triangulaciones_layers[base]

                # Buscar DEM correspondiente
                datos_nombre = self.parsear_nombre_archivo(base)
                muro_code = datos_nombre["Muro_Code"].upper()  # Convertir a mayúsculas
                dem_name = dem_map.get(muro_code)
                tin_base = None
                if dem_name:
                    for layer in project.mapLayers().values():
                        if layer.name() == dem_name:
                            tin_base = layer
                            break
                if not tin_base:
                    self.log_callback(f"⚠️ No se encontró DEM para el muro {muro_code} ({base})")
                    continue

                # Obtener información de levantamientos
                info_lev = self.obtener_info_levantamientos(base)
                operador_value = info_lev["operador"]
                metodo_value = info_lev["metodo"]
                ncapas_value = info_lev["ncapas"]

                # Extraer vértices extremos y agregar a tabla
                self.extraer_vertices_extremos(
                    puntos_layer, poligono_layer, base, base, tabla, operador_value,
                    metodo_value, ncapas_value, tin_nuevo, tin_base, "field_4", protocolo_val
                )
                protocolo_val += 1  # Incrementa para la siguiente fila

                # Actualizar campo plano
                nombre_imagen = f"P{base}"
                self.actualizar_tabla_plano(tabla, base, nombre_imagen)

                self.log_callback(f"✔️ Procesamiento de tabla completado para {base}")

            # Agregar tabla al proyecto
            self.progress_callback(85, "Agregando tabla al proyecto...")
            project.addMapLayer(tabla, False)
            root.insertLayer(0, tabla)
            
            self.progress_callback(100, "¡Tabla creada exitosamente!")
            self.log_callback("✔️ Tabla 'Tabla Base Datos' creada y agregada al proyecto.")

            return {
                'success': True,
                'message': f'Tabla creada exitosamente con {capas_procesadas} registros.',
                'tabla_nombre': 'Tabla Base Datos',
                'registros_creados': capas_procesadas
            }

        except Exception as e:
            import traceback
            error_msg = f"Error durante la creación de tabla: {str(e)}"
            error_details = traceback.format_exc()
            self.log_callback(f"❌ {error_msg}")
            self.log_callback(f"📋 Detalles del error:\n{error_details}")
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }