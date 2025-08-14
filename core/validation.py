# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Validation module for Canchas Las Tortolas plugin
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
Módulo de validación completa para Canchas Las Tortolas
Adaptado del script standalone 1_Validacion.py - VERSIÓN COMPLETA
"""

import os
import shutil
from datetime import datetime
from collections import Counter
import pandas as pd
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsVectorLayer, QgsProject, QgsGeometry, QgsPointXY, QgsFeatureRequest, 
    QgsField, QgsFeature, QgsRaster, QgsRasterLayer
)
import processing
import tempfile
import time
import re

class ValidationProcessor:
    """Procesador de validación completa - TODAS las funciones del script original"""
    
    def __init__(self, proc_root, orig_gpkg, dir_csv_orig, dir_img_orig, progress_callback=None, log_callback=None):
        """Inicializar procesador con rutas de la GUI"""
        self.PROC_ROOT = proc_root
        self.ORIG_GPKG = orig_gpkg
        self.DIR_CSV_ORIG = dir_csv_orig
        self.DIR_IMG_ORIG = dir_img_orig
        
        # Carpetas derivadas
        self.DIR_CSV_PROC = os.path.join(proc_root, "CSV-ASC")
        self.DIR_IMG_PROC = os.path.join(proc_root, "IMAGENES")
        self.TMP_GPKG = os.path.join(proc_root, "Levantamientos.gpkg")
        self.CARPETA_BACKUP = os.path.join(proc_root, "backups")
        
        # Callbacks
        self.progress_callback = progress_callback or (lambda x, msg="": None)
        self.log_callback = log_callback or (lambda msg: print(msg))
        
        # Constantes del script original
        self.NOMBRE_CAPA = "Levantamientos"
        self.COLUMNA_NOMBRE = "NombreArchivo"
        self.COLUMNA_VALIDAR = "Validar info"
        self.COLUMNA_COMENTARIOS = "Validar info Comentarios"
        self.COLUMNA_PROCESADO = "Procesado"
        self.COLUMNA_FOTO = "FOTO"
        self.COLUMNAS_REQUERIDAS = ["id", "norte", "este", "cota", "descripcion"]
        self.CRS_EPSG = "EPSG:32719"

    # =========================
    # UTILIDADES GENERALES
    # =========================
    
    def limpiar_nombre(self, nombre):
        """Quita puntos finales, espacios y puntos consecutivos del nombre base."""
        return re.sub(r'\.+', '.', nombre.strip()).rstrip('.').strip()

    def actualizar_nombre_archivo(self, nombre_original, nuevo_muro=None, nuevo_sector=None):
        base, ext = os.path.splitext(nombre_original)
        partes = base.split('_')
        if len(partes) < 3:
            return self.limpiar_nombre(nombre_original)
        if nuevo_muro:
            partes[1] = nuevo_muro
        if nuevo_sector:
            partes[2] = f'S{nuevo_sector}' if not str(nuevo_sector).startswith('S') else str(nuevo_sector)
        nuevo_nombre = '_'.join(partes)
        nuevo_nombre = self.limpiar_nombre(nuevo_nombre) + ext
        return nuevo_nombre

    def asegurar_carpetas(self):
        for d in (self.DIR_CSV_PROC, self.DIR_IMG_PROC, self.CARPETA_BACKUP):
            os.makedirs(d, exist_ok=True)

    def respaldo_completo(self):
        fecha = datetime.now().strftime("%Y_%m_%d")
        carpeta_b = os.path.join(self.CARPETA_BACKUP, f"backup_{fecha}")
        os.makedirs(carpeta_b, exist_ok=True)
        
        if os.path.exists(self.DIR_CSV_ORIG):
            for f in os.listdir(self.DIR_CSV_ORIG):
                shutil.copy2(os.path.join(self.DIR_CSV_ORIG, f), carpeta_b)
        
        if os.path.exists(self.DIR_IMG_ORIG):
            for f in os.listdir(self.DIR_IMG_ORIG):
                shutil.copy2(os.path.join(self.DIR_IMG_ORIG, f), carpeta_b)
        
        if os.path.exists(self.ORIG_GPKG):
            shutil.copy2(self.ORIG_GPKG, carpeta_b)
        
        self.log_callback(f"📦 Backup completo creado en: {carpeta_b}")
        return carpeta_b

    def respaldar_archivo(self, path, carpeta_b):
        try:
            shutil.copy2(path, carpeta_b)
        except Exception as e:
            self.log_callback(f"⚠️ No se pudo respaldar {path}: {e}")

    # =========================
    # FUNCIONES DE PROCESAMIENTO CSV
    # =========================

    def leer_archivo_flexible(self, path):
        ext = os.path.splitext(path)[1].lower()
        df = None
        if ext in ['.xlsx', '.xls']:
            try:
                with pd.ExcelFile(path, engine="openpyxl") as xl:
                    df_xl = pd.read_excel(xl, header=None, dtype=str)
                if df_xl.shape[1] == 1:
                    df_expanded = df_xl[0].str.split(',', expand=True)
                    if df_expanded.shape[1] >= 5:
                        df = df_expanded
                    else:
                        return None
                elif df_xl.shape[1] >= 5:
                    df = df_xl
                else:
                    return None
            except Exception:
                return None
        else:
            for sep in [';', '\t', ',']:
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        df_tmp = pd.read_csv(f, sep=sep, header=None, dtype=str, engine="python")
                    if df_tmp.shape[1] >= 5:
                        df = df_tmp
                        break
                except Exception:
                    continue
        
        if df is None:
            return None

        header_keywords = {"id", "norte", "este", "cota", "desc", "descripcion", "x", "y", "z"}
        primera_fila = df.iloc[0].astype(str).str.lower()
        n_no_num = sum([not val.replace('.', '', 1).isdigit() for val in primera_fila[:4]])
        if (
            n_no_num >= 2
            or any(any(k in str(cell) for k in header_keywords) for cell in primera_fila)
        ):
            df = df.iloc[1:].reset_index(drop=True)

        df.columns = self.COLUMNAS_REQUERIDAS
        # Eliminar filas donde la columna 'descripcion' contiene 'inf' (case-insensitive)
        if not df.empty:
            df = df[~df['descripcion'].str.lower().str.contains('inf', na=False)].reset_index(drop=True)
            if df.empty:
                self.log_callback(f"⚠️ Todas las filas en {path} contenían 'inf' en la columna 'descripcion'. DataFrame vacío.")
        return df

    def validar_numeros(self, df):
        for _, f in df.iterrows():
            if not (f['norte'].split('.')[0].isdigit() and len(f['norte'].split('.')[0])==7): 
                return False
            if not (f['este'].split('.')[0].isdigit() and len(f['este'].split('.')[0])==6): 
                return False
            if not (f['cota'].split('.')[0].isdigit() and len(f['cota'].split('.')[0])==3): 
                return False
        return True

    def invertir_columnas(self, df):
        df = df.copy()
        df['norte'], df['este'] = df['este'], df['norte']
        return df

    def extraer_estructura_base(self, desc):
        if not isinstance(desc, str): 
            return None
        partes = desc.split('/')
        for i in range(len(partes)-1, -1, -1):
            if partes[i].startswith('m'):
                return '/'.join(partes[:i])
        return '/'.join(partes[:-1])

    def csv_a_capa_puntos(self, df, nombre="input_points"):
        uri = f"Point?crs={self.CRS_EPSG}"
        vl = QgsVectorLayer(uri, nombre, "memory")
        pr = vl.dataProvider()
        pr.addAttributes([
            QgsField("id", QVariant.Int),
            QgsField("cota", QVariant.Double),
            QgsField("descripcion", QVariant.String)
        ])
        vl.updateFields()
        feats = []
        for ix, row in df.iterrows():
            try:
                x = float(row["este"])
                y = float(row["norte"])
                f = QgsFeature(vl.fields())
                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
                f["id"] = int(row["id"])
                f["cota"] = float(row["cota"])
                f["descripcion"] = row["descripcion"]
                feats.append(f)
            except Exception as e:
                self.log_callback(f"Error en fila {ix}: {e}")
        pr.addFeatures(feats)
        vl.updateExtents()
        return vl

    def generar_concave_hull(self, capa_puntos, alpha=1.0):
        params = {
            'INPUT': capa_puntos,
            'ALPHA': alpha,
            'HOLES': False,
            'NO_MULTIGEOMETRY': False,
            'OUTPUT': 'memory:'
        }
        result = processing.run("native:concavehull", params)
        return result['OUTPUT']

    def validar_concavehull(self, poligono, capa_muros, capa_sectores):
        poly_feat = next(poligono.getFeatures(), None)
        if poly_feat is None:
            return {"muros": [], "sectores": []}
        poly_geom = poly_feat.geometry()
        muros_ok = []
        sectores_ok = []
        for feat in capa_muros.getFeatures():
            if poly_geom.intersects(feat.geometry()):
                muros_ok.append(feat["NAME"])
        for feat in capa_sectores.getFeatures():
            if poly_geom.intersects(feat.geometry()):
                sectores_ok.append(feat["NAME"])
        return {"muros": muros_ok, "sectores": sectores_ok}

    def comparar_cota_dem(self, capa_puntos, dem_layer, tolerancia=15):
        prov = dem_layer.dataProvider()
        fuera = []
        for f in capa_puntos.getFeatures():
            pt = f.geometry().asPoint()
            res = prov.identify(QgsPointXY(pt.x(), pt.y()), QgsRaster.IdentifyFormatValue)
            val = res.results().get(1)
            if val is not None:
                diff = abs(f["cota"]-val)
                if diff > tolerancia:
                    fuera.append({"id": f["id"], "cota": f["cota"], "dem": val, "diff": diff})
        return fuera

    def validar_filas(self, df, archivo, fid, capa):
        comentarios = []
        if not self.validar_numeros(df):
            inv = self.invertir_columnas(df)
            if self.validar_numeros(inv):
                df = inv
                comentarios.append('Coordenadas invertidas corregidas')
            else:
                return {"ok":False,"comentarios":["Error en columna Norte"],
                        "coordenadas":df,"muro":None,"sector":None}
        
        f = next(capa.getFeatures(QgsFeatureRequest(fid)))
        muro, sector = f['Muro'], f['Sector']
        pts = [QgsGeometry.fromPointXY(QgsPointXY(float(r['este']),float(r['norte'])))
               for _,r in df.iterrows()]
        
        try:
            capa_pol = QgsProject.instance().mapLayersByName('Poligonos')[0]
            detectados = [
                next((str(p['NAME']).upper() for p in capa_pol.getFeatures() if pt.within(p.geometry())),None)
                for pt in pts
            ]
            otros = [d for d in detectados if d in ['MP','ME','MO'] and d!=muro]
            nuevo_muro = Counter(otros).most_common(1)[0][0] if otros else muro
            if nuevo_muro!=muro:
                comentarios.append(f"Muro corregido: {muro} -> {nuevo_muro}")
            
            capa_sec = QgsProject.instance().mapLayersByName('Poligonos_Sectores')[0]
            cont = Counter()
            for pt in pts:
                for p in capa_sec.getFeatures():
                    if pt.within(p.geometry()) and str(p['NAME']).upper().startswith(nuevo_muro+'_'):
                        cont[str(p['NAME']).upper().split('_')[1]]+=1
                        break
            if cont:
                top,ct = cont.most_common(1)[0]
                if ct/len(pts)>=0.6 and top!=sector:
                    comentarios.append(f"Sector corregido: {sector} -> {top}")
                    sector = top
            
            dem = QgsProject.instance().mapLayersByName(f"DEM_{nuevo_muro}")[0]
            prov = dem.dataProvider()
            for _,r in df.iterrows():
                pt = QgsPointXY(float(r['este']),float(r['norte']))
                res = prov.identify(pt, QgsRaster.IdentifyFormatValue)
                val = res.results().get(1)
                if val is not None and abs(float(r['cota'])-val)>15:
                    return {"ok":False,
                            "comentarios":[f"Cota fuera de DEM (>15m): diff={abs(float(r['cota'])-val):.2f}"],
                            "coordenadas":df,"muro":nuevo_muro,"sector":sector}
        except Exception as e:
            self.log_callback(f"⚠️ Error en validación espacial: {e}")
            
        return {"ok":True,
                "comentarios":comentarios if comentarios else ["OK"],
                "coordenadas":df,"muro":nuevo_muro,"sector":sector}

    # =========================
    # PROCESAMIENTO DE CSV Y ASC
    # =========================

    def procesar_csv_valido(self, capa, fid, arc, ext, ruta_csv, carpeta_b, idx_v, idx_c,
                           idx_proc, idx_nom, idx_foto, df_corr, res, comentarios_extra=None):
        max_attempts = 5
        delay = 1
        rell = capa.getFeature(fid)["Relleno"].replace(" ", "").upper()
        nombre_original = os.path.basename(ruta_csv)
        if nombre_original.startswith("ARCHIVOS_NUBE/CSV-ASC/"):
            nombre_original = nombre_original.replace("ARCHIVOS_NUBE/CSV-ASC/", "")

        # Usar extensión .csv para archivos xlsx/xls
        ext_final = ".csv" if ext.lower() in [".xlsx", ".xls"] else ext

        nuevo_nombre_archivo = self.actualizar_nombre_archivo(
            nombre_original,
            nuevo_muro=res.get('muro'),
            nuevo_sector=res.get('sector')
        )
        nuevo_nombre_archivo = self.limpiar_nombre(os.path.splitext(nuevo_nombre_archivo)[0]) + ext_final

        self.respaldar_archivo(ruta_csv, carpeta_b)

        if df_corr is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8", newline="") as tmpfile:
                df_corr.to_csv(tmpfile, sep=';', header=False, index=False)
                tmp_csv_path = tmpfile.name
            ruta_a_copiar = tmp_csv_path
        else:
            ruta_a_copiar = ruta_csv

        dst_csv = os.path.join(self.DIR_CSV_PROC, nuevo_nombre_archivo)

        for attempt in range(max_attempts):
            try:
                shutil.copy2(ruta_a_copiar, dst_csv)
                self.log_callback(f"🗃️ CSV copiado a procesados: {dst_csv}")
                break
            except PermissionError as e:
                if attempt < max_attempts - 1:
                    self.log_callback(f"⚠️ Intento {attempt + 1} fallido: {e}. Reintentando en {delay} segundos...")
                    time.sleep(delay)
                else:
                    self.log_callback(f"❌ Error: No se pudo copiar {ruta_a_copiar} después de {max_attempts} intentos.")
                    raise

        base_arc_limpio = self.limpiar_nombre(os.path.splitext(arc)[0])
        base_nuevo_nombre_limpio = self.limpiar_nombre(os.path.splitext(nuevo_nombre_archivo)[0])
        
        orig_jpg = os.path.join(self.DIR_IMG_ORIG, base_arc_limpio + ".jpg")
        if os.path.exists(orig_jpg):
            self.respaldar_archivo(orig_jpg, carpeta_b)
            dst_jpg = os.path.join(self.DIR_IMG_PROC, f"F{base_nuevo_nombre_limpio}.jpg")
            shutil.copy2(orig_jpg, dst_jpg)
            self.log_callback(f"🖼️ JPG copiado a procesados: {dst_jpg}")

        comentarios_final = res["comentarios"].copy()
        if comentarios_extra:
            comentarios_final += comentarios_extra

        capa.changeAttributeValue(fid, idx_v, 1)
        capa.changeAttributeValue(fid, idx_c, ";".join(comentarios_final).replace(";", ","))
        capa.changeAttributeValue(fid, idx_proc, True)
        capa.changeAttributeValue(fid, capa.fields().indexOf('Muro'), res['muro'])
        capa.changeAttributeValue(fid, capa.fields().indexOf('Sector'), res['sector'])
        capa.changeAttributeValue(fid, idx_nom, nuevo_nombre_archivo)
        capa.changeAttributeValue(fid, idx_foto, f"F{base_nuevo_nombre_limpio}.jpg")

    def marcar_csv_invalido(self, capa, fid, arc, idx_v, idx_c, idx_proc, coms="Archivo invalido"):
        self.log_callback(f"❌ CSV inválido: {arc}")
        capa.changeAttributeValue(fid, idx_v, 0)
        capa.changeAttributeValue(fid, idx_c, coms)
        capa.changeAttributeValue(fid, idx_proc, True)

    def procesar_archivo_asc_validacion(self, capa, fid, arc, ruta_asc, carpeta_b, idx_v, idx_c, idx_proc,
                                       capa_muros=None, capa_sectores=None, DEMS=None,
                                       tolerancia_cota=20, area_min_valido=10):
        """Procesa y valida espacialmente un archivo .asc"""
        self.respaldar_archivo(ruta_asc, carpeta_b)
        arc_limpio = self.limpiar_nombre(os.path.splitext(arc)[0]) + ".asc"
        dst_asc = os.path.join(self.DIR_CSV_PROC, arc_limpio)
        shutil.copy2(ruta_asc, dst_asc)

        # Eliminar archivo auxiliar innecesario si se generó
        aux_xml = dst_asc + ".aux.xml"
        if os.path.exists(aux_xml):
            try:
                os.remove(aux_xml)
                self.log_callback(f"🧹 Archivo auxiliar eliminado: {aux_xml}")
            except Exception as e:
                self.log_callback(f"⚠️ No se pudo eliminar {aux_xml}: {e}")

        base_arc_limpio = self.limpiar_nombre(os.path.splitext(arc)[0])
        orig_jpg = os.path.join(self.DIR_IMG_ORIG, base_arc_limpio + ".jpg")
        if os.path.exists(orig_jpg):
            self.respaldar_archivo(orig_jpg, carpeta_b)
            dst_jpg = os.path.join(self.DIR_IMG_PROC, f"F{base_arc_limpio}.jpg")
            shutil.copy2(orig_jpg, dst_jpg)
            self.log_callback(f"🖼️ JPG copiado a procesados (ASC): {dst_jpg}")

        raster_layer = QgsRasterLayer(dst_asc, base_arc_limpio)
        if not raster_layer.isValid():
            msg = "Archivo .asc inválido (no se pudo cargar raster)"
            self.log_callback(f"❌ {msg}: {arc}")
            capa.changeAttributeValue(fid, idx_v, 0)
            capa.changeAttributeValue(fid, idx_c, msg)
            capa.changeAttributeValue(fid, idx_proc, True)
            return

        try:
            poly_result = processing.run("gdal:polygonize", {
                'INPUT': raster_layer.dataProvider().dataSourceUri(),
                'BAND': 1,
                'FIELD': 'DN',
                'EIGHT_CONNECTEDNESS': False,
                'EXTRA': '',
                'OUTPUT': 'TEMPORARY_OUTPUT'
            })
            poly_layer_path = poly_result['OUTPUT']
            poly_layer = QgsVectorLayer(poly_layer_path, "poly_from_asc", "ogr")
            if not poly_layer.isValid():
                msg = "Archivo .asc inválido (no se pudo cargar capa vectorizada)"
                self.log_callback(f"❌ {msg}: {arc}")
                capa.changeAttributeValue(fid, idx_v, 0)
                capa.changeAttributeValue(fid, idx_c, msg)
                capa.changeAttributeValue(fid, idx_proc, True)
                return

            no_data = raster_layer.dataProvider().sourceNoDataValue(1)
            features_todos = [f for f in poly_layer.getFeatures() if f['DN'] != no_data and f['DN'] is not None]
            features_grandes = [f for f in features_todos if f.geometry().area() > area_min_valido]

            if len(features_grandes) == 0:
                msg = "Archivo .asc inválido: no se detectó ningún polígono con área suficiente"
                self.log_callback(f"❌ {msg}: {arc}")
                capa.changeAttributeValue(fid, idx_v, 0)
                capa.changeAttributeValue(fid, idx_c, msg)
                capa.changeAttributeValue(fid, idx_proc, True)
                return

            comentarios_gis = []
            muros_hit = set()
            sectores_hit = set()

            for feat in features_grandes:
                fields = poly_layer.fields()
                boundary_layer = QgsVectorLayer("Polygon?crs={}".format(poly_layer.crs().authid()),
                                                base_arc_limpio, "memory")
                boundary_layer_data = boundary_layer.dataProvider()
                boundary_layer_data.addAttributes(fields)
                boundary_layer.updateFields()
                new_feat = QgsFeature(boundary_layer.fields())
                new_feat.setGeometry(feat.geometry())
                for i, field in enumerate(fields):
                    new_feat.setAttribute(i, feat[field.name()])
                boundary_layer_data.addFeatures([new_feat])
                boundary_layer.updateExtents()

                # Validación espacial muros/sectores
                if isinstance(capa_muros, QgsVectorLayer) and isinstance(capa_sectores, QgsVectorLayer):
                    resultado_esp = self.validar_concavehull(boundary_layer, capa_muros, capa_sectores)
                    muros_hit.update(resultado_esp["muros"])
                    sectores_hit.update(resultado_esp["sectores"])
                else:
                    comentarios_gis.append("No se validó contra muros/sectores por falta de capas.")

                # Validación DEM
                dem_layer = None
                if muros_hit and DEMS:
                    for muro in muros_hit:
                        dem_candidate = DEMS.get(f"DEM_{muro}")
                        if dem_candidate:
                            dem_layer = dem_candidate
                            break
                if not dem_layer and DEMS:
                    dem_layer = list(DEMS.values())[0]
                if dem_layer:
                    geom = new_feat.geometry()
                    extent = geom.boundingBox()
                    step = max((extent.width()/30), (extent.height()/30), 1)
                    fuera_dem = []
                    x = extent.xMinimum()
                    while x < extent.xMaximum():
                        y = extent.yMinimum()
                        while y < extent.yMaximum():
                            pt = QgsPointXY(x, y)
                            if geom.contains(QgsGeometry.fromPointXY(pt)):
                                prov_dem = dem_layer.dataProvider()
                                prov_asc = raster_layer.dataProvider()
                                res_dem = prov_dem.identify(pt, QgsRaster.IdentifyFormatValue)
                                res_asc = prov_asc.identify(pt, QgsRaster.IdentifyFormatValue)
                                val_dem = res_dem.results().get(1)
                                val_asc = res_asc.results().get(1)
                                if val_dem is not None and val_asc is not None:
                                    diff = abs(val_dem - val_asc)
                                    if diff > tolerancia_cota:
                                        fuera_dem.append({"x": x, "y": y, "diff": diff})
                            y += step
                        x += step
                    if fuera_dem:
                        msg = f"Boundary: diferencia de cota DEM > {tolerancia_cota}m en {len(fuera_dem)} puntos"
                        comentarios_gis.append(msg)
                        self.log_callback(f"❌ {msg}")
                        capa.changeAttributeValue(fid, idx_v, 0)
                        capa.changeAttributeValue(fid, idx_c, msg)
                        capa.changeAttributeValue(fid, idx_proc, True)
                        return

            if muros_hit:
                comentarios_gis.append(f"Boundary interseca muros: {', '.join(muros_hit)}")
            if sectores_hit:
                comentarios_gis.append(f"Boundary interseca sectores: {', '.join(sectores_hit)}")

            capa.changeAttributeValue(fid, idx_v, 1)
            comentarios_final = comentarios_gis.copy()
            capa.changeAttributeValue(fid, idx_c, ";".join(comentarios_final).replace(";", ",") if comentarios_final else "OK")
            capa.changeAttributeValue(fid, idx_proc, True)

        except Exception as e:
            msg = f"Error procesando ASC: {str(e)}"
            self.log_callback(f"❌ {msg}")
            capa.changeAttributeValue(fid, idx_v, 0)
            capa.changeAttributeValue(fid, idx_c, msg)
            capa.changeAttributeValue(fid, idx_proc, True)

    # =========================
    # VALIDACIÓN Y PROCESAMIENTO GENERAL
    # =========================

    def actualizar_nombres_capa(self, capa):
        idx_nom = capa.fields().indexOf(self.COLUMNA_NOMBRE)
        capa.startEditing()
        for feat in capa.getFeatures():
            v = feat[".CSV"]
            if v and v.startswith("ARCHIVOS_NUBE/CSV-ASC/"):
                capa.changeAttributeValue(feat.id(), idx_nom, v.replace("ARCHIVOS_NUBE/CSV-ASC/", ""))
        capa.commitChanges()
        self.log_callback("✅ Campos 'NombreArchivo' actualizados sin prefijo")

    def procesar_archivos_y_validar(self, capa, carpeta_b):
        idx_v = capa.fields().indexOf(self.COLUMNA_VALIDAR)
        idx_c = capa.fields().indexOf(self.COLUMNA_COMENTARIOS)
        idx_proc = capa.fields().indexOf(self.COLUMNA_PROCESADO)
        idx_nom = capa.fields().indexOf(self.COLUMNA_NOMBRE)
        idx_foto = capa.fields().indexOf(self.COLUMNA_FOTO)
        
        feats = {
            self.limpiar_nombre(os.path.splitext(f[self.COLUMNA_NOMBRE])[0]): f.id()
            for f in capa.getFeatures()
            if f[self.COLUMNA_NOMBRE] and not f[self.COLUMNA_PROCESADO]
        }
        
        try:
            capa_muros = QgsProject.instance().mapLayersByName('Poligonos')[0]
            capa_sectores = QgsProject.instance().mapLayersByName('Poligonos_Sectores')[0]
            DEMS = {l.name():l for l in QgsProject.instance().mapLayers().values() if l.name().startswith("DEM_")}
        except Exception as e:
            self.log_callback(f"⚠️ No se encontraron todas las capas de referencia: {e}")
            capa_muros = None
            capa_sectores = None
            DEMS = {}
        
        capa.startEditing()
        
        archivos_procesados = 0
        total_archivos = len([f for f in os.listdir(self.DIR_CSV_ORIG) 
                             if self.limpiar_nombre(os.path.splitext(f)[0]) in feats])

        for arc in os.listdir(self.DIR_CSV_ORIG):
            base, ext = os.path.splitext(arc)
            base_limpio = self.limpiar_nombre(base)
            if base_limpio not in feats:
                continue
            
            fid = feats[base_limpio]
            ruta_archivo = os.path.join(self.DIR_CSV_ORIG, arc)
            self.log_callback(f"\n🔎 Procesando archivo: {arc}")
            
            # Actualizar progreso
            archivos_procesados += 1
            progreso_archivo = 50 + int((archivos_procesados / total_archivos) * 30)
            self.progress_callback(progreso_archivo, f"Procesando {arc}...")

            if ext.lower() == '.asc':
                self.procesar_archivo_asc_validacion(
                    capa, fid, arc, ruta_archivo, carpeta_b, idx_v, idx_c, idx_proc,
                    capa_muros=capa_muros, capa_sectores=capa_sectores, DEMS=DEMS, tolerancia_cota=20
                )
                continue

            df = self.leer_archivo_flexible(ruta_archivo)
            if df is None:
                self.marcar_csv_invalido(capa, fid, arc, idx_v, idx_c, idx_proc, "Formato archivo inválido")
                continue

            if ext.lower() in ['.xlsx', '.xls']:
                salida_csv = os.path.join(self.DIR_CSV_PROC, self.limpiar_nombre(base) + ".csv")
                with open(salida_csv, 'w', encoding='utf-8') as f:
                    df.to_csv(f, sep=';', header=False, index=False)
                ruta_csv = salida_csv
            else:
                ruta_csv = ruta_archivo

            res = self.validar_filas(df, arc, fid, capa)
            ok, coms = res["ok"], ";".join(res["comentarios"])
            df_corr = res["coordenadas"]
            if not ok:
                self.marcar_csv_invalido(capa, fid, arc, idx_v, idx_c, idx_proc, coms)
                continue

            capa_puntos = self.csv_a_capa_puntos(df_corr, nombre=f"pts_{arc}")
            comentarios_gis = []
            if capa_puntos and capa_puntos.featureCount() > 2:
                try:
                    poligono = self.generar_concave_hull(capa_puntos, alpha=1.0)
                    if poligono and poligono.featureCount() > 0:
                        if capa_muros and capa_sectores:
                            resultado_esp = self.validar_concavehull(poligono, capa_muros, capa_sectores)
                            muros_hit = resultado_esp["muros"]
                            sectores_hit = resultado_esp["sectores"]
                            if muros_hit:
                                comentarios_gis.append(f"ConcaveHull interseca muros: {', '.join(muros_hit)}")
                            if sectores_hit:
                                comentarios_gis.append(f"ConcaveHull interseca sectores: {', '.join(sectores_hit)}")
                            
                            dem_layer = None
                            if muros_hit and f"DEM_{muros_hit[0]}" in DEMS:
                                dem_layer = DEMS[f"DEM_{muros_hit[0]}"]
                            elif DEMS:
                                dem_layer = list(DEMS.values())[0]
                            if dem_layer:
                                fuera_dem = self.comparar_cota_dem(capa_puntos, dem_layer)
                                if fuera_dem:
                                    comentarios_gis.append(f"ConcaveHull: puntos fuera DEM: {[f['id'] for f in fuera_dem]}")
                        else:
                            comentarios_gis.append("No se validó espacialmente (capas faltantes)")
                    else:
                        comentarios_gis.append("No se generó polígono ConcaveHull")
                except Exception as e:
                    comentarios_gis.append(f"Error en validación espacial: {str(e)}")
            else:
                comentarios_gis.append("No se generó capa de puntos válida para ConcaveHull")

            self.procesar_csv_valido(
                capa, fid, arc, ext, ruta_csv, carpeta_b, idx_v, idx_c, idx_proc,
                idx_nom, idx_foto, df_corr, res, comentarios_gis
            )

        # Verificación final para corregir nombres con puntos adicionales
        capa.startEditing()
        for feat in capa.getFeatures():
            nombre = feat[self.COLUMNA_NOMBRE]
            if nombre and '..' in nombre:
                nombre_corregido = self.limpiar_nombre(nombre)
                capa.changeAttributeValue(feat.id(), idx_nom, nombre_corregido)
                self.log_callback(f"✅ Corregido NombreArchivo: {nombre} -> {nombre_corregido}")
        capa.commitChanges()

        # Renombrar archivos en las carpetas de salida con ".."
        for folder in [self.DIR_CSV_PROC, self.DIR_IMG_PROC]:
            if os.path.exists(folder):
                for fname in os.listdir(folder):
                    if '..' in fname:
                        fname_limpio = self.limpiar_nombre(fname)
                        if fname != fname_limpio:
                            os.rename(os.path.join(folder, fname), os.path.join(folder, fname_limpio))
                            self.log_callback(f"✅ Archivo renombrado: {fname} -> {fname_limpio}")

        capa.commitChanges()
        self.log_callback("\n✅ Proceso GIS completado con validación espacial, backup y corrección de nombres.")

    def limpiar_archivos_auxiliares(self):
        if os.path.exists(self.DIR_CSV_PROC):
            for fname in os.listdir(self.DIR_CSV_PROC):
                if fname.endswith('.asc.aux.xml'):
                    aux_path = os.path.join(self.DIR_CSV_PROC, fname)
                    try:
                        os.remove(aux_path)
                        self.log_callback(f"🧹 Archivo auxiliar eliminado: {aux_path}")
                    except Exception as e:
                        self.log_callback(f"⚠️ No se pudo eliminar {aux_path}: {e}")

    # =========================
    # MÉTODO PRINCIPAL
    # =========================

    def ejecutar_validacion_completa(self):
        """Ejecutar todo el proceso de validación - MÉTODO PRINCIPAL"""
        try:
            self.progress_callback(5, "Iniciando validación completa...")
            self.log_callback("🔍 Iniciando script de validación GIS completo...")
            
            # Asegurar carpetas
            self.progress_callback(10, "Creando estructura de carpetas...")
            self.asegurar_carpetas()
            
            # Copiar GPKG
            self.progress_callback(15, "Copiando GPKG original...")
            self.log_callback("🔄 Copiando GPKG original a carpeta de procesados...")
            shutil.copy2(self.ORIG_GPKG, self.TMP_GPKG)
            
            # Cargar capa
            self.progress_callback(20, "Cargando capa de levantamientos...")
            uri = f"{self.TMP_GPKG}|layername={self.NOMBRE_CAPA}"
            layer = QgsVectorLayer(uri, self.NOMBRE_CAPA, "ogr")
            if not layer.isValid():
                raise Exception(f"No se pudo cargar la capa desde {self.TMP_GPKG}")
            
            # Agregar al proyecto si no existe
            project = QgsProject.instance()
            if not any(lyr.name() == self.NOMBRE_CAPA for lyr in project.mapLayers().values()):
                project.addMapLayer(layer)
                self.log_callback(f"✅ Capa '{self.NOMBRE_CAPA}' cargada desde copia temporal")
            else:
                self.log_callback(f"ℹ️ Capa '{self.NOMBRE_CAPA}' ya está cargada")
            
            # Backup completo
            self.progress_callback(30, "Creando backup completo...")
            carpeta_b = self.respaldo_completo()
            
            # Actualizar nombres
            self.progress_callback(40, "Actualizando nombres de archivos...")
            self.actualizar_nombres_capa(layer)
            
            # Procesar y validar archivos (progreso 50-80 dentro del método)
            self.progress_callback(50, "Procesando y validando archivos...")
            self.procesar_archivos_y_validar(layer, carpeta_b)
            
            # Limpiar auxiliares
            self.progress_callback(90, "Limpiando archivos auxiliares...")
            self.limpiar_archivos_auxiliares()
            
            self.progress_callback(100, "¡Validación completada!")
            self.log_callback("🎉 Proceso GIS completado con validación espacial, backup y limpieza de auxiliares")
            
            return {
                'success': True,
                'message': 'Validación completada exitosamente',
                'backup_folder': carpeta_b
            }
            
        except Exception as e:
            import traceback
            error_msg = f"Error durante la validación: {str(e)}"
            error_details = traceback.format_exc()
            self.log_callback(f"❌ {error_msg}")
            self.log_callback(f"📋 Detalles del error:\n{error_details}")
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }