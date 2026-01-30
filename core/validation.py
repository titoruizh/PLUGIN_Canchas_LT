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
        
        # Contadores para logs concisos
        self.log_counters = {
            'archivos_renombrados': 0,
            'rutas_normalizadas': 0,
            'auxiliares_eliminados': 0,
            'csv_copiados': 0,
            'jpg_copiados': 0,
            'filas_filtradas': 0
        }

    # =========================
    # UTILIDADES GENERALES
    # =========================
    
    def limpiar_nombre(self, nombre):
        """Quita puntos finales, espacios y puntos consecutivos del nombre base, y convierte a mayúsculas."""
        return re.sub(r'\.+', '.', nombre.strip()).rstrip('.').strip().upper()

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
        
        # Silencioso: el backup se reporta al final
        # self.log_callback(f"📦 Backup completo creado en: {carpeta_b}")
        return carpeta_b

    def respaldar_archivo(self, path, carpeta_b):
        try:
            shutil.copy2(path, carpeta_b)
        except Exception as e:
            self.log_callback(f"⚠️ No se pudo respaldar {path}: {e}")

    def detectar_errores_humanos(self, capa):
        """Detecta errores humanos comunes antes de procesar"""
        errores = []
        advertencias = []
        
        # 1. Archivos CSV/ASC duplicados en GPKG
        archivos_dict = {}
        idx_csv = capa.fields().indexOf(".CSV")
        
        for feat in capa.getFeatures():
            nombre = feat[self.COLUMNA_NOMBRE]
            if nombre:
                nombre_limpio = self.limpiar_nombre(nombre)
                if nombre_limpio in archivos_dict:
                    errores.append(f"❌ DUPLICADO: '{nombre}' aparece en filas {archivos_dict[nombre_limpio]} y {feat.id()}")
                else:
                    archivos_dict[nombre_limpio] = feat.id()
        
        # 2. Imágenes duplicadas en GPKG
        fotos_dict = {}
        idx_foto = capa.fields().indexOf("Foto")
        
        if idx_foto >= 0:
            for feat in capa.getFeatures():
                foto = feat["Foto"]
                if foto:
                    foto_limpia = self.limpiar_nombre(foto)
                    if foto_limpia in fotos_dict:
                        errores.append(f"❌ IMAGEN DUPLICADA: '{foto}' en filas {fotos_dict[foto_limpia]} y {feat.id()}")
                    else:
                        fotos_dict[foto_limpia] = feat.id()
        
        # 3. Inconsistencia nombre vs muro/sector en BD
        idx_muro = capa.fields().indexOf("Muro")
        idx_sector = capa.fields().indexOf("Sector")
        
        if idx_muro >= 0:
            for feat in capa.getFeatures():
                nombre = feat[self.COLUMNA_NOMBRE]
                muro = feat["Muro"]
                
                if nombre and muro:
                    # Extraer muro del nombre (ej: MP_S1_... -> MP)
                    partes = nombre.split('_')
                    if len(partes) >= 2:
                        muro_en_nombre = partes[0].upper()
                        if muro_en_nombre != muro.upper() and muro_en_nombre in ['MP', 'ME', 'MO']:
                            advertencias.append(f"⚠️ INCONSISTENCIA fila {feat.id()}: Nombre indica '{muro_en_nombre}' pero BD tiene '{muro}'")
        
        # 4. Archivos físicos duplicados en carpetas
        archivos_fisicos_csv = {}
        if os.path.exists(self.DIR_CSV_ORIG):
            for archivo in os.listdir(self.DIR_CSV_ORIG):
                nombre_limpio = self.limpiar_nombre(archivo).upper()
                if nombre_limpio in archivos_fisicos_csv:
                    errores.append(f"❌ ARCHIVO DUPLICADO EN DISCO: '{archivo}' y '{archivos_fisicos_csv[nombre_limpio]}'")
                else:
                    archivos_fisicos_csv[nombre_limpio] = archivo
        
        archivos_fisicos_img = {}
        if os.path.exists(self.DIR_IMG_ORIG):
            for archivo in os.listdir(self.DIR_IMG_ORIG):
                nombre_limpio = self.limpiar_nombre(archivo).upper()
                if nombre_limpio in archivos_fisicos_img:
                    errores.append(f"❌ IMAGEN DUPLICADA EN DISCO: '{archivo}' y '{archivos_fisicos_img[nombre_limpio]}'")
                else:
                    archivos_fisicos_img[nombre_limpio] = archivo
        
        return errores, advertencias

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

        # FILTRADO TEMPRANO: Eliminar filas problemáticas ANTES de procesar
        if not df.empty:
            # Patrones a filtrar: RTCM, chequeo, inf
            patrones_filtrar = ['rtcm', 'chequeo', 'inf']
            
            # Crear máscara para identificar filas problemáticas
            mask_problemas = False
            for patron in patrones_filtrar:
                # Revisar todas las columnas del DataFrame
                for col in df.columns:
                    mask_problemas |= df[col].astype(str).str.lower().str.contains(patron, na=False)
            
            filas_originales = len(df)
            df = df[~mask_problemas].reset_index(drop=True)
            filas_filtradas = filas_originales - len(df)
            
            # Solo contar, no logear individualmente
            if filas_filtradas > 0:
                self.log_counters['filas_filtradas'] += filas_filtradas

        header_keywords = {"id", "norte", "este", "cota", "desc", "descripcion", "x", "y", "z"}
        primera_fila = df.iloc[0].astype(str).str.lower()
        n_no_num = sum([not val.replace('.', '', 1).isdigit() for val in primera_fila[:4]])
        if (
            n_no_num >= 2
            or any(any(k in str(cell) for k in header_keywords) for cell in primera_fila)
        ):
            df = df.iloc[1:].reset_index(drop=True)

        df.columns = self.COLUMNAS_REQUERIDAS
        return df

    def validar_coordenadas_csv(self, df, archivo="archivo"):
        """Valida que las coordenadas tengan el formato correcto"""
        for idx, f in df.iterrows():
            try:
                # Validar Norte
                norte_val = f['norte']
                if pd.isna(norte_val):
                    self.log_callback(f"⚠️ [{archivo}] Fila {idx}: Valor 'norte' vacío")
                    return False
                norte_str = str(int(float(norte_val))) if isinstance(norte_val, (int, float)) else str(norte_val).split('.')[0]
                if not (norte_str.isdigit() and len(norte_str) == 7):
                    self.log_callback(f"⚠️ [{archivo}] Fila {idx}: 'norte' inválido: {norte_val} (debe ser 7 dígitos) - Fila eliminada")
                    return False
                
                # Validar Este
                este_val = f['este']
                if pd.isna(este_val):
                    self.log_callback(f"⚠️ Fila {idx}: Valor 'este' vacío")
                    return False
                este_str = str(int(float(este_val))) if isinstance(este_val, (int, float)) else str(este_val).split('.')[0]
                if not (este_str.isdigit() and len(este_str) == 6):
                    self.log_callback(f"⚠️ Fila {idx}: 'este' inválido: {este_val} (debe ser 6 dígitos)")
                    return False
                
                # Validar Cota
                cota_val = f['cota']
                if pd.isna(cota_val):
                    self.log_callback(f"⚠️ Fila {idx}: Valor 'cota' vacío")
                    return False
                cota_str = str(int(float(cota_val))) if isinstance(cota_val, (int, float)) else str(cota_val).split('.')[0]
                if not (cota_str.isdigit() and len(cota_str) == 3):
                    self.log_callback(f"⚠️ Fila {idx}: 'cota' inválida: {cota_val} (debe ser 3 dígitos)")
                    return False
                    
            except Exception as e:
                self.log_callback(f"⚠️ Error en fila {idx}: {e}")
                return False
        return True

    def validar_datos_faltantes(self, df, nombre_archivo):
        """
        Valida si hay datos faltantes en columnas críticas
        
        Args:
            df: DataFrame a validar
            nombre_archivo: Nombre del archivo para reportes
            
        Returns:
            list: Lista de errores encontrados
        """
        columnas_criticas = ['este', 'norte', 'cota']
        errores = []
        
        for col in columnas_criticas:
            if col in df.columns:
                # Contar valores NaN, vacíos o None
                vacios = df[col].isna().sum()
                if vacios > 0:
                    filas_vacias = df[df[col].isna()].index.tolist()
                    errores.append(f"Columna '{col}': {vacios} valores vacíos en filas {filas_vacias}")
            else:
                errores.append(f"Columna '{col}': no existe en el archivo")
        
        if errores:
            self.log_callback(f"❌ ERRORES EN {nombre_archivo}:")
            for i, error in enumerate(errores, 1):
                self.log_callback(f"   {i}. {error}")
        
        return errores

    def generar_reporte_errores(self, nombre_archivo, errores, tipo_error="Validación"):
        """
        Genera un reporte detallado de errores por archivo
        
        Args:
            nombre_archivo: Nombre del archivo con errores
            errores: Lista de errores
            tipo_error: Tipo de error para el reporte
        """
        if errores:
            self.log_callback(f"📋 REPORTE DE {tipo_error.upper()} - {nombre_archivo}:")
            for i, error in enumerate(errores, 1):
                self.log_callback(f"   {i}. {error}")
            self.log_callback(f"📊 Total: {len(errores)} problemas encontrados")
            self.log_callback("")  # Línea en blanco para separar reportes

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
        
        # Validación previa de datos faltantes
        errores_faltantes = self.validar_datos_faltantes(df, archivo)
        if errores_faltantes:
            self.generar_reporte_errores(archivo, errores_faltantes, "Datos Faltantes")
            return {"ok": False, "comentarios": errores_faltantes, 
                   "coordenadas": df, "muro": None, "sector": None}
        
        # Validación de coordenadas con nombre de archivo
        if not self.validar_coordenadas_csv(df, archivo):
            # Intentar invertir columnas como solución
            inv = self.invertir_columnas(df)
            if self.validar_coordenadas_csv(inv, archivo):
                df = inv
                comentarios.append('Coordenadas invertidas corregidas')
            else:
                error_msg = f"Error en validación numérica para archivo {archivo}"
                self.log_callback(f"❌ {error_msg}")
                return {"ok": False, "comentarios": [error_msg],
                        "coordenadas": df, "muro": None, "sector": None}
        
        f = next(capa.getFeatures(QgsFeatureRequest(fid)))
        muro, sector = f['Muro'], f['Sector']
        nuevo_muro = muro  # Inicializar antes del try-except
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
            
            # Búsqueda flexible de DEM (acepta DEM_MP_250101 como DEM_MP)
            dem_prefix = f"DEM_{nuevo_muro}".upper()
            dem_layer = None
            for lyr in QgsProject.instance().mapLayers().values():
                if lyr.name().upper().startswith(dem_prefix):
                    dem_layer = lyr
                    break
            
            if not dem_layer:
                # Fallback to mapLayersByName just in case
                dems_strict = QgsProject.instance().mapLayersByName(f"DEM_{nuevo_muro}")
                if dems_strict:
                    dem_layer = dems_strict[0]
            
            if not dem_layer:
                # Si no hay DEM específico, logear advertencia pero no fallar hard si no es crítico,
                # o re-raise exception. El código original asumía que existía.
                # Mantendremos la excepción para seguir el flujo original de error.
                raise Exception(f"No se encontró capa DEM para muro {nuevo_muro} (Buscado: {dem_prefix}*)")

            dem = dem_layer
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
                self.log_counters['csv_copiados'] += 1  # Solo contar, no logear
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
            self.log_counters['jpg_copiados'] += 1  # Solo contar, no logear

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
                self.log_counters['auxiliares_eliminados'] += 1  # Solo contar, no logear
            except Exception as e:
                self.log_callback(f"⚠️ No se pudo eliminar {aux_xml}: {e}")

        base_arc_limpio = self.limpiar_nombre(os.path.splitext(arc)[0])
        orig_jpg = os.path.join(self.DIR_IMG_ORIG, base_arc_limpio + ".jpg")
        if os.path.exists(orig_jpg):
            self.respaldar_archivo(orig_jpg, carpeta_b)
            dst_jpg = os.path.join(self.DIR_IMG_PROC, f"F{base_arc_limpio}.jpg")
            shutil.copy2(orig_jpg, dst_jpg)
            self.log_counters['jpg_copiados'] += 1  # Solo contar, no logear

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

    def normalizar_ruta_archivos_nube(self, ruta):
        """
        Normaliza rutas que contengan ARCHIVOS_NUBE eliminando prefijos y estandarizando barras
        
        Ejemplos:
        E:\CANCHAS_QFIELD\QFIELD TERRENO\QFIELD\ARCHIVOS_NUBE\CSV-ASC\archivo.csv
        -> ARCHIVOS_NUBE/CSV-ASC/archivo.csv
        
        E:\CANCHAS_QFIELD\QFIELD TERRENO\QFIELD\ARCHIVOS_NUBE\IMAGENES\foto.jpg
        -> ARCHIVOS_NUBE/IMAGENES/foto.jpg
        """
        if not ruta:
            return ruta
            
        # Convertir todas las barras a forward slash para estandarizar
        ruta_normalizada = str(ruta).replace("\\", "/")
        
        # Buscar la posición de ARCHIVOS_NUBE (case insensitive)
        ruta_upper = ruta_normalizada.upper()
        pos_archivos_nube = ruta_upper.find("ARCHIVOS_NUBE")
        
        if pos_archivos_nube != -1:
            # Extraer desde ARCHIVOS_NUBE hasta el final
            ruta_final = ruta_normalizada[pos_archivos_nube:]
            if ruta_normalizada != ruta_final:  # Solo contar si hubo cambio
                self.log_counters['rutas_normalizadas'] += 1
            return ruta_final
        
        # Si no contiene ARCHIVOS_NUBE, devolver la ruta original normalizada
        return ruta_normalizada

    def actualizar_nombres_capa(self, capa):
        """
        Actualiza y normaliza los campos de rutas en la capa, eliminando prefijos largos
        y estandarizando el formato de rutas
        """
        idx_nom = capa.fields().indexOf(self.COLUMNA_NOMBRE)
        idx_csv = capa.fields().indexOf(".CSV")
        idx_foto = capa.fields().indexOf("Foto")
        
        capa.startEditing()
        total_actualizados = 0
        
        for feat in capa.getFeatures():
            fid = feat.id()
            cambios_realizados = False
            
            # Normalizar campo .CSV
            if idx_csv >= 0:
                csv_actual = feat[".CSV"]
                if csv_actual:
                    csv_normalizado = self.normalizar_ruta_archivos_nube(csv_actual)
                    if csv_actual != csv_normalizado:
                        capa.changeAttributeValue(fid, idx_csv, csv_normalizado)
                        cambios_realizados = True
            
            # Normalizar campo Foto
            if idx_foto >= 0:
                foto_actual = feat["Foto"]
                if foto_actual:
                    foto_normalizada = self.normalizar_ruta_archivos_nube(foto_actual)
                    if foto_actual != foto_normalizada:
                        capa.changeAttributeValue(fid, idx_foto, foto_normalizada)
                        cambios_realizados = True
            
            # Actualizar NombreArchivo basado en el campo .CSV normalizado
            if idx_nom >= 0 and idx_csv >= 0:
                csv_normalizado = feat[".CSV"] if not cambios_realizados else self.normalizar_ruta_archivos_nube(feat[".CSV"])
                if csv_normalizado and csv_normalizado.startswith("ARCHIVOS_NUBE/CSV-ASC/"):
                    nombre_archivo = csv_normalizado.replace("ARCHIVOS_NUBE/CSV-ASC/", "")
                    capa.changeAttributeValue(fid, idx_nom, nombre_archivo)
            cambios_realizados = True
            
            if cambios_realizados:
                total_actualizados += 1
        
        capa.commitChanges()        
        # Silencioso: no logear normalización (solo progreso visual)
        # self.log_callback(f"📋 Normalización completada: {total_actualizados} registros actualizados")

    def procesar_archivos_y_validar(self, capa, carpeta_b):
        # Estadísticas de procesamiento
        self.stats_procesamiento = {
            'total_archivos': 0,
            'archivos_exitosos': 0,
            'archivos_con_errores': 0,
            'errores_por_archivo': {},
            'archivos_sin_bd': [],
            'archivos_con_bd': [],
            'archivos_asc_procesados': [],
            'archivos_csv_exitosos': [],
            'archivos_copiados_sin_validar': []
        }
        
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
        
        # Verificar si hay archivos pendientes de procesar
        if not feats:
            total_registros = sum(1 for f in capa.getFeatures() if f[self.COLUMNA_NOMBRE])
            self.log_callback(f"⚠️ No hay archivos pendientes de procesar.")
            self.log_callback(f"📋 Total de registros en BD: {total_registros}")
            self.log_callback(f"✅ Todos los archivos ya están marcados como 'Procesado'")
            self.log_callback(f"\n💡 Para reprocesar, desmarca la columna 'Procesado' en el GeoPackage")
            return self.stats_procesamiento
        
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
        # Contar TODOS los archivos en la carpeta origen para estadísticas reales
        todos_archivos = [f for f in os.listdir(self.DIR_CSV_ORIG) 
                         if f.lower().endswith(('.csv', '.xlsx', '.xls', '.asc'))]
        archivos_en_bd = [f for f in todos_archivos 
                         if self.limpiar_nombre(os.path.splitext(f)[0]) in feats]
        archivos_sin_bd = [f for f in todos_archivos 
                          if self.limpiar_nombre(os.path.splitext(f)[0]) not in feats]
        
        # Inicializar estadísticas con números reales
        self.stats_procesamiento['total_archivos'] = len(todos_archivos)
        self.stats_procesamiento['archivos_con_bd'] = archivos_en_bd
        self.stats_procesamiento['archivos_sin_bd'] = archivos_sin_bd

        for arc in os.listdir(self.DIR_CSV_ORIG):
            base, ext = os.path.splitext(arc)
            base_limpio = self.limpiar_nombre(base)
            if base_limpio not in feats:
                continue
            
            fid = feats[base_limpio]
            ruta_archivo = os.path.join(self.DIR_CSV_ORIG, arc)            
            # Silencioso: no logear cada archivo individual
            # self.log_callback(f"\n🔎 Procesando archivo: {arc}")
            
            # Actualizar progreso
            archivos_procesados += 1
            progreso_archivo = 50 + int((archivos_procesados / self.stats_procesamiento['total_archivos']) * 30)
            self.progress_callback(progreso_archivo, f"Procesando {arc}...")

            if ext.lower() == '.asc':
                self.procesar_archivo_asc_validacion(
                    capa, fid, arc, ruta_archivo, carpeta_b, idx_v, idx_c, idx_proc,
                    capa_muros=capa_muros, capa_sectores=capa_sectores, DEMS=DEMS, tolerancia_cota=20
                )
                self.stats_procesamiento['archivos_asc_procesados'].append(arc)
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

            try:
                res = self.validar_filas(df, arc, fid, capa)
                ok, coms = res["ok"], ";".join(res["comentarios"])
                df_corr = res["coordenadas"]
                if not ok:
                    self.marcar_csv_invalido(capa, fid, arc, idx_v, idx_c, idx_proc, coms)
                    self.log_callback(f"⚠️ Archivo {arc} marcado como inválido: {coms}")
                    self.stats_procesamiento['archivos_con_errores'] += 1
                    self.stats_procesamiento['errores_por_archivo'][arc] = coms
                    continue
                else:
                    self.stats_procesamiento['archivos_exitosos'] += 1
                    self.stats_procesamiento['archivos_csv_exitosos'].append(arc)
            except Exception as e:
                error_msg = f"Error en validación de {arc}: {str(e)}"
                self.log_callback(f"❌ {error_msg}")
                self.marcar_csv_invalido(capa, fid, arc, idx_v, idx_c, idx_proc, error_msg)
                self.stats_procesamiento['archivos_con_errores'] += 1
                self.stats_procesamiento['errores_por_archivo'][arc] = error_msg
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
        
        # Generar reporte final de estadísticas
        self.generar_reporte_detallado()
        
        self.log_callback("\n✅ Proceso GIS completado con validación espacial, backup y corrección de nombres.")

    def generar_reporte_final(self):
        """Genera un reporte final con estadísticas del procesamiento"""
        stats = self.stats_procesamiento
        self.log_callback("\n" + "="*60)
        self.log_callback("📊 REPORTE FINAL DE PROCESAMIENTO")
        self.log_callback("="*60)
        self.log_callback(f"� Total de archivos encontrados: {stats['total_archivos']}")
        self.log_callback(f"📋 Archivos con registro en BD: {stats.get('archivos_en_bd', 0)}")
        self.log_callback(f"📝 Archivos sin registro en BD: {stats.get('archivos_sin_bd', 0)}")
        self.log_callback(f"✅ Archivos procesados exitosamente: {stats['archivos_exitosos']}")
        self.log_callback(f"❌ Archivos con errores: {stats['archivos_con_errores']}")
        
        # Calcular archivos copiados pero no validados
        archivos_copiados = stats['archivos_exitosos'] + stats['archivos_con_errores']
        if archivos_copiados < stats['total_archivos']:
            no_procesados = stats['total_archivos'] - archivos_copiados
            self.log_callback(f"📋 Archivos copiados sin validar: {no_procesados}")
        
        if stats['errores_por_archivo']:
            self.log_callback("\n🔍 DETALLE DE ERRORES POR ARCHIVO:")
            for archivo, error in stats['errores_por_archivo'].items():
                self.log_callback(f"   📁 {archivo}: {error}")
        
        # Porcentaje de éxito sobre archivos que intentaron validarse
        archivos_intentados = stats['archivos_exitosos'] + stats['archivos_con_errores']
        if archivos_intentados > 0:
            porcentaje_exito = (stats['archivos_exitosos'] / archivos_intentados * 100)
            self.log_callback(f"\n📈 Tasa de éxito en validación: {porcentaje_exito:.1f}%")
        
        self.log_callback("="*60)

    def limpiar_archivos_auxiliares(self):
        """Limpia archivos auxiliares sin generar logs individuales"""
        if os.path.exists(self.DIR_CSV_PROC):
            for fname in os.listdir(self.DIR_CSV_PROC):
                if fname.endswith('.asc.aux.xml'):
                    aux_path = os.path.join(self.DIR_CSV_PROC, fname)
                    try:
                        os.remove(aux_path)
                        self.log_counters['auxiliares_eliminados'] += 1
                    except Exception as e:
                        self.log_callback(f"⚠️ No se pudo eliminar {aux_path}: {e}")

    def normalizar_nombres_y_validar_nomenclatura(self, capa):
        """
        Normaliza nombres de archivos a mayúsculas y valida nomenclatura con GPKG
        """
        # Silencioso: solo mostrar errores si los hay
        # self.log_callback("🔄 Iniciando normalización de nombres y validación de nomenclatura...")
        
        # 1. Normalizar nombres de archivos a MAYÚSCULAS
        self.normalizar_nombres_archivos()
        
        # 2. Actualizar campos del GPKG para que coincidan con archivos normalizados
        self.actualizar_campos_gpkg_mayusculas(capa)
        
        # 3. Validar nomenclatura con datos del GPKG
        self.validar_nomenclatura_con_gpkg(capa)
    
    def normalizar_nombres_archivos(self):
        """Convierte todos los nombres de archivos a MAYÚSCULAS"""
        carpetas = [self.DIR_CSV_ORIG, self.DIR_IMG_ORIG]
        total_renombrados = 0
        
        for carpeta in carpetas:
            if not os.path.exists(carpeta):
                continue
            
            for archivo in os.listdir(carpeta):
                ruta_actual = os.path.join(carpeta, archivo)
                if os.path.isfile(ruta_actual):
                    # Separar nombre y extensión
                    nombre_sin_ext, extension = os.path.splitext(archivo)
                    nombre_mayuscula = nombre_sin_ext.upper() + extension.lower()
                    
                    if archivo != nombre_mayuscula:
                        ruta_nueva = os.path.join(carpeta, nombre_mayuscula)
                        try:
                            os.rename(ruta_actual, ruta_nueva)
                            total_renombrados += 1
                        except Exception as e:
                            self.log_callback(f"   ❌ Error renombrando {archivo}: {e}")
        
        if total_renombrados > 0:
            self.log_callback(f"📋 Archivos renombrados a mayúsculas: {total_renombrados}")
    
    def actualizar_campos_gpkg_mayusculas(self, capa):
        """Actualiza los campos del GPKG para que coincidan con archivos normalizados"""
        # self.log_callback("🔄 Actualizando campos del GPKG a mayúsculas...")
        
        capa.startEditing()
        total_actualizados = 0
        
        try:
            for feature in capa.getFeatures():
                fid = feature.id()
                cambios_realizados = False
                
                # Actualizar campo Muro a mayúsculas
                try:
                    muro_actual = feature["Muro"] if "Muro" in [field.name() for field in feature.fields()] else ""
                    if muro_actual and str(muro_actual) != str(muro_actual).upper():
                        idx_muro = capa.fields().indexOf("Muro")
                        if idx_muro >= 0:
                            capa.changeAttributeValue(fid, idx_muro, str(muro_actual).upper())
                            cambios_realizados = True
                except (KeyError, AttributeError):
                    pass
                
                # Actualizar campo Sector a mayúsculas
                try:
                    sector_actual = feature["Sector"] if "Sector" in [field.name() for field in feature.fields()] else ""
                    if sector_actual and str(sector_actual) != str(sector_actual).upper():
                        idx_sector = capa.fields().indexOf("Sector")
                        if idx_sector >= 0:
                            capa.changeAttributeValue(fid, idx_sector, str(sector_actual).upper())
                            cambios_realizados = True
                except (KeyError, AttributeError):
                    pass
                
                # Actualizar campo Relleno a mayúsculas
                try:
                    relleno_actual = feature["Relleno"] if "Relleno" in [field.name() for field in feature.fields()] else ""
                    if relleno_actual and str(relleno_actual) != str(relleno_actual).upper():
                        idx_relleno = capa.fields().indexOf("Relleno")
                        if idx_relleno >= 0:
                            capa.changeAttributeValue(fid, idx_relleno, str(relleno_actual).upper())
                            cambios_realizados = True
                except (KeyError, AttributeError):
                    pass
                
                # Actualizar NombreArchivo a mayúsculas (solo el nombre, no la ruta)
                try:
                    nombre_archivo = feature["NombreArchivo"] if "NombreArchivo" in [field.name() for field in feature.fields()] else ""
                    if nombre_archivo:
                        nombre_normalizado = self.normalizar_nombre_campo(nombre_archivo)
                        if nombre_archivo != nombre_normalizado:
                            idx_nombre = capa.fields().indexOf("NombreArchivo")
                            if idx_nombre >= 0:
                                capa.changeAttributeValue(fid, idx_nombre, nombre_normalizado)
                                cambios_realizados = True
                except (KeyError, AttributeError):
                    pass
                
                # Actualizar Foto a mayúsculas (solo el nombre, no la ruta)
                try:
                    foto = feature["Foto"] if "Foto" in [field.name() for field in feature.fields()] else ""
                    if foto:
                        foto_normalizada = self.normalizar_nombre_campo(foto)
                        if foto != foto_normalizada:
                            idx_foto = capa.fields().indexOf("Foto")
                            if idx_foto >= 0:
                                capa.changeAttributeValue(fid, idx_foto, foto_normalizada)
                                cambios_realizados = True
                except (KeyError, AttributeError):
                    pass
                
                if cambios_realizados:
                    total_actualizados += 1
            
            capa.commitChanges()
            # self.log_callback(f"✅ Campos del GPKG actualizados: {total_actualizados} registros")
            
        except Exception as e:
            capa.rollBack()
            self.log_callback(f"❌ Error actualizando campos del GPKG: {e}")
    
    def normalizar_nombre_campo(self, nombre_campo):
        """Normaliza un campo de nombre (archivo o foto) manteniendo estructura de carpetas"""
        if not nombre_campo:
            return nombre_campo
            
        # Si tiene ruta, separar directorio y archivo
        if "/" in nombre_campo or "\\" in nombre_campo:
            partes = nombre_campo.replace("\\", "/").split("/")
            nombre_archivo = partes[-1]  # Último elemento es el archivo
            ruta_carpetas = "/".join(partes[:-1])  # Todo excepto el último
            
            # Normalizar solo el nombre del archivo
            if "." in nombre_archivo:
                nombre_sin_ext, extension = nombre_archivo.rsplit(".", 1)
                nombre_normalizado = nombre_sin_ext.upper() + "." + extension.lower()
            else:
                nombre_normalizado = nombre_archivo.upper()
            
            return ruta_carpetas + "/" + nombre_normalizado
        else:
            # Solo nombre de archivo, sin ruta
            if "." in nombre_campo:
                nombre_sin_ext, extension = nombre_campo.rsplit(".", 1)
                return nombre_sin_ext.upper() + "." + extension.lower()
            else:
                return nombre_campo.upper()
    
    def validar_nomenclatura_con_gpkg(self, capa):
        """Valida que la nomenclatura de archivos coincida con datos del GPKG"""
        # self.log_callback("🔍 Validando nomenclatura con datos del GPKG...")
        
        errores_nomenclatura = []
        coincidencias = 0
        
        for feature in capa.getFeatures():
            try:
                # Obtener datos del GPKG usando acceso seguro
                try:
                    fecha_gpkg = feature["Fecha"] if "Fecha" in [field.name() for field in feature.fields()] else ""
                except (KeyError, AttributeError):
                    fecha_gpkg = ""
                
                try:
                    muro_gpkg = feature["Muro"] if "Muro" in [field.name() for field in feature.fields()] else ""
                except (KeyError, AttributeError):
                    muro_gpkg = ""
                
                try:
                    sector_gpkg = feature["Sector"] if "Sector" in [field.name() for field in feature.fields()] else ""
                except (KeyError, AttributeError):
                    sector_gpkg = ""
                
                try:
                    relleno_gpkg = feature["Relleno"] if "Relleno" in [field.name() for field in feature.fields()] else ""
                except (KeyError, AttributeError):
                    relleno_gpkg = ""
                
                try:
                    archivo_csv = feature["NombreArchivo"] if "NombreArchivo" in [field.name() for field in feature.fields()] else ""
                except (KeyError, AttributeError):
                    archivo_csv = ""
                
                try:
                    archivo_foto = feature["Foto"] if "Foto" in [field.name() for field in feature.fields()] else ""
                except (KeyError, AttributeError):
                    archivo_foto = ""
                
                if not all([fecha_gpkg, muro_gpkg, sector_gpkg, relleno_gpkg]):
                    continue
                
                # Construir nombre esperado desde GPKG (convertir todo a mayúsculas)
                fecha_formato = self.extraer_fecha_formato(str(fecha_gpkg))
                if not fecha_formato:
                    continue
                    
                nombre_esperado = f"{fecha_formato}_{str(muro_gpkg).upper()}_{str(sector_gpkg).upper()}_{str(relleno_gpkg).upper()}"
                
                # Validar archivo CSV
                if archivo_csv:
                    nombre_csv_limpio = self.extraer_nombre_archivo(archivo_csv)
                    if nombre_csv_limpio != nombre_esperado:
                        errores_nomenclatura.append({
                            'tipo': 'CSV',
                            'archivo': archivo_csv,
                            'esperado': nombre_esperado,
                            'encontrado': nombre_csv_limpio,
                            'gpkg_data': f"Fecha:{fecha_gpkg}, Muro:{str(muro_gpkg).upper()}, Sector:{str(sector_gpkg).upper()}, Relleno:{str(relleno_gpkg).upper()}"
                        })
                    else:
                        coincidencias += 1
                
                # Validar archivo FOTO
                if archivo_foto:
                    nombre_foto_limpio = self.extraer_nombre_archivo(archivo_foto)
                    if nombre_foto_limpio != nombre_esperado:
                        errores_nomenclatura.append({
                            'tipo': 'FOTO',
                            'archivo': archivo_foto,
                            'esperado': nombre_esperado,
                            'encontrado': nombre_foto_limpio,
                            'gpkg_data': f"Fecha:{fecha_gpkg}, Muro:{str(muro_gpkg).upper()}, Sector:{str(sector_gpkg).upper()}, Relleno:{str(relleno_gpkg).upper()}"
                        })
                    else:
                        coincidencias += 1
                        
            except Exception as e:
                self.log_callback(f"⚠️ Error validando feature {feature.id()}: {e}")
        
        # Reportar resultados
        # Solo logear si hay errores
        # self.log_callback(f"📊 Resultado validación nomenclatura:")
        # self.log_callback(f"   ✅ Coincidencias: {coincidencias}")
        # self.log_callback(f"   ❌ Errores: {len(errores_nomenclatura)}")
        
        if errores_nomenclatura:
            self.log_callback(f"\n🔍 ERRORES DE NOMENCLATURA:")
            for error in errores_nomenclatura[:10]:  # Mostrar solo los primeros 10
                self.log_callback(f"   📁 {error['tipo']}: {error['archivo']}")
                self.log_callback(f"      Esperado: {error['esperado']}")
                self.log_callback(f"      Encontrado: {error['encontrado']}")
                self.log_callback(f"      Datos GPKG: {error['gpkg_data']}")
                self.log_callback("")
            if len(errores_nomenclatura) > 10:
                self.log_callback(f"   ... y {len(errores_nomenclatura) - 10} errores más")
    
    def extraer_fecha_formato(self, fecha_str):
        """Extrae fecha en formato YYMMDD desde string de fecha"""
        try:
            from datetime import datetime
            # Intentar varios formatos de fecha
            formatos = ["%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"]
            
            for formato in formatos:
                try:
                    fecha_dt = datetime.strptime(fecha_str.split(' ')[0], formato)  # Solo la parte de fecha
                    return fecha_dt.strftime("%y%m%d")  # Formato YYMMDD
                except ValueError:
                    continue
            return None
        except Exception:
            return None
    
    def extraer_nombre_archivo(self, ruta_archivo):
        """Extrae el nombre del archivo sin ruta y sin extensión"""
        try:
            # Remover ruta (tanto / como \)
            nombre_con_ext = os.path.basename(ruta_archivo)
            # Remover extensión
            nombre_sin_ext = os.path.splitext(nombre_con_ext)[0]
            return nombre_sin_ext.upper()
        except Exception:
            return ""

    # =========================
    # MÉTODO PRINCIPAL
    # =========================

    def ejecutar_validacion_completa(self):
        """Ejecutar todo el proceso de validación - MÉTODO PRINCIPAL"""
        try:
            self.progress_callback(5, "Iniciando validación completa...")
            self.log_callback("🔍 Iniciando validación completa...")
            
            # Asegurar carpetas
            self.progress_callback(10, "Creando estructura de carpetas...")
            self.asegurar_carpetas()
            
            # Copiar GPKG
            self.progress_callback(15, "Copiando GPKG original...")
            shutil.copy2(self.ORIG_GPKG, self.TMP_GPKG)
            
            # Cargar capa
            self.progress_callback(20, "Cargando capa de levantamientos...")
            uri = f"{self.TMP_GPKG}|layername={self.NOMBRE_CAPA}"
            layer = QgsVectorLayer(uri, self.NOMBRE_CAPA, "ogr")
            if not layer.isValid():
                raise Exception(f"No se pudo cargar la capa desde {self.TMP_GPKG}")
            
            # Normalizar rutas de archivos PRIMERO (para eliminar prefijos largos)
            self.progress_callback(25, "Normalizando rutas de archivos...")
            self.actualizar_nombres_capa(layer)
            
            # Normalizar nombres a mayúsculas y validar nomenclatura
            self.progress_callback(30, "Normalizando nombres y validando nomenclatura...")
            self.normalizar_nombres_y_validar_nomenclatura(layer)
            
            # ⚡ DETECCIÓN INTELIGENTE DE ERRORES HUMANOS
            self.progress_callback(35, "Detectando errores y duplicados...")
            errores, advertencias = self.detectar_errores_humanos(layer)
            
            if errores or advertencias:
                self.log_callback("\n" + "="*70)
                if errores:
                    self.log_callback("❌ ERRORES CRÍTICOS DETECTADOS:")
                    for error in errores:
                        self.log_callback(f"   {error}")
                
                if advertencias:
                    self.log_callback("\n⚠️ ADVERTENCIAS:")
                    for adv in advertencias:
                        self.log_callback(f"   {adv}")
                self.log_callback("="*70 + "\n")
            
            # Agregar al proyecto si no existe (sin log)
            project = QgsProject.instance()
            if not any(lyr.name() == self.NOMBRE_CAPA for lyr in project.mapLayers().values()):
                project.addMapLayer(layer)
            
            # Backup completo
            self.progress_callback(40, "Creando backup completo...")
            carpeta_b = self.respaldo_completo()
            
            # Procesar y validar archivos (progreso 50-80 dentro del método)
            self.progress_callback(50, "Procesando y validando archivos...")
            self.procesar_archivos_y_validar(layer, carpeta_b)
            
            # Limpiar auxiliares
            self.progress_callback(90, "Limpiando archivos auxiliares...")
            self.limpiar_archivos_auxiliares()
            
            self.progress_callback(100, "¡Validación completada!")
            # Crear resumen final conciso (se genera en procesar_archivos_y_validar)
            
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

    def generar_reporte_detallado(self):
        """Genera un reporte CONCISO enfocado en errores y resúmenes"""
        stats = self.stats_procesamiento
        counters = self.log_counters
        
        self.log_callback("\n" + "="*70)
        self.log_callback("📊 RESUMEN DE VALIDACIÓN")
        self.log_callback("="*70)
        
        # Resumen de archivos procesados (UNA SOLA LÍNEA)
        total_procesados = stats['archivos_exitosos'] + len(stats['archivos_asc_procesados'])
        self.log_callback(f"✅ Procesados: {stats['archivos_exitosos']} CSV + {len(stats['archivos_asc_procesados'])} ASC = {total_procesados} archivos")
        
        # Solo mostrar si hay errores
        if stats['archivos_con_errores'] > 0:
            self.log_callback(f"❌ Con errores: {stats['archivos_con_errores']}")
            self.log_callback("\n🔍 DETALLE DE ERRORES:")
            for archivo, error in stats['errores_por_archivo'].items():
                self.log_callback(f"   • {archivo}: {error}")
        
        
        self.log_callback("="*70)