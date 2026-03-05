# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime
from qgis.core import (
    QgsPointXY, QgsGeometry, QgsField, QgsProject,
    QgsCoordinateTransform, QgsCoordinateReferenceSystem
)
from qgis.PyQt.QtCore import QVariant

class LabReportLoader:
    """
    Clase para cargar reportes de laboratorio desde Excel y enriquecer la capa de canchas.
    Maneja parsing de coordenadas y lógica estricta de cruce.
    """

    def __init__(self, log_callback=None):
        self.log_callback = log_callback or (lambda x: None)
        self.column_mapping = {
            'fecha': 0,      # Columna A: Fecha de control
            'muro': 1,       # Columna B: Muro
            'sector': 3,     # Columna D: Sector (Ojo: Revisar índice exacto 0-based)
            'capa': 4,       # Columna E: Capa N°
            'plataforma': 2, # Columna C: Plataforma
            'coord': 7,      # Columna H: Coordenadas
            'n_informe_1': 14, # Columna O: N° de Informe (Indice 14 si A=0)
            'n_informe_2': 27  # Columna AB: Informe (Indice 27 aprox, verificar)
        }
        # Índices 0-based estimados de la imagen:
        # A=0, B=1, C=2, D=3, E=4, F=5, G=6, H=7... O=14... AB=27
        
    def load_excel_and_enrich(self, excel_path, layer):
        """
        Carga el Excel y actualiza la capa 'layer' con el N° de Informe.
        Retorna (success, message, contadores)
        """
        if not os.path.exists(excel_path):
            return False, f"Archivo no encontrado: {excel_path}", {}

        try:
            import openpyxl
        except ImportError:
            return False, "Librería 'openpyxl' no instalada. No se puede leer Excel.", {}

        self.log_callback(f"📂 Cargando reporte de laboratorio: {os.path.basename(excel_path)}")

        try:
            wb = openpyxl.load_workbook(excel_path, data_only=True)
            sheet = wb.active
            
            # 1. Asegurar campo en la capa
            field_name = "N_Ensayo"
            idx_field = layer.fields().indexOf(field_name)
            if idx_field == -1:
                self.log_callback(f"✨ Creando campo '{field_name}' en tabla de atributos...")
                layer.dataProvider().addAttributes([QgsField(field_name, QVariant.String)])
                layer.updateFields()
                idx_field = layer.fields().indexOf(field_name)
            
            count_matches = 0
            count_errors = 0
            rows_processed = 0
            
            # Contadores de rechazo para diagnóstico
            count_no_coord = 0
            count_no_informe = 0
            count_no_spatial = 0
            count_reject_fecha = 0
            count_reject_muro = 0
            count_reject_sector = 0
            unmatched_rows = []  # Para resumen final
            
            # Iniciar edición
            layer.startEditing()
            
            # Pre-cachear features para no reiterar la capa
            features_cache = list(layer.getFeatures())
            self.log_callback(f"📋 Canchas en capa: {len(features_cache)}")
            
            # Iterar filas del Excel (Saltar cabecera, asumiendo fila 5 son headers, fila 6 datos)
            for row_idx, row in enumerate(sheet.iter_rows(min_row=6, values_only=True), start=6):
                if not row[self.column_mapping['coord']]: # Si no hay coordenada, saltar
                    count_no_coord += 1
                    continue
                    
                rows_processed += 1
                
                # Extraer datos
                raw_coord = str(row[self.column_mapping['coord']])
                raw_fecha = row[self.column_mapping['fecha']]
                raw_muro = str(row[self.column_mapping['muro']]).strip() if row[self.column_mapping['muro']] else ""
                raw_sector = str(row[self.column_mapping['sector']]).strip() if row[self.column_mapping['sector']] else ""
                raw_capa = str(row[self.column_mapping['capa']]).strip() if row[self.column_mapping['capa']] else ""
                
                # N° Informe (Prioridad Col O, luego AB)
                n_informe = row[self.column_mapping['n_informe_1']]
                if not n_informe:
                    n_informe = row[self.column_mapping['n_informe_2']]
                
                if not n_informe:
                    count_no_informe += 1
                    continue
                    
                n_informe_str = str(n_informe).strip()
                
                # Parsear Coordenadas
                pt_geom = self._parse_coordinate(raw_coord)
                if not pt_geom:
                    count_errors += 1
                    continue
                
                # Normalizar fecha Excel (datetime a date)
                date_obj = None
                if isinstance(raw_fecha, datetime):
                    date_obj = raw_fecha.date()
                elif isinstance(raw_fecha, str):
                    # Intentar parsing básico si es string
                    try:
                        date_obj = datetime.strptime(raw_fecha, "%d-%m-%Y").date()
                    except:
                        pass
                
                # Debug de primera fila o filas con error
                if rows_processed <= 5: 
                    self.log_callback(f"🔍 Debug Fila {row_idx}: Fecha='{date_obj}', Muro='{raw_muro}', Sector='{raw_sector}', Coord={pt_geom.asWkt() if pt_geom else 'None'}")

                # BÚSQUEDA ESPACIAL Y MATCHING
                match_found = False
                closest_dist = float('inf')
                closest_id = None
                closest_name = ""
                reject_reason = ""  # Razón del último rechazo
                
                # Iterar canchas
                for feature in features_cache:
                    # Calculo de distancia (0 si está dentro)
                    dist = feature.geometry().distance(pt_geom)
                    
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_id = feature.id()
                        closest_name = feature['Protocolo Topografico'] if feature['Protocolo Topografico'] else str(feature.id())
                    
                    # 1. Check Espacial (tolerancia 2 metros)
                    if dist > 2.0:
                        continue
                        
                    # CANDIDATO ESPACIAL ENCONTRADO
                    
                    # 2. Check Fecha (con logica segura)
                    feat_fecha_val = feature['Fecha']
                    feat_date = None
                    if feat_fecha_val:
                        if hasattr(feat_fecha_val, 'toPyDate'):
                             feat_date = feat_fecha_val.toPyDate()
                        elif isinstance(feat_fecha_val, str):
                            try:
                                feat_date = datetime.strptime(feat_fecha_val, "%Y-%m-%d").date()
                            except:
                                pass
                        else:
                            feat_date = feat_fecha_val
                            
                    # Comparación fecha
                    dates_match = False
                    if str(feat_date) == str(date_obj):
                        dates_match = True
                        
                    if not dates_match:
                        reject_reason = f"FECHA: Excel({date_obj}) != Cancha({feat_date})"
                        count_reject_fecha += 1
                        continue
                        
                    # 3. Check Metadata (Muro/Sector)
                    feat_muro = str(feature['Muro']).strip() if feature['Muro'] else ""
                    feat_sector = str(feature['Sector']).strip() if feature['Sector'] else ""
                    
                    # Logica Muro: Si Excel tiene muro, Cancha debe coincidir
                    if raw_muro and feat_muro:
                        m_excel = raw_muro.upper()
                        m_feat = feat_muro.upper()
                        
                        # Alias comunes
                        if m_excel == "MP": m_excel = "PRINCIPAL"
                        if m_feat == "MP": m_feat = "PRINCIPAL"
                        
                        if m_excel != m_feat:
                            reject_reason = f"MURO: Excel({raw_muro}) != Cancha({feat_muro})"
                            count_reject_muro += 1
                            continue
                    
                    # Logica Sector: "4" in "Sector 4"
                    if raw_sector and feat_sector:
                        # Limpieza básica
                        s_excel = raw_sector.upper().replace("SECTOR", "").strip()
                        s_feat = feat_sector.upper().replace("SECTOR", "").strip()
                        if s_excel != s_feat:
                             reject_reason = f"SECTOR: Excel({raw_sector}) != Cancha({feat_sector})"
                             count_reject_sector += 1
                             continue
                    
                    # ASIGNAR Y SALIR DEL LOOP DE FEATURES
                    feat_name = feature['Protocolo Topografico'] if feature['Protocolo Topografico'] else str(feature.id())
                    self.log_callback(f"✅ MATCH ENCONTRADO! Fila {row_idx} -> Cancha ID {feature.id()} ({feat_name})")
                    feature[field_name] = n_informe_str
                    layer.updateFeature(feature)
                    match_found = True
                    count_matches += 1
                    break 
                
                if not match_found:
                    # Determinar razón principal
                    if closest_dist > 2.0:
                        reject_reason = f"FUERA DE RANGO ESPACIAL (distancia mínima: {closest_dist:.1f}m a '{closest_name}')"
                        count_no_spatial += 1
                    
                    # Loguear TODAS las filas sin match
                    self.log_callback(f"  ⚠️ SIN MATCH Fila {row_idx}: Fecha={date_obj}, Muro={raw_muro}, Sector={raw_sector}, Informe={n_informe_str} → {reject_reason}")
                    unmatched_rows.append({
                        'fila': row_idx,
                        'fecha': str(date_obj),
                        'muro': raw_muro,
                        'sector': raw_sector,
                        'razon': reject_reason,
                        'dist_min': closest_dist,
                        'cancha_cercana': closest_name
                    })
            
            layer.commitChanges()
            
            # ═══════════════════════════════════════════════════
            # RESUMEN DETALLADO DE MATCHING
            # ═══════════════════════════════════════════════════
            self.log_callback(f"")
            self.log_callback(f"{'═'*60}")
            self.log_callback(f"📊 RESUMEN DE MATCHING LABORATORIO")
            self.log_callback(f"{'═'*60}")
            self.log_callback(f"  📋 Filas en Excel con coordenada: {rows_processed}")
            self.log_callback(f"  🚫 Filas sin coordenada (saltadas): {count_no_coord}")
            self.log_callback(f"  🚫 Filas sin N° Informe (saltadas): {count_no_informe}")
            self.log_callback(f"  ❌ Filas con error de parseo coord: {count_errors}")
            self.log_callback(f"  ✅ Matches exitosos: {count_matches}")
            self.log_callback(f"  ❌ Sin match: {len(unmatched_rows)}")
            self.log_callback(f"{'─'*60}")
            self.log_callback(f"  📊 DESGLOSE DE RECHAZOS:")
            self.log_callback(f"    🗺️ Fuera de rango espacial (>2m): {count_no_spatial}")
            self.log_callback(f"    📅 Fecha no coincide: {count_reject_fecha}")
            self.log_callback(f"    🧱 Muro no coincide: {count_reject_muro}")
            self.log_callback(f"    📍 Sector no coincide: {count_reject_sector}")
            
            # Agrupar sin-match por fecha para detectar patrones
            if unmatched_rows:
                from collections import Counter
                fechas_sin_match = Counter(r['fecha'] for r in unmatched_rows)
                self.log_callback(f"{'─'*60}")
                self.log_callback(f"  📅 FECHAS CON MÁS FILAS SIN MATCH:")
                for fecha, cnt in fechas_sin_match.most_common(10):
                    self.log_callback(f"    {fecha}: {cnt} filas sin match")
                
                razones_sin_match = Counter(r['razon'].split(':')[0] for r in unmatched_rows if r['razon'])
                self.log_callback(f"{'─'*60}")
                self.log_callback(f"  🔍 RAZONES PRINCIPALES:")
                for razon, cnt in razones_sin_match.most_common():
                    self.log_callback(f"    {razon}: {cnt}")
            
            self.log_callback(f"{'═'*60}")
            
            return True, f"Proceso completado. {count_matches} ensayos asignados de {rows_processed} filas procesadas.", {'matches': count_matches}

        except Exception as e:
            layer.rollBack()
            import traceback
            traceback.print_exc()
            return False, f"Error procesando Excel: {str(e)}", {}

    def _parse_coordinate(self, coord_str):
        """
        Extrae N y E de string tipo "N: 6334524.989 E: 337428.330"
        o "N:6334524.989\nE:337428.330"
        Retorna QgsGeometry (Punto) o None.
        """
        if not coord_str: return None
        
        # Normalizar string (quitar saltos de linea)
        s = coord_str.replace("\n", " ").replace("\r", " ").upper()
        
        # Regex flexible
        # Busca N seguido de numero, y E seguido de numero
        try:
            match_n = re.search(r'N\s*[:]\s*([\d\.]+)', s)
            match_e = re.search(r'E\s*[:]\s*([\d\.]+)', s)
            
            if match_n and match_e:
                northing = float(match_n.group(1))
                easting = float(match_e.group(1))
                return QgsGeometry.fromPointXY(QgsPointXY(easting, northing))
        except:
            return None
            
        return None
