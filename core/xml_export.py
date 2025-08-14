# -*- coding: utf-8 -*-
"""
/***************************************************************************
 XML export module for Canchas Las Tortolas plugin
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
Módulo de exportación XML para Canchas Las Tortolas
Adaptado del script standalone 3.4_XML.py - VERSIÓN COMPLETA
"""

import os
from datetime import datetime
import numpy as np
from qgis.core import (
    QgsProject, QgsMapLayer, QgsPointXY, QgsRaster, QgsRasterLayer, QgsVectorLayer
)
from scipy.spatial import Delaunay

class XMLExportProcessor:
    """Procesador de exportación XML completo - TODAS las funciones del script original"""
    
    def __init__(self, proc_root, swap_xy=True, raster_sample_step=2, 
                 progress_callback=None, log_callback=None):
        """
        Inicializar procesador con parámetros de la GUI
        
        Args:
            proc_root: Carpeta raíz de procesamiento (PROC_ROOT)
            swap_xy: Intercambiar coordenadas X-Y en la exportación (default True)
            raster_sample_step: Paso de muestreo para rasters ASC (default 2)
            progress_callback: Función callback para actualizar progreso
            log_callback: Función callback para logs
        """
        self.PROC_ROOT = proc_root
        self.CARPETA_XML = os.path.join(proc_root, "XML")
        
        # Parámetros configurables desde GUI
        self.swap_xy = swap_xy
        self.RASTER_SAMPLE_STEP = raster_sample_step
        
        # Callbacks
        self.progress_callback = progress_callback or (lambda x, msg="": None)
        self.log_callback = log_callback or (lambda msg: print(msg))
        
        # Constantes del script original
        self.NOMBRE_CAPA_LEVANTAMIENTOS = "Levantamientos"

    # ============================================================
    # FUNCIONES DE ÁREA Y RASTER DEL SCRIPT ORIGINAL
    # ============================================================

    def area_2d(self, triangle):
        p1, p2, p3 = triangle
        return 0.5 * abs((p2[0] - p1[0]) * (p3[1] - p1[1]) -
                         (p3[0] - p1[0]) * (p2[1] - p1[1]))

    def area_3d(self, triangle):
        a = triangle[1] - triangle[0]
        b = triangle[2] - triangle[0]
        return 0.5 * np.linalg.norm(np.cross(a, b))

    def muestrear_puntos_raster(self, raster_layer, step=1):
        provider = raster_layer.dataProvider()
        extent = raster_layer.extent()
        width = raster_layer.width()
        height = raster_layer.height()
        pixel_size_x = extent.width() / width
        pixel_size_y = extent.height() / height

        points = []
        for row in range(0, height, step):
            for col in range(0, width, step):
                x = extent.xMinimum() + (col + 0.5) * pixel_size_x
                y = extent.yMaximum() - (row + 0.5) * pixel_size_y
                ident = provider.identify(QgsPointXY(x, y), QgsRaster.IdentifyFormatValue)
                if ident.isValid():
                    vals = ident.results()
                    if vals:
                        z = list(vals.values())[0]
                        if z is not None and not np.isnan(z):
                            points.append([x, y, z])
        return points

    # ============================================================
    # FUNCIONES DE EXPORTACIÓN XML DEL SCRIPT ORIGINAL
    # ============================================================

    def generar_archivos_xml(self, levantamientos_layer, puntos_layers, raster_layers, csv_paths=None):
        self.log_callback("✔️ Iniciando generación de archivos XML...")
        
        # Asegurar que existe la carpeta XML
        if not os.path.exists(self.CARPETA_XML):
            try:
                os.makedirs(self.CARPETA_XML)
                self.log_callback(f"✔️ Carpeta creada: {self.CARPETA_XML}")
            except Exception as e:
                self.log_callback(f"❌ Error al crear la carpeta {self.CARPETA_XML}: {e}")
                return 0

        # Obtener lista de levantamientos a procesar
        levantamientos = list(levantamientos_layer.getFeatures())
        total_levantamientos = len(levantamientos)
        levantamientos_procesados = 0
        exitosos = 0

        for lev_feat in levantamientos:
            levantamientos_procesados += 1
            progreso = int((levantamientos_procesados / total_levantamientos) * 90) + 5  # 5-95%
            
            nombre_archivo = lev_feat["NombreArchivo"]
            base = os.path.splitext(os.path.basename(nombre_archivo))[0]
            
            self.progress_callback(progreso, f"Procesando {base}...")
            self.log_callback(f"🟢 Procesando levantamiento: {base} ({nombre_archivo})")
            
            archivo_xml = os.path.join(self.CARPETA_XML, f"{base}.xml")
            
            try:
                points = []
                
                # Procesar según tipo de archivo
                if nombre_archivo.lower().endswith(".csv"):
                    puntos_layer = puntos_layers.get(base)
                    if not puntos_layer:
                        self.log_callback(f"❌ No se encontró capa de puntos para {base}")
                        continue
                    
                    campo_cota = "field_4"
                    for i, feature in enumerate(puntos_layer.getFeatures(), 1):
                        geom = feature.geometry().asPoint()
                        try:
                            z = feature[campo_cota]
                            if z is not None:
                                if self.swap_xy:
                                    points.append([geom.y(), geom.x(), z])
                                else:
                                    points.append([geom.x(), geom.y(), z])
                        except KeyError:
                            self.log_callback(f"⚠️ El campo '{campo_cota}' no existe en la capa de puntos para {base}")
                            continue

                elif nombre_archivo.lower().endswith(".asc"):
                    raster_layer = raster_layers.get(base)
                    if not raster_layer:
                        self.log_callback(f"❌ No se encontró capa raster para {base}")
                        continue
                    
                    points = self.muestrear_puntos_raster(raster_layer, step=self.RASTER_SAMPLE_STEP)
                    if self.swap_xy:
                        points = [[p[1], p[0], p[2]] for p in points]

                else:
                    self.log_callback(f"❌ Archivo no reconocido: {nombre_archivo} (solo .csv o .asc)")
                    continue

                # Validar que tenemos suficientes puntos
                if len(points) < 3:
                    self.log_callback(f"❌ No se encontraron puntos suficientes para {base}")
                    continue

                # Convertir a numpy array y generar triangulación
                points = np.array(points)
                points_2d = points[:, :2]
                tri = Delaunay(points_2d)
                faces = tri.simplices

                # Debug: mostrar primeros puntos
                self.log_callback("Primeros 5 puntos a exportar (X Y Z):")
                for idx, pt in enumerate(points[:5]):
                    self.log_callback(f"Punto {idx+1}: X={pt[0]}, Y={pt[1]}, Z={pt[2]}")

                # Calcular áreas y elevaciones
                area2d = sum(self.area_2d(points[face, :2]) for face in faces)
                area3d = sum(self.area_3d(points[face]) for face in faces)
                elev_min = float(np.min(points[:, 2]))
                elev_max = float(np.max(points[:, 2]))

                # Generar XML
                success = self._generar_xml_landxml(base, points, faces, area2d, area3d, 
                                                  elev_min, elev_max, archivo_xml, csv_paths)
                if success:
                    exitosos += 1

            except Exception as e:
                self.log_callback(f"❌ Error al generar XML para {base}: {e}")

        self.log_callback(f"✔️ Generación de archivos XML completada: {exitosos}/{total_levantamientos} exitosos.")
        return exitosos

    def _generar_xml_landxml(self, base, points, faces, area2d, area3d, elev_min, elev_max, 
                           archivo_xml, csv_paths=None):
        """Generar el archivo XML en formato LandXML"""
        try:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            xml = []
            xml.append('<?xml version="1.0"?>')
            xml.append('<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                'xsi:schemaLocation="http://www.landxml.org/schema/LandXML-1.2 '
                'http://www.landxml.org/schema/LandXML-1.2/LandXML-1.2.xsd" '
                f'date="{date_str}" time="{time_str}" version="1.2" language="English" readOnly="false">')
            xml.append('    <Units>')
            xml.append('        <Metric areaUnit="squareMeter" linearUnit="meter" volumeUnit="cubicMeter" temperatureUnit="celsius" pressureUnit="milliBars" diameterUnit="millimeter" angularUnit="decimal degrees" directionUnit="decimal degrees"></Metric>')
            xml.append('    </Units>')
            xml.append(f'    <Project name="{base}"/>')
            xml.append(f'    <Application name="QGIS" desc="QGIS Processing" manufacturer="QGIS" version="3.28.9" manufacturerURL="www.qgis.org" timeStamp="{date_str}T{time_str}"/>')
            xml.append('    <Surfaces>')
            xml.append(f'        <Surface name="{base}" desc="{base}">')
            
            # SourceData section
            if csv_paths and base in csv_paths:
                xml.append('            <SourceData>')
                xml.append('                <PointFiles>')
                xml.append(f'                    <PointFile fileName="{csv_paths[base]}" fileType="binary" fileFormat="xyz"></PointFile>')
                xml.append('                </PointFiles>')
                xml.append('            </SourceData>')
            else:
                xml.append('            <SourceData/>')

            # Definition section
            xml.append(f'            <Definition surfType="TIN" area2DSurf="{area2d:.9f}" area3DSurf="{area3d:.9f}" elevMax="{elev_max:.3f}" elevMin="{elev_min:.3f}">')
            
            # Points section
            xml.append('                <Pnts>')
            for i, point in enumerate(points, 1):
                xml.append(f'                    <P id="{i}">{point[0]:.9f} {point[1]:.9f} {point[2]:.3f}</P>')
            xml.append('                </Pnts>')
            
            # Faces section
            xml.append('                <Faces>')
            for face in faces:
                xml.append(f'                    <F>{face[0]+1} {face[1]+1} {face[2]+1}</F>')
            xml.append('                </Faces>')
            
            xml.append('            </Definition>')
            xml.append('        </Surface>')
            xml.append('    </Surfaces>')
            xml.append('</LandXML>')

            # Escribir archivo
            with open(archivo_xml, 'w', encoding='utf-8') as f:
                f.write("\n".join(xml))

            # Verificar que se creó
            if os.path.exists(archivo_xml):
                self.log_callback(f"✔️ Archivo XML exportado para {base}: {archivo_xml}")
                return True
            else:
                self.log_callback(f"❌ Error: No se creó el archivo XML para {base}: Archivo no encontrado en disco")
                return False

        except Exception as e:
            self.log_callback(f"❌ Error al escribir XML para {base}: {e}")
            return False

    # ============================================================
    # MÉTODO PRINCIPAL
    # ============================================================

    def ejecutar_exportacion_xml_completa(self):
        """Ejecutar todo el proceso de exportación XML - MÉTODO PRINCIPAL"""
        try:
            self.progress_callback(5, "Iniciando exportación XML...")
            self.log_callback("📄 Iniciando exportación a LandXML...")

            # Asegurar que existe la carpeta XML
            if not os.path.exists(self.CARPETA_XML):
                os.makedirs(self.CARPETA_XML)
                self.log_callback(f"📁 Carpeta creada: {self.CARPETA_XML}")

            # Buscar la capa Levantamientos en el proyecto
            self.progress_callback(10, "Buscando capa de levantamientos...")
            project = QgsProject.instance()
            root = project.layerTreeRoot()

            levantamientos_layer = None
            for lyr in project.mapLayers().values():
                if lyr.name().lower() == self.NOMBRE_CAPA_LEVANTAMIENTOS.lower() and lyr.type() == QgsMapLayer.VectorLayer:
                    levantamientos_layer = lyr
                    break
            
            if not levantamientos_layer:
                # Listar capas disponibles para debug
                capas_disponibles = [lyr.name() for lyr in project.mapLayers().values()]
                return {
                    'success': False,
                    'message': f'No se encontró la capa vectorial "{self.NOMBRE_CAPA_LEVANTAMIENTOS}" en el proyecto.',
                    'capas_disponibles': capas_disponibles
                }

            # Buscar grupos de puntos y triangulaciones
            self.progress_callback(15, "Buscando grupos de procesamiento...")
            group = None
            for g in root.children():
                if g.nodeType() == 0 and g.name().startswith("Procesamiento_"):
                    group = g
                    break
            
            if not group:
                return {
                    'success': False,
                    'message': 'No se encontró ningún grupo que empiece con "Procesamiento_". Debe ejecutar el procesamiento espacial primero.'
                }

            def find_subgroup(parent, name):
                for g in parent.children():
                    if g.nodeType() == 0 and g.name().lower() == name.lower():
                        return g
                return None

            puntos_group = find_subgroup(group, "Puntos")
            raster_group = find_subgroup(group, "Triangulaciones")
            
            if not puntos_group or not raster_group:
                subgrupos_disponibles = [sg.name() for sg in group.children() if sg.nodeType() == 0]
                return {
                    'success': False,
                    'message': 'Subgrupos "Puntos" o "Triangulaciones" no encontrados.',
                    'subgrupos_disponibles': subgrupos_disponibles
                }

            # Obtener capas de puntos y rasters
            self.progress_callback(20, "Obteniendo capas de puntos y triangulaciones...")
            puntos_layers = {l.name(): l.layer() for l in puntos_group.findLayers() 
                           if l.layer().type() == QgsMapLayer.VectorLayer}
            raster_layers = {l.name(): l.layer() for l in raster_group.findLayers() 
                           if l.layer().type() == QgsMapLayer.RasterLayer}

            self.log_callback("Capas en Puntos: " + str(list(puntos_layers.keys())))
            self.log_callback("Capas en Triangulaciones: " + str(list(raster_layers.keys())))
            self.log_callback("Capa de levantamientos: " + levantamientos_layer.name())

            if not puntos_layers and not raster_layers:
                return {
                    'success': False,
                    'message': 'No se encontraron capas de puntos ni triangulaciones para exportar.'
                }

            # Generar archivos XML
            self.progress_callback(25, "Generando archivos XML...")
            csv_paths = {}  # Opcional, para referencias de archivos fuente
            
            exitosos = self.generar_archivos_xml(
                levantamientos_layer,
                puntos_layers,
                raster_layers,
                csv_paths=csv_paths
            )

            self.progress_callback(100, "¡Exportación XML completada!")

            total_levantamientos = levantamientos_layer.featureCount()
            return {
                'success': True,
                'message': f'Exportación XML completada exitosamente: {exitosos}/{total_levantamientos} archivos.',
                'archivos_exitosos': exitosos,
                'total_archivos': total_levantamientos,
                'carpeta_salida': self.CARPETA_XML
            }

        except Exception as e:
            import traceback
            error_msg = f"Error durante la exportación XML: {str(e)}"
            error_details = traceback.format_exc()
            self.log_callback(f"❌ {error_msg}")
            self.log_callback(f"📋 Detalles del error:\n{error_details}")
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }