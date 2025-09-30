# -*- coding: utf-8 -*-
"""
Generador de gráficos de barras simplificado
Basado directamente en consulta_GRAFICO_BARRAS_canchas_sector.py
"""
import os
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from matplotlib.ticker import MaxNLocator
from qgis.core import QgsProject

class SimpleBarChartGenerator:
    """
    Generador de gráficos simplificado que replica exactamente el comportamiento
    del script consulta_GRAFICO_BARRAS_canchas_sector.py
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
    
    def generar_graficos_barras(self):
        """
        Genera gráficos de barras para cada registro de la Tabla Base Datos
        usando exactamente la misma lógica que consulta_GRAFICO_BARRAS_canchas_sector.py
        """
        try:
            # Crear carpetas
            if not self.proc_root:
                self.log_message("❌ Error: No se ha configurado la carpeta de procesamiento")
                return {'success': False, 'message': 'No hay carpeta de procesamiento configurada'}
            
            carpeta_aux = os.path.join(self.proc_root, "Aux Reporte")
            carpeta_barras = os.path.join(carpeta_aux, "Grafico Barras")
            os.makedirs(carpeta_aux, exist_ok=True)
            os.makedirs(carpeta_barras, exist_ok=True)
            self.log_message(f"📁 Carpeta de gráficos creada: {carpeta_barras}")
            
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
            
            # Verificar si existe la columna 'G1', si no existe, crearla
            field_names = [field.name() for field in tabla_base_layer.fields()]
            if 'G1' not in field_names:
                self.log_message("🔧 Creando columna 'G1' en Tabla Base Datos...")
                from qgis.core import QgsField
                from qgis.PyQt.QtCore import QVariant
                
                # Crear el campo G1
                new_field = QgsField('G1', QVariant.String, len=255)
                
                # Agregar el campo a la capa
                tabla_base_layer.dataProvider().addAttributes([new_field])
                tabla_base_layer.updateFields()
                self.log_message("✅ Columna 'G1' creada exitosamente")
            else:
                self.log_message("ℹ️ La columna 'G1' ya existe en la tabla")
            
            total_registros = tabla_base_layer.featureCount()
            self.log_message(f"🔍 Procesando {total_registros} registros para generar gráficos de barras")
            
            graficos_generados = 0
            graficos_fallidos = 0
            
            # Procesar cada feature en tabla base
            for i, feature in enumerate(tabla_base_layer.getFeatures()):
                progress = int((i + 1) / total_registros * 100)
                self.update_progress(progress, f"Generando gráfico {i+1}/{total_registros}")
                self.log_message(f"📋 Generando gráfico {i+1}/{total_registros}")
                
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
                    
                    # Buscar campo protocolo con diferentes nombres posibles
                    protocolo = None
                    for field_name in ["Protocolo Topográfico", "Protocolo_Topográfico", "Protocolo", "protocolo", "PT", "pt"]:
                        try:
                            protocolo = feature[field_name]
                            if protocolo:
                                break
                        except:
                            continue
                    
                    if not protocolo:
                        # Usar el índice como protocolo si no se encuentra
                        protocolo = i + 1
                        self.log_message(f"⚠️ No se encontró campo protocolo, usando índice: {protocolo}")
                    
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
                    nombre_archivo_generado = self.generar_grafico_individual(
                        datos_historicos_layer, 
                        muro, 
                        fecha_str, 
                        sector,
                        relleno,
                        protocolo, 
                        carpeta_barras,
                        i + 1
                    )
                    
                    if nombre_archivo_generado:
                        # Actualizar el campo G1 con el nombre del archivo generado
                        self.actualizar_campo_g1(tabla_base_layer, feature, nombre_archivo_generado)
                        graficos_generados += 1
                    else:
                        graficos_fallidos += 1
                        
                except Exception as e:
                    self.log_message(f"❌ Error en registro {i+1}: {str(e)}")
                    graficos_fallidos += 1
            
            self.log_message(f"✅ Generación de gráficos de barras completada")
            self.log_message(f"📊 {graficos_generados} gráficos generados correctamente")
            if graficos_fallidos > 0:
                self.log_message(f"⚠️ {graficos_fallidos} gráficos no pudieron generarse")
            
            return {
                'success': True,
                'message': 'Generación de gráficos completada',
                'graficos_generados': graficos_generados,
                'graficos_fallidos': graficos_fallidos,
                'total_registros': total_registros,
                'carpeta_salida': carpeta_barras
            }
            
        except Exception as e:
            import traceback
            self.log_message(f"❌ Error general: {str(e)}")
            self.log_message(f"📋 Detalles: {traceback.format_exc()}")
            return {
                'success': False,
                'message': f'Error en la generación de gráficos: {str(e)}',
                'details': traceback.format_exc()
            }
    
    def actualizar_campo_g1(self, tabla_base_layer, feature, nombre_archivo):
        """
        Actualiza el campo G1 del feature con el nombre del archivo generado
        """
        try:
            # Iniciar edición
            tabla_base_layer.startEditing()
            
            # Actualizar el campo G1
            field_index = tabla_base_layer.fields().indexFromName('G1')
            if field_index != -1:
                tabla_base_layer.changeAttributeValue(feature.id(), field_index, nombre_archivo)
                
            # Guardar cambios
            tabla_base_layer.commitChanges()
            self.log_message(f"📝 Campo G1 actualizado para feature {feature.id()}: {nombre_archivo}")
            
        except Exception as e:
            self.log_message(f"⚠️ Error al actualizar campo G1: {str(e)}")
            tabla_base_layer.rollBack()
    
    def generar_grafico_individual(self, datos_historicos_layer, muro, fecha_str, sector, relleno, protocolo, carpeta_salida, num_registro):
        """
        Replica exactamente la lógica de consulta_GRAFICO_BARRAS_canchas_sector.py
        pero con nomenclatura personalizada: G1250820_MP_S1_Arenafina.png
        
        Returns:
            str: Nombre del archivo generado si fue exitoso, None si hubo error
        """
        try:
            # Convertir fecha (igual que el script original)
            fecha_corte = datetime.strptime(str(fecha_str), "%Y-%m-%d")
            
            # -------------------------
            # Recolectar datos hasta la fecha de corte (EXACTAMENTE igual al script original)
            # -------------------------
            data = []
            for f in datos_historicos_layer.getFeatures():
                if f["Muro"] == muro:
                    f_fecha_str = f["Fecha"]
                    f_sector = f["Sector"]
                    if f_fecha_str and f_sector:
                        try:
                            f_fecha_dt = datetime.strptime(str(f_fecha_str), "%Y-%m-%d")
                            if f_fecha_dt <= fecha_corte:
                                data.append(f_sector)
                        except:
                            pass
            
            # -------------------------
            # Contar registros por sector (EXACTAMENTE igual al script original)
            # -------------------------
            if not data:
                self.log_message(f"⚠️ No hay datos para muro '{muro}' hasta la fecha {fecha_corte.date()}")
                return None
            else:
                df = pd.DataFrame(data, columns=["Sector"])
                conteos = df["Sector"].value_counts().sort_index().astype(int)
                
                # -------------------------
                # Graficar barras con fuentes más grandes para mejor legibilidad en PDFs
                # -------------------------
                plt.figure(figsize=(12,6))  # Figura más grande para mejor legibilidad
                plt.bar(conteos.index, conteos.values, color="skyblue")
                
                # Título más simple y fuente más grande - TODO EN MAYÚSCULAS
                plt.title(f"HISTORICO CANCHAS MURO {muro.upper()}", fontsize=24, fontweight='bold', pad=20)
                
                # Etiquetas de ejes con fuentes más grandes - TODO EN MAYÚSCULAS
                plt.xlabel("SECTOR", fontsize=20, fontweight='bold')
                plt.ylabel("CANTIDAD", fontsize=20, fontweight='bold')
                
                # Etiquetas de valores en los ejes más grandes
                plt.xticks(rotation=45, fontsize=16)
                plt.yticks(fontsize=16)
                
                # eje Y resumido con solo enteros
                ax = plt.gca()
                ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))  # máximo 5 ticks
                
                plt.grid(axis="y", linestyle="--", alpha=0.7)
                plt.tight_layout()
                
                # Generar nombre de archivo con nueva nomenclatura: G1250820_MP_S1_Arenafina.png
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
                
                # Nomenclatura final: G1{fecha}_{muro}_{sector}_{relleno}.png
                # Ejemplo: G1250820_MP_S1_Arenafina.png
                nombre_archivo = f"G1{fecha_procesada}_{muro_procesado}_{sector_procesado}_{relleno_procesado}.png"
                ruta_completa = os.path.join(carpeta_salida, nombre_archivo)
                
                plt.savefig(ruta_completa, dpi=200, bbox_inches='tight')  # DPI más alto y mejor ajuste
                plt.close()
                
                self.log_message(f"✅ Gráfico generado: {nombre_archivo}")
                return nombre_archivo  # Retornar el nombre del archivo
            
        except Exception as e:
            self.log_message(f"❌ Error al generar gráfico para registro {num_registro}: {str(e)}")
            import traceback
            self.log_message(traceback.format_exc())
            return None