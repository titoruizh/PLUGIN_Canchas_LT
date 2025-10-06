# -*- coding: utf-8 -*-
"""
Módulo para análisis histórico de datos y cálculos de intervenciones
para el plugin de Canchas Las Tortolas
"""

from datetime import datetime, timedelta
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, edit, QgsField, QgsFeatureRequest
)
from PyQt5.QtCore import QVariant

class HistoricalAnalysisProcessor:
    """Procesador para análisis de datos históricos"""
    
    def __init__(self, progress_callback=None, log_callback=None):
        """
        Inicializar procesador de análisis histórico
        
        Args:
            progress_callback: Función callback para actualizar progreso
            log_callback: Función callback para logs
        """
        # Callbacks
        self.progress_callback = progress_callback or (lambda x, msg="": None)
        self.log_callback = log_callback or (lambda msg: print(msg))

    def verificar_columnas_existentes(self, layer, columnas):
        """
        Verifica si las columnas existen en la capa
        
        Args:
            layer: Capa a verificar
            columnas: Lista de nombres de columnas a verificar
            
        Returns:
            list: Lista de columnas que no existen en la capa
        """
        campos_existentes = [field.name() for field in layer.fields()]
        return [col for col in columnas if col not in campos_existentes]
    
    def crear_columnas_si_no_existen(self, layer, columnas):
        """
        Crea columnas en la capa si no existen
        
        Args:
            layer: Capa donde crear las columnas
            columnas: Diccionario con nombre de columna y tipo de datos
            
        Returns:
            bool: True si se crearon columnas, False en caso de error
        """
        try:
            campos_faltantes = self.verificar_columnas_existentes(layer, columnas.keys())
            
            if not campos_faltantes:
                self.log_message("✅ Todas las columnas necesarias ya existen")
                return True
            
            # Crear las columnas faltantes
            provider = layer.dataProvider()
            
            for col_name in campos_faltantes:
                field_type = columnas[col_name]
                # Mapeo de tipos para mostrar en log
                type_names = {
                    QVariant.String: "String",
                    QVariant.Int: "Integer",
                    QVariant.Double: "Double",
                    QVariant.Date: "Date",
                    QVariant.DateTime: "DateTime"
                }
                type_name = type_names.get(field_type, "Unknown")
                self.log_message(f"📊 Creando columna: {col_name} ({type_name})")
                provider.addAttributes([QgsField(col_name, field_type)])
            
            layer.updateFields()
            self.log_message(f"✅ Se crearon {len(campos_faltantes)} columnas nuevas")
            return True
            
        except Exception as e:
            self.log_message(f"❌ Error al crear columnas: {e}")
            import traceback
            self.log_message(f"📋 Traceback: {traceback.format_exc()}")
            return False

    def calcular_ultima_intervencion(self, tabla_base, datos_historicos):
        """
        Calcula la última fecha de intervención para cada registro de la tabla base
        
        Args:
            tabla_base: Capa de tabla base
            datos_historicos: Capa de datos históricos
            
        Returns:
            dict: Resultado con éxito/error y detalles
        """
        try:
            self.log_message("🔄 Calculando últimas fechas de intervención...")
            
            # Verificar y crear la columna si no existe
            columnas = {"Ultima Intervencion": QVariant.String}
            self.crear_columnas_si_no_existen(tabla_base, columnas)
            
            # Obtener índice de la columna
            idx_ultima_intervencion = tabla_base.fields().indexFromName("Ultima Intervencion")
            
            if idx_ultima_intervencion == -1:
                return {
                    'success': False,
                    'message': 'No se pudo crear o encontrar la columna "Ultima Intervencion"'
                }
            
            # Procesar cada registro de la tabla base
            registros_totales = tabla_base.featureCount()
            registros_actualizados = 0
            registros_sin_intervencion = 0
            
            # Verificar si la capa está en modo de edición, si no, activarlo
            editing_started = False
            if not tabla_base.isEditable():
                tabla_base.startEditing()
                editing_started = True
            
            try:
                for i, f_base in enumerate(tabla_base.getFeatures()):
                    # Actualizar progreso
                    progreso = int(50 * (i+1) / registros_totales)
                    self.progress_callback(progreso, f"Procesando registro {i+1}/{registros_totales}")
                    
                    # Obtener datos del registro actual
                    muro = f_base["Muro"]
                    sector = f_base["Sector"]
                    fecha_str = f_base["Fecha"]
                    
                    # Verificar datos necesarios
                    if not muro or not sector or not fecha_str:
                        continue
                    
                    try:
                        # Convertir fecha a datetime
                        fecha_obj_dt = datetime.strptime(str(fecha_str), "%Y-%m-%d")
                        
                        # Buscar registros históricos con el mismo muro y sector
                        registros = []
                        for f_hist in datos_historicos.getFeatures():
                            muro_hist = f_hist["Muro"]
                            sector_hist = f_hist["Sector"]
                            fecha_hist_str = f_hist["Fecha"]
                            
                            if muro_hist == muro and sector_hist == sector and fecha_hist_str:
                                try:
                                    fecha_hist_dt = datetime.strptime(str(fecha_hist_str), "%Y-%m-%d")
                                    registros.append((fecha_hist_dt, f_hist))
                                except:
                                    pass
                        
                        # Ordenar registros por fecha ascendente
                        registros.sort(key=lambda x: x[0])
                        
                        # Buscar la última fecha anterior a la fecha actual
                        ultima_fecha = None
                        for fecha_dt, feat in registros:
                            if fecha_dt < fecha_obj_dt:
                                ultima_fecha = fecha_dt
                            elif fecha_dt == fecha_obj_dt:
                                # Llegó a la fecha actual, se corta
                                break
                        
                        # Actualizar el campo
                        if ultima_fecha:
                            ultima_fecha_str = ultima_fecha.strftime("%Y-%m-%d")
                            f_base["Ultima Intervencion"] = ultima_fecha_str
                            tabla_base.updateFeature(f_base)
                            registros_actualizados += 1
                        else:
                            f_base["Ultima Intervencion"] = ""
                            tabla_base.updateFeature(f_base)
                            registros_sin_intervencion += 1
                            
                    except Exception as e:
                        self.log_message(f"⚠️ Error en registro {f_base.id()}: {e}")
            
            finally:
                # Confirmar cambios y salir del modo de edición si lo iniciamos
                if editing_started:
                    tabla_base.commitChanges()
            
            self.log_message(f"✅ Cálculo de últimas intervenciones completado:")
            self.log_message(f"  • {registros_actualizados} registros con última intervención")
            self.log_message(f"  • {registros_sin_intervencion} registros sin intervenciones previas")
            
            return {
                'success': True,
                'message': f'Se actualizaron {registros_actualizados} registros con fechas de última intervención',
                'registros_actualizados': registros_actualizados,
                'registros_sin_intervencion': registros_sin_intervencion
            }
            
        except Exception as e:
            import traceback
            error_msg = f"Error durante el cálculo de última intervención: {str(e)}"
            error_details = traceback.format_exc()
            self.log_message(f"❌ {error_msg}")
            self.log_message(f"📋 Detalles del error:\n{error_details}")
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }
    
    def calcular_crecimiento_anual(self, tabla_base, datos_historicos, dias_atras=365):
        """
        Calcula el crecimiento anual para cada registro de la tabla base
        
        Args:
            tabla_base: Capa de tabla base
            datos_historicos: Capa de datos históricos
            dias_atras: Número de días hacia atrás para buscar el crecimiento
            
        Returns:
            dict: Resultado con éxito/error y detalles
        """
        try:
            self.log_message(f"🔄 Calculando crecimiento anual ({dias_atras} días)...")
            
            # Verificar y crear la columna si no existe
            columnas = {"Ultimo Crecimiento Anual": QVariant.Double}
            self.crear_columnas_si_no_existen(tabla_base, columnas)
            
            # Obtener índice de la columna
            idx_crecimiento = tabla_base.fields().indexFromName("Ultimo Crecimiento Anual")
            
            if idx_crecimiento == -1:
                return {
                    'success': False,
                    'message': 'No se pudo crear o encontrar la columna "Ultimo Crecimiento Anual"'
                }
            
            # Procesar cada registro de la tabla base
            registros_totales = tabla_base.featureCount()
            registros_actualizados = 0
            registros_sin_datos = 0
            
            # Verificar si la capa está en modo de edición, si no, activarlo
            editing_started_crecimiento = False
            if not tabla_base.isEditable():
                tabla_base.startEditing()
                editing_started_crecimiento = True
            
            try:
                for i, f_base in enumerate(tabla_base.getFeatures()):
                    # Actualizar progreso
                    progreso = int(50 + 50 * (i+1) / registros_totales)
                    self.progress_callback(progreso, f"Procesando crecimiento {i+1}/{registros_totales}")
                    
                    # Obtener datos del registro actual
                    muro = f_base["Muro"]
                    sector = f_base["Sector"]
                    fecha_str = f_base["Fecha"]
                    
                    # Verificar datos necesarios
                    if not muro or not sector or not fecha_str:
                        continue
                    
                    try:
                        # Convertir fecha a datetime
                        fecha_final = datetime.strptime(str(fecha_str), "%Y-%m-%d")
                        fecha_inicio = fecha_final - timedelta(days=dias_atras)
                        
                        # Recolectar datos del muro y sector en el período especificado
                        data = []
                        for f_hist in datos_historicos.getFeatures():
                            muro_val = str(f_hist["Muro"]).strip().lower()
                            sector_val = str(f_hist["Sector"]).strip().lower()
                            fecha_hist_str = str(f_hist["Fecha"]).strip()
                            espesor_str = f_hist["Espesor"]
                            
                            if muro_val == muro.lower() and sector_val == sector.lower():
                                try:
                                    fecha_hist_dt = datetime.strptime(fecha_hist_str, "%Y-%m-%d")
                                    if espesor_str is not None and str(espesor_str).strip() != "":
                                        espesor_val = float(str(espesor_str).replace(",", "."))
                                        if fecha_inicio <= fecha_hist_dt <= fecha_final:
                                            data.append((fecha_hist_dt, espesor_val))
                                except Exception as e:
                                    pass
                        
                        # Calcular crecimiento total
                        if data:
                            # Ordenar datos por fecha
                            data.sort(key=lambda x: x[0])
                            
                            # Sumar todos los espesores para obtener el crecimiento total
                            crecimiento_total = sum(item[1] for item in data)
                            
                            # Actualizar el campo con redondeo a 4 decimales
                            f_base["Ultimo Crecimiento Anual"] = round(crecimiento_total, 4)
                            tabla_base.updateFeature(f_base)
                            registros_actualizados += 1
                        else:
                            f_base["Ultimo Crecimiento Anual"] = round(0, 4)  # Consistencia en formato
                            tabla_base.updateFeature(f_base)
                            registros_sin_datos += 1
                            
                    except Exception as e:
                        self.log_message(f"⚠️ Error en registro {f_base.id()}: {e}")
            
            finally:
                # Confirmar cambios y salir del modo de edición si lo iniciamos
                if editing_started_crecimiento:
                    tabla_base.commitChanges()
            
            self.log_message(f"✅ Cálculo de crecimiento anual completado:")
            self.log_message(f"  • {registros_actualizados} registros con crecimiento anual calculado")
            self.log_message(f"  • {registros_sin_datos} registros sin datos suficientes para cálculo")
            
            return {
                'success': True,
                'message': f'Se actualizaron {registros_actualizados} registros con crecimiento anual',
                'registros_actualizados': registros_actualizados,
                'registros_sin_datos': registros_sin_datos
            }
            
        except Exception as e:
            import traceback
            error_msg = f"Error durante el cálculo de crecimiento anual: {str(e)}"
            error_details = traceback.format_exc()
            self.log_message(f"❌ {error_msg}")
            self.log_message(f"📋 Detalles del error:\n{error_details}")
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }

    def calcular_movimientos_tierra_anuales(self, tabla_base, datos_historicos, dias_atras=365):
        """
        Calcula movimientos de tierra anuales: neto, relleno acumulado y corte acumulado
        
        Args:
            tabla_base: Capa de la tabla base donde guardar los resultados
            datos_historicos: Capa de datos históricos para consultar
            dias_atras: Número de días hacia atrás para el análisis (default 365)
            
        Returns:
            dict: Resultado con éxito/error y detalles
        """
        try:
            self.log_message(f"🔄 Calculando movimientos de tierra anuales ({dias_atras} días)...")
            
            # Verificar y crear las columnas si no existen
            columnas = {
                "Movimiento Tierra Anual Neto": QVariant.Double,
                "Relleno Anual Acumulado": QVariant.Double, 
                "Corte Anual Acumulado": QVariant.Double
            }
            self.crear_columnas_si_no_existen(tabla_base, columnas)
            
            # Obtener índices de las columnas
            idx_neto = tabla_base.fields().indexFromName("Movimiento Tierra Anual Neto")
            idx_relleno = tabla_base.fields().indexFromName("Relleno Anual Acumulado")
            idx_corte = tabla_base.fields().indexFromName("Corte Anual Acumulado")
            
            if idx_neto == -1 or idx_relleno == -1 or idx_corte == -1:
                return {
                    'success': False,
                    'message': 'No se pudieron crear o encontrar las columnas de movimientos de tierra'
                }
            
            # Procesar cada registro de la tabla base
            registros_totales = tabla_base.featureCount()
            registros_actualizados = 0
            registros_sin_datos = 0
            
            # Verificar si la capa está en modo de edición, si no, activarlo
            editing_started_movimientos = False
            if not tabla_base.isEditable():
                tabla_base.startEditing()
                editing_started_movimientos = True
            
            try:
                for i, f_base in enumerate(tabla_base.getFeatures()):
                    # Actualizar progreso
                    progreso = int(70 + 30 * (i+1) / registros_totales)
                    self.progress_callback(progreso, f"Procesando movimientos tierra {i+1}/{registros_totales}")
                    
                    try:
                        # Obtener datos del registro actual
                        muro = f_base["Muro"]
                        sector = f_base["Sector"] 
                        fecha_str = f_base["Fecha"]
                        
                        self.log_message(f"🔄 Procesando registro {i+1}/{registros_totales}: {muro}-{sector} ({fecha_str})")
                        
                        if not all([muro, sector, fecha_str]):
                            self.log_message(f"⚠️ Datos incompletos: Muro={muro}, Sector={sector}, Fecha={fecha_str}")
                            f_base["Movimiento Tierra Anual Neto"] = round(0, 4)
                            f_base["Relleno Anual Acumulado"] = round(0, 4)
                            f_base["Corte Anual Acumulado"] = round(0, 4)
                            tabla_base.updateFeature(f_base)
                            registros_sin_datos += 1
                            continue
                            
                        # Calcular fecha límite (fecha actual - días_atras)
                        fecha_final = datetime.strptime(str(fecha_str), "%Y-%m-%d")
                        fecha_inicio = fecha_final - timedelta(days=dias_atras)
                        fecha_limite = fecha_inicio.strftime("%Y-%m-%d")
                        
                        self.log_message(f"📅 Buscando datos desde {fecha_limite} hasta {fecha_str}")
                        
                        # Filtro para buscar registros históricos (escapar comillas simples)
                        muro_escaped = muro.replace("'", "''") if muro else ''
                        sector_escaped = sector.replace("'", "''") if sector else ''
                        filter_expression = f'"Muro" = \'{muro_escaped}\' AND "Sector" = \'{sector_escaped}\' AND "Fecha" >= \'{fecha_limite}\' AND "Fecha" <= \'{fecha_str}\''
                        
                        self.log_message(f"🔍 Filtro aplicado: {filter_expression}")
                        
                        request = QgsFeatureRequest().setFilterExpression(filter_expression)
                        features = list(datos_historicos.getFeatures(request))
                        
                        if features:
                            # Calcular sumas de Fill y Cut
                            suma_fill = 0
                            suma_cut = 0
                            
                            self.log_message(f"🔍 Encontrados {len(features)} registros históricos para {muro}-{sector}")
                            
                            for feature in features:
                                # Obtener valores usando nombres de campo
                                fill_val = feature["Fill"] if feature["Fill"] is not None else 0
                                cut_val = feature["Cut"] if feature["Cut"] is not None else 0
                                
                                try:
                                    fill_float = float(fill_val) if fill_val != '' else 0
                                    cut_float = float(cut_val) if cut_val != '' else 0
                                    
                                    suma_fill += fill_float
                                    suma_cut += cut_float
                                    
                                except (ValueError, TypeError) as e:
                                    self.log_message(f"  ⚠️ Error convertir valores: Fill={fill_val}, Cut={cut_val}")
                                    continue
                            
                            # Calcular movimiento neto (Fill - Cut)
                            movimiento_neto = suma_fill - suma_cut
                            
                            self.log_message(f"📊 Resultados para {muro}-{sector}:")
                            self.log_message(f"  • Fill total: {suma_fill}")
                            self.log_message(f"  • Cut total: {suma_cut}")  
                            self.log_message(f"  • Movimiento neto: {movimiento_neto}")
                            
                            # Actualizar los campos con redondeo a 4 decimales
                            f_base["Movimiento Tierra Anual Neto"] = round(movimiento_neto, 4)
                            f_base["Relleno Anual Acumulado"] = round(suma_fill, 4)
                            f_base["Corte Anual Acumulado"] = round(suma_cut, 4)
                            tabla_base.updateFeature(f_base)
                            registros_actualizados += 1
                        else:
                            self.log_message(f"⚠️ No se encontraron datos históricos para {muro}-{sector} en el período")
                            self.log_message(f"  • Filtro usado: {filter_expression}")
                            f_base["Movimiento Tierra Anual Neto"] = round(0, 4)
                            f_base["Relleno Anual Acumulado"] = round(0, 4)
                            f_base["Corte Anual Acumulado"] = round(0, 4)
                            tabla_base.updateFeature(f_base)
                            registros_sin_datos += 1
                            
                    except Exception as e:
                        self.log_message(f"⚠️ Error en registro movimientos tierra {f_base.id()}: {e}")
            
            finally:
                # Confirmar cambios y salir del modo de edición si lo iniciamos
                if editing_started_movimientos:
                    tabla_base.commitChanges()
            
            self.log_message(f"✅ Cálculo de movimientos de tierra anuales completado:")
            self.log_message(f"  • {registros_actualizados} registros con movimientos calculados")
            self.log_message(f"  • {registros_sin_datos} registros sin datos suficientes")
            
            return {
                'success': True,
                'message': f'Se actualizaron {registros_actualizados} registros con movimientos de tierra',
                'registros_actualizados': registros_actualizados,
                'registros_sin_datos': registros_sin_datos
            }
            
        except Exception as e:
            import traceback
            error_msg = f"Error durante el cálculo de movimientos de tierra: {str(e)}"
            error_details = traceback.format_exc()
            self.log_message(f"❌ {error_msg}")
            self.log_message(f"📋 Detalles del error:\n{error_details}")
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }

    def ejecutar_analisis_historico_completo(self, dias_crecimiento_anual=365):
        """
        Ejecuta todo el proceso de análisis histórico
        
        Args:
            dias_crecimiento_anual: Número de días hacia atrás para crecimiento anual
            
        Returns:
            dict: Resultado con éxito/error y detalles
        """
        try:
            self.log_message("📊 Iniciando análisis histórico completo...")
            self.progress_callback(5, "Buscando tablas necesarias...")
            
            # Buscar las capas requeridas
            project = QgsProject.instance()
            tabla_base = None
            datos_historicos = None
            
            # Encontrar tablas por nombre exacto
            for layer in project.mapLayers().values():
                if layer.name() == "Tabla Base Datos":
                    tabla_base = layer
                elif layer.name() == "DATOS HISTORICOS":
                    datos_historicos = layer
            
            # Verificar que ambas tablas existan
            if not tabla_base:
                return {
                    'success': False,
                    'message': 'No se encontró la capa "Tabla Base Datos". Debe ejecutar el proceso de creación de tabla primero.'
                }
            
            if not datos_historicos:
                return {
                    'success': False,
                    'message': 'No se encontró la capa "DATOS HISTORICOS". Debe ejecutar la fusión de datos primero.'
                }
            
            # Verificar que Tabla Base tenga registros
            if tabla_base.featureCount() == 0:
                return {
                    'success': False,
                    'message': 'La tabla "Tabla Base Datos" está vacía.'
                }
            
            self.log_message(f"✅ Tablas encontradas:")
            self.log_message(f"   • Tabla Base Datos: {tabla_base.featureCount()} registros")
            self.log_message(f"   • DATOS HISTORICOS: {datos_historicos.featureCount()} registros")
            
            # Calcular última intervención
            self.progress_callback(10, "Calculando última fecha de intervención...")
            resultado_intervencion = self.calcular_ultima_intervencion(tabla_base, datos_historicos)
            
            if not resultado_intervencion['success']:
                return resultado_intervencion
            
            # Calcular crecimiento anual
            self.progress_callback(60, "Calculando crecimiento anual...")
            resultado_crecimiento = self.calcular_crecimiento_anual(
                tabla_base, 
                datos_historicos,
                dias_atras=dias_crecimiento_anual
            )
            
            if not resultado_crecimiento['success']:
                return resultado_crecimiento
            
            # Calcular movimientos de tierra anuales
            self.progress_callback(70, "Calculando movimientos de tierra anuales...")
            resultado_movimientos = self.calcular_movimientos_tierra_anuales(
                tabla_base, 
                datos_historicos,
                dias_atras=dias_crecimiento_anual
            )
            
            if not resultado_movimientos['success']:
                return resultado_movimientos

            # Resumir resultados
            self.progress_callback(100, "¡Análisis histórico completado!")
            
            return {
                'success': True,
                'message': 'Análisis histórico completado exitosamente',
                'resultado_intervencion': resultado_intervencion,
                'resultado_crecimiento': resultado_crecimiento,
                'resultado_movimientos': resultado_movimientos,
                'registros_totales': tabla_base.featureCount(),
                'dias_crecimiento_anual': dias_crecimiento_anual
            }
            
        except Exception as e:
            import traceback
            error_msg = f"Error durante el análisis histórico: {str(e)}"
            error_details = traceback.format_exc()
            self.log_message(f"❌ {error_msg}")
            self.log_message(f"📋 Detalles del error:\n{error_details}")
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }
    
    def log_message(self, message):
        """Enviar mensaje al log a través del callback"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)