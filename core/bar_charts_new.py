# -*- coding: utf-8 -*-
"""
Módulo para la generación de gráficos de barras por sector para cada registro
en la Tabla Base Datos, utilizando datos de la tabla DATOS HISTORICOS.
Este módulo utiliza un enfoque simplificado que evita problemas de codificación.
"""
import os
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from matplotlib.ticker import MaxNLocator
from qgis.core import QgsProject

class BarChartGenerator:
    """
    Clase para generar gráficos de barras por sector para cada registro
    en la Tabla Base Datos, utilizando datos de la tabla DATOS HISTORICOS.
    """
    
    def __init__(self, proc_root="", progress_callback=None, log_callback=None):
        """
        Inicializar el generador de gráficos de barras.
        
        Args:
            proc_root: Ruta base para el procesamiento
            progress_callback: Función de callback para actualizar progreso (0-100)
            log_callback: Función de callback para registrar mensajes
        """
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
        Genera gráficos de barras para cada registro de la Tabla Base Datos.
        
        Returns:
            dict: Resultado del proceso con estadísticas
        """
        try:
            # Crear carpetas para los gráficos si no existen
            if not self.proc_root:
                self.log_message("❌ Error: No se ha configurado la carpeta de procesamiento (PROC_ROOT)")
                return {
                    'success': False,
                    'message': 'No se ha configurado la carpeta de procesamiento (PROC_ROOT)'
                }
            
            carpeta_aux = os.path.join(self.proc_root, "Aux Reporte")
            carpeta_barras = os.path.join(carpeta_aux, "Grafico Barras")
            
            os.makedirs(carpeta_aux, exist_ok=True)
            os.makedirs(carpeta_barras, exist_ok=True)
            
            self.log_message(f"📁 Carpeta de gráficos creada: {carpeta_barras}")
            
            # Obtener capas necesarias
            tabla_base = None
            datos_historicos = None
            
            for layer in QgsProject.instance().mapLayers().values():
                if layer.name() == "Tabla Base Datos":
                    tabla_base = layer
                elif layer.name() == "DATOS HISTORICOS":
                    datos_historicos = layer
            
            # Verificar que ambas capas existan
            if not tabla_base:
                self.log_message("❌ Error: No se encontró la capa 'Tabla Base Datos'")
                return {
                    'success': False,
                    'message': 'No se encontró la capa Tabla Base Datos'
                }
            
            if not datos_historicos:
                self.log_message("❌ Error: No se encontró la capa 'DATOS HISTORICOS'")
                return {
                    'success': False,
                    'message': 'No se encontró la capa DATOS HISTORICOS'
                }
            
            # Procesar cada registro de la tabla base
            total_registros = tabla_base.featureCount()
            if total_registros == 0:
                self.log_message("⚠️ La tabla base no contiene registros para generar gráficos")
                return {
                    'success': False,
                    'message': 'La tabla base no contiene registros para generar gráficos'
                }
            
            # DEBUG: Mostrar campos disponibles
            fields = tabla_base.fields()
            field_names = [field.name() for field in fields]
            self.log_message(f"🔍 Campos disponibles en 'Tabla Base Datos': {field_names}")
            
            self.log_message(f"🔍 Procesando {total_registros} registros para generar gráficos de barras")
            
            graficos_generados = 0
            graficos_fallidos = 0
            
            # Procesar cada registro
            for i, feature in enumerate(tabla_base.getFeatures()):
                # Actualizar progreso
                progress = int((i + 1) / total_registros * 100)
                self.update_progress(progress, f"Generando gráfico {i+1}/{total_registros}")
                
                # Obtener valores necesarios
                try:
                    self.log_message(f"📋 Generando gráfico {i+1}/{total_registros}")
                    
                    # Extraer datos con manejo seguro usando el layer para verificar campos
                    fields = tabla_base.fields()
                    field_names = [field.name() for field in fields]
                    
                    if "Muro" in field_names:
                        muro = feature["Muro"]
                    else:
                        self.log_message(f"⚠️ Registro {i+1} no tiene campo 'Muro'")
                        graficos_fallidos += 1
                        continue
                        
                    if "Fecha" in field_names:
                        fecha_str = feature["Fecha"]
                    else:
                        self.log_message(f"⚠️ Registro {i+1} no tiene campo 'Fecha'")
                        graficos_fallidos += 1
                        continue
                        
                    if "Protocolo Topográfico" in field_names:
                        protocolo = feature["Protocolo Topográfico"]
                    else:
                        self.log_message(f"⚠️ Registro {i+1} no tiene campo 'Protocolo Topográfico'")
                        graficos_fallidos += 1
                        continue
                    
                    # Verificar que los datos existan
                    if not muro or not fecha_str or not protocolo:
                        self.log_message(f"⚠️ Registro {i+1} incompleto: faltan datos necesarios")
                        graficos_fallidos += 1
                        continue
                    
                    # Usar el método de consulta_GRAFICO_BARRAS_canchas_sector.py
                    if self.generar_grafico_simplificado(
                        datos_historicos, 
                        muro, 
                        fecha_str, 
                        protocolo, 
                        carpeta_barras,
                        i+1
                    ):
                        graficos_generados += 1
                    else:
                        graficos_fallidos += 1
                        
                except Exception as e:
                    self.log_message(f"❌ Error en registro {i+1}: {str(e)}")
                    graficos_fallidos += 1
            
            # Resumen final
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
            self.log_message(f"❌ Error en la generación de gráficos: {str(e)}")
            self.log_message(f"📋 Detalles: {traceback.format_exc()}")
            return {
                'success': False,
                'message': f'Error en la generación de gráficos: {str(e)}',
                'details': traceback.format_exc()
            }
    
    def generar_grafico_simplificado(self, datos_historicos, muro, fecha_str, protocolo, carpeta_salida, num_registro):
        """
        Genera un gráfico de barras individual para un registro específico.
        Utiliza un enfoque simplificado basado en consulta_GRAFICO_BARRAS_canchas_sector.py
        
        Args:
            datos_historicos: Capa con datos históricos
            muro: Nombre del muro
            fecha_str: Fecha del registro (YYYY-MM-DD)
            protocolo: Número de protocolo para nombrar el archivo
            carpeta_salida: Carpeta donde guardar el gráfico
            num_registro: Número de registro (para logging)
            
        Returns:
            bool: True si se generó correctamente, False en caso contrario
        """
        try:
            # Intentar convertir fecha
            try:
                fecha_corte = datetime.strptime(str(fecha_str), "%Y-%m-%d")
            except ValueError as e:
                self.log_message(f"⚠️ Formato de fecha inválido en registro {num_registro}: {str(e)}")
                return False
            
            # -------------------------
            # Recolectar datos hasta la fecha de corte (exactamente como en el script original)
            # -------------------------
            data = []
            for f in datos_historicos.getFeatures():
                # Acceso directo a los campos, exactamente como en el script original
                try:
                    if f["Muro"] == muro:
                        f_fecha_str = f["Fecha"]
                        f_sector = f["Sector"]
                        if f_fecha_str and f_sector:
                            try:
                                f_fecha_dt = datetime.strptime(str(f_fecha_str), "%Y-%m-%d")
                                if f_fecha_dt <= fecha_corte:
                                    data.append(f_sector)
                            except:
                                continue
                except Exception:
                    # Si hay un error al acceder a los campos, simplemente continúa
                    continue
            
            # Verificar que haya datos
            if not data:
                self.log_message(f"⚠️ No hay datos para muro '{muro}' hasta la fecha {fecha_corte.date()}")
                return False
            
            # -------------------------
            # Contar registros por sector (exactamente como en el script original)
            # -------------------------
            df = pd.DataFrame(data, columns=["Sector"])
            conteos = df["Sector"].value_counts().sort_index().astype(int)
            
            # -------------------------
            # Graficar barras (exactamente como en el script original)
            # -------------------------
            plt.figure(figsize=(10, 5))
            plt.bar(conteos.index, conteos.values, color="skyblue")
            plt.title(f"Cantidad de registros por Sector - Muro: {muro} (hasta {fecha_corte.date()})")
            plt.xlabel("Sector")
            plt.ylabel("Cantidad de registros")
            plt.xticks(rotation=45)
            
            # eje Y resumido con solo enteros
            ax = plt.gca()
            ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))  # máximo 5 ticks
            
            plt.grid(axis="y", linestyle="--", alpha=0.7)
            plt.tight_layout()
            
            # En lugar de plt.show(), guardamos a archivo
            # Generar nombre de archivo seguro
            nombre_archivo = f"PT{str(protocolo).zfill(4)}_{str(muro).replace(' ', '_')}_barras.png"
            nombre_archivo = nombre_archivo.replace("/", "_").replace("\\", "_")
            ruta_completa = os.path.join(carpeta_salida, nombre_archivo)
            
            plt.savefig(ruta_completa, dpi=150)
            plt.close()
            
            self.log_message(f"✅ Gráfico generado: {nombre_archivo}")
            return True
            
        except Exception as e:
            import traceback
            self.log_message(f"❌ Error al generar gráfico para registro {num_registro}: {str(e)}")
            self.log_message(traceback.format_exc())
            return False