# -*- coding: utf-8 -*-
"""
Generador de gráficos de series temporales
Basado directamente en consulta_GRAFICO_SERIE_TEMPORTAL_colores.py
"""
import os
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from qgis.core import QgsProject

class TimeSeriesChartGenerator:
    """
    Generador de gráficos de series temporales que replica exactamente el comportamiento
    del script consulta_GRAFICO_SERIE_TEMPORTAL_colores.py
    """
    
    def __init__(self, proc_root="", progress_callback=None, log_callback=None):
        self.proc_root = proc_root
        self.progress_callback = progress_callback
        self.log_callback = log_callback
    
    def log_message(self, message):
        """Registrar mensaje en el log"""
        if self.log_callback:
            self.log_callback(message)
    
    def update_progress(self, value, message=""):
        """Actualizar barra de progreso"""
        if self.progress_callback:
            self.progress_callback(value, message)
    
    def generar_graficos_series_temporales(self):
        """
        Genera gráficos de series temporales para cada registro de la Tabla Base Datos
        usando exactamente la misma lógica que consulta_GRAFICO_SERIE_TEMPORTAL_colores.py
        """
        try:
            # Crear carpetas
            if not self.proc_root:
                self.log_message("❌ Error: No se ha configurado la carpeta de procesamiento")
                return {'success': False, 'message': 'No hay carpeta de procesamiento configurada'}
            
            carpeta_aux = os.path.join(self.proc_root, "Aux Reporte")
            carpeta_series = os.path.join(carpeta_aux, "Grafico Series")
            os.makedirs(carpeta_aux, exist_ok=True)
            os.makedirs(carpeta_series, exist_ok=True)
            self.log_message(f"📁 Carpeta de gráficos de series creada: {carpeta_series}")
            
            # Obtener capas - exactamente como en el script original
            tabla_base_layer = None
            datos_historicos_layer = None
            
            for layer in QgsProject.instance().mapLayers().values():
                if layer.name() == "Tabla Base Datos":
                    tabla_base_layer = layer
                elif layer.name() == "DATOS HISTORICOS":
                    datos_historicos_layer = layer
            
            if not tabla_base_layer:
                self.log_message("❌ No se encontró 'Tabla Base Datos'")
                return {'success': False, 'message': 'No se encontró Tabla Base Datos'}
            
            if not datos_historicos_layer:
                self.log_message("❌ No se encontró 'DATOS HISTORICOS'")  
                return {'success': False, 'message': 'No se encontró DATOS HISTORICOS'}
            
            # Debug: ver campos disponibles
            self.log_message(f"🔍 Campos en Tabla Base Datos: {[f.name() for f in tabla_base_layer.fields()]}")
            
            # Verificar si existe la columna 'G2', si no existe, crearla
            field_names = [field.name() for field in tabla_base_layer.fields()]
            if 'G2' not in field_names:
                self.log_message("🔧 Creando columna 'G2' en Tabla Base Datos...")
                from qgis.core import QgsField
                from qgis.PyQt.QtCore import QVariant
                
                # Crear el campo G2
                new_field = QgsField('G2', QVariant.String, len=255)
                
                # Agregar el campo a la capa
                tabla_base_layer.dataProvider().addAttributes([new_field])
                tabla_base_layer.updateFields()
                self.log_message("✅ Columna 'G2' creada exitosamente")
            else:
                self.log_message("ℹ️ La columna 'G2' ya existe en la tabla")
            
            total_registros = tabla_base_layer.featureCount()
            self.log_message(f"🔍 Procesando {total_registros} registros para generar gráficos de series temporales")
            
            graficos_generados = 0
            graficos_fallidos = 0
            
            # Procesar cada feature en tabla base
            for i, feature in enumerate(tabla_base_layer.getFeatures()):
                progress = int((i + 1) / total_registros * 100)
                self.update_progress(progress, f"Generando serie temporal {i+1}/{total_registros}")
                self.log_message(f"📋 Generando serie temporal {i+1}/{total_registros}")
                
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
                        graficos_fallidos += 1
                        continue
                    
                    if not sector:
                        self.log_message(f"⚠️ Registro {i+1}: no se encontró campo Sector")
                        sector = "SIN_SECTOR"
                    
                    if not relleno:
                        self.log_message(f"⚠️ Registro {i+1}: no se encontró campo Relleno")
                        relleno = "SIN_RELLENO"
                    
                    # Generar gráfico usando la lógica exacta del script original
                    nombre_archivo_generado = self.generar_grafico_serie_temporal_individual(
                        datos_historicos_layer, 
                        muro, 
                        sector,
                        fecha_str, 
                        relleno,
                        carpeta_series,
                        i + 1
                    )
                    
                    if nombre_archivo_generado:
                        # Actualizar el campo G2 con el nombre del archivo generado
                        self.actualizar_campo_g2(tabla_base_layer, feature, nombre_archivo_generado)
                        graficos_generados += 1
                    else:
                        graficos_fallidos += 1
                        
                except Exception as e:
                    self.log_message(f"❌ Error en registro {i+1}: {str(e)}")
                    graficos_fallidos += 1
            
            self.log_message(f"✅ Generación de gráficos de series temporales completada")
            self.log_message(f"📊 {graficos_generados} gráficos generados correctamente")
            if graficos_fallidos > 0:
                self.log_message(f"⚠️ {graficos_fallidos} gráficos no pudieron generarse")
            
            return {
                'success': True,
                'message': 'Generación de gráficos de series temporales completada',
                'graficos_generados': graficos_generados,
                'graficos_fallidos': graficos_fallidos,
                'total_registros': total_registros,
                'carpeta_salida': carpeta_series
            }
            
        except Exception as e:
            import traceback
            self.log_message(f"❌ Error general: {str(e)}")
            self.log_message(f"📋 Detalles: {traceback.format_exc()}")
            return {
                'success': False,
                'message': f'Error en la generación de gráficos de series temporales: {str(e)}',
                'details': traceback.format_exc()
            }
    
    def actualizar_campo_g2(self, tabla_base_layer, feature, nombre_archivo):
        """
        Actualiza el campo G2 del feature con el nombre del archivo generado
        """
        try:
            # Iniciar edición
            tabla_base_layer.startEditing()
            
            # Actualizar el campo G2
            field_index = tabla_base_layer.fields().indexFromName('G2')
            if field_index != -1:
                tabla_base_layer.changeAttributeValue(feature.id(), field_index, nombre_archivo)
                
            # Guardar cambios
            tabla_base_layer.commitChanges()
            self.log_message(f"📝 Campo G2 actualizado para feature {feature.id()}: {nombre_archivo}")
            
        except Exception as e:
            self.log_message(f"⚠️ Error al actualizar campo G2: {str(e)}")
            tabla_base_layer.rollBack()
    
    def generar_grafico_serie_temporal_individual(self, datos_historicos_layer, muro, sector, fecha_str, relleno, carpeta_salida, num_registro):
        """
        Replica exactamente la lógica de consulta_GRAFICO_SERIE_TEMPORTAL_colores.py
        
        Returns:
            str: Nombre del archivo generado si fue exitoso, None si hubo error
        """
        try:
            # -------------------------
            # Recolectar datos (EXACTAMENTE igual al script original)
            # -------------------------
            data = []
            for f in datos_historicos_layer.getFeatures():
                if f["Muro"] == muro and f["Sector"] == sector:
                    f_fecha_str = f["Fecha"]
                    f_espesor_str = f["Espesor"]
                    if f_fecha_str and f_espesor_str:
                        try:
                            f_fecha_dt = datetime.strptime(str(f_fecha_str), "%Y-%m-%d")
                            f_espesor_val = float(str(f_espesor_str).replace(",", "."))
                            data.append((f_fecha_dt, f_espesor_val))
                        except:
                            pass
            
            # Verificar que haya datos
            if not data:
                self.log_message(f"⚠️ No hay datos para Muro '{muro}', Sector '{sector}'")
                return None
            
            # -------------------------
            # Crear dataframe ordenado (EXACTAMENTE igual al script original)
            # -------------------------
            df = pd.DataFrame(data, columns=["Fecha", "Espesor"])
            df = df.sort_values("Fecha")
            
            # Convertir a listas para matplotlib
            fechas = df["Fecha"].tolist()
            espesores = df["Espesor"].tolist()
            
            # -------------------------
            # Graficar con mejor legibilidad para PDFs
            # -------------------------
            plt.figure(figsize=(12,6))  # Figura ligeramente más alta
            
            # línea principal más gruesa
            plt.plot(fechas, espesores, color="black", linewidth=2.5, label="ESPESOR")
            
            # área positiva
            plt.fill_between(fechas, espesores, 0, where=[e>0 for e in espesores],
                             interpolate=True, color="green", alpha=0.3)
            
            # área negativa
            plt.fill_between(fechas, espesores, 0, where=[e<0 for e in espesores],
                             interpolate=True, color="red", alpha=0.3)
            
            # puntos individuales verde/rojo más grandes
            for f, e in zip(fechas, espesores):
                color = "green" if e > 0 else "red"
                plt.scatter(f, e, color=color, s=60, zorder=3)  # Puntos más grandes
            
            # línea de referencia en 0 más gruesa
            plt.axhline(0, color="gray", linestyle="--", linewidth=2)
            
            # títulos y estilo con fuentes más grandes para mejor legibilidad en PDFs - TODO EN MAYÚSCULAS
            plt.title(f"SERIE ANUAL DEL ESPESOR - MURO {muro.upper()} {sector.upper()}", fontsize=24, fontweight='bold', pad=20)
            plt.xlabel("FECHA", fontsize=20, fontweight='bold')
            plt.ylabel("ESPESOR", fontsize=20, fontweight='bold')
            
            # Etiquetas de valores en los ejes más grandes
            plt.xticks(fontsize=16)
            plt.yticks(fontsize=16)
            
            # Ajustar tamaño de la leyenda
            plt.legend(fontsize=16)
            
            plt.grid(True)
            plt.tight_layout()
            
            # Generar nombre de archivo con nueva nomenclatura: G2{fecha}_{muro}_{sector}_{relleno}.png
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
            
            # Nomenclatura final: G2{fecha}_{muro}_{sector}_{relleno}.png
            # Ejemplo: G2250820_MP_S1_Arenafina.png
            nombre_archivo = f"G2{fecha_procesada}_{muro_procesado}_{sector_procesado}_{relleno_procesado}.png"
            ruta_completa = os.path.join(carpeta_salida, nombre_archivo)
            
            # En lugar de plt.show(), guardamos a archivo
            plt.savefig(ruta_completa, dpi=200, bbox_inches='tight')  # DPI más alto y mejor ajuste
            plt.close()
            
            self.log_message(f"✅ Serie temporal generada: {nombre_archivo}")
            return nombre_archivo  # Retornar el nombre del archivo
            
        except Exception as e:
            self.log_message(f"❌ Error al generar serie temporal para registro {num_registro}: {str(e)}")
            import traceback
            self.log_message(traceback.format_exc())
            return None