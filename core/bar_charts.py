# -*- coding: utf-8 -*-
"""
Módulo para la generación de gráficos de barras por sector para cada registro
en la Tabla Base Datos, utilizando datos de la tabla DATOS HISTORICOS.
"""
import os
import matplotlib.pyplot as plt
import pandas as pd
import unicodedata
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
                    muro = feature["Muro"]
                    fecha_str = feature["Fecha"]
                    protocolo = feature["Protocolo Topográfico"]
                    
                    if not muro or not fecha_str or not protocolo:
                        self.log_message(f"⚠️ Registro {i+1} incompleto: faltan datos necesarios")
                        graficos_fallidos += 1
                        continue
                    
                    # Generar gráfico para este registro
                    resultado = self.generar_grafico_individual(
                        datos_historicos, 
                        muro, 
                        fecha_str, 
                        protocolo, 
                        carpeta_barras
                    )
                    
                    if resultado:
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
    
    def generar_grafico_individual(self, datos_historicos, muro, fecha_str, protocolo, carpeta_salida):
        """
        Genera un gráfico de barras individual para un registro específico.
        
        Args:
            datos_historicos: Capa con datos históricos
            muro: Nombre del muro
            fecha_str: Fecha del registro (YYYY-MM-DD)
            protocolo: Número de protocolo para nombrar el archivo
            carpeta_salida: Carpeta donde guardar el gráfico
            
        Returns:
            bool: True si se generó correctamente, False en caso contrario
        """
        try:
            # Normalizar los datos de entrada para evitar problemas de codificación
            muro_norm = self._normalizar_texto(str(muro)) if muro else ""
            fecha_norm = str(fecha_str) if fecha_str else ""
            protocolo_norm = str(protocolo) if protocolo else ""
            
            self.log_message(f"📋 Generando gráfico para Muro: '{muro_norm}', Fecha: '{fecha_norm}'")
            
            if not muro_norm or not fecha_norm or not protocolo_norm:
                self.log_message(f"⚠️ Datos incompletos para generar el gráfico")
                return False
            
            # Convertir fecha
            try:
                fecha_dt = datetime.strptime(fecha_norm, "%Y-%m-%d")
            except ValueError as e:
                self.log_message(f"⚠️ Formato de fecha incorrecto: {fecha_norm} - {str(e)}")
                return False
            
            # Crear una lista para almacenar los datos de sectores
            sectores = []
            
            # Recorrer manualmente todos los registros históricos
            for feature in datos_historicos.getFeatures():
                try:
                    # Extraer valores de forma segura
                    feature_muro = ""
                    feature_fecha = ""
                    feature_sector = ""
                    
                    # Obtener valores de manera segura
                    if feature.hasAttribute("Muro") and feature["Muro"] is not None:
                        feature_muro = self._normalizar_texto(str(feature["Muro"]))
                    
                    if feature.hasAttribute("Fecha") and feature["Fecha"] is not None:
                        feature_fecha = str(feature["Fecha"])
                    
                    if feature.hasAttribute("Sector") and feature["Sector"] is not None:
                        feature_sector = self._normalizar_texto(str(feature["Sector"]))
                    
                    # Verificar si este registro histórico pertenece al muro actual y es anterior o igual a la fecha
                    if (feature_muro.lower() == muro_norm.lower() and 
                            feature_fecha and feature_fecha <= fecha_norm and 
                            feature_sector):
                        sectores.append(feature_sector)
                except Exception as inner_e:
                    # Si hay un error con un registro específico, simplemente continuamos
                    self.log_message(f"⚠️ Error al procesar un registro histórico: {str(inner_e)}")
                    continue
            
            # Verificar que haya datos
            if not sectores:
                self.log_message(f"⚠️ No hay datos históricos para Muro: '{muro_norm}' hasta '{fecha_norm}'")
                return False
            
            # Crear DataFrame y contar por sector
            df = pd.DataFrame({"Sector": sectores})
            conteo_sectores = df["Sector"].value_counts().sort_index()
            
            # Crear el gráfico
            plt.figure(figsize=(10, 5))
            plt.bar(conteo_sectores.index, conteo_sectores.values, color="skyblue")
            
            # Título y etiquetas
            titulo = f"Registros por Sector - Muro: {muro_norm} (hasta {fecha_dt.strftime('%Y-%m-%d')})"
            plt.title(titulo)
            plt.xlabel("Sector")
            plt.ylabel("Cantidad de registros")
            plt.xticks(rotation=45)
            
            # Formato de eje Y con enteros solamente
            ax = plt.gca()
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            
            # Agregar cuadrícula
            plt.grid(axis="y", linestyle="--", alpha=0.7)
            plt.tight_layout()
            
            # Generar nombre de archivo seguro
            muro_filename = muro_norm.replace(" ", "_").replace("/", "_").replace("\\", "_")
            archivo = f"PT{protocolo_norm.zfill(4)}_{muro_filename}_barras.png"
            ruta_completa = os.path.join(carpeta_salida, archivo)
            
            # Guardar imagen
            plt.savefig(ruta_completa, dpi=150)
            plt.close()
            
            self.log_message(f"✅ Gráfico generado correctamente: {archivo}")
            return True
            
        except Exception as e:
            import traceback
            self.log_message(f"❌ Error al generar gráfico: {str(e)}")
            self.log_message(traceback.format_exc())
            return False
    
    def _normalizar_texto(self, texto):
        """
        Normaliza un texto para eliminar caracteres especiales y acentos.
        Utiliza unicodedata para una normalización más robusta.
        
        Args:
            texto: Texto a normalizar
            
        Returns:
            str: Texto normalizado
        """
        # Asegurar que es un string
        if not isinstance(texto, str):
            texto = str(texto)
        
        # Si está vacío, devolver vacío
        if not texto:
            return ""
            
        try:
            # Normalizar: convertir caracteres acentuados a su forma base + acento
            normalizado = unicodedata.normalize('NFKD', texto)
            
            # Eliminar caracteres no ASCII (como acentos)
            sin_acentos = ''.join(c for c in normalizado if unicodedata.category(c) != 'Mn')
            
            # Reemplazar caracteres especiales y no permitidos en nombres de archivo
            for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '#', '%']:
                sin_acentos = sin_acentos.replace(char, '_')
                
            return sin_acentos
        except Exception:
            # En caso de error, devolver una versión básica normalizada
            resultado = str(texto)
            for char in ['á', 'à', 'ä', 'â', 'ã']:
                resultado = resultado.replace(char, 'a')
            for char in ['é', 'è', 'ë', 'ê']:
                resultado = resultado.replace(char, 'e')
            for char in ['í', 'ì', 'ï', 'î']:
                resultado = resultado.replace(char, 'i')
            for char in ['ó', 'ò', 'ö', 'ô', 'õ']:
                resultado = resultado.replace(char, 'o')
            for char in ['ú', 'ù', 'ü', 'û']:
                resultado = resultado.replace(char, 'u')
            for char in ['ñ', 'ń']:
                resultado = resultado.replace(char, 'n')
                
            # Eliminar caracteres problemáticos para nombres de archivo
            for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '#', '%']:
                resultado = resultado.replace(char, '_')
                
            return resultado