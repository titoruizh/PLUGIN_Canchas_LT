# -*- coding: utf-8 -*-
"""
Módulo para la fusión de datos entre la tabla base y datos históricos
para el plugin de Canchas Las Tortolas
"""

from datetime import datetime
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, edit
)

class DataMergeProcessor:
    """Procesador de fusión de datos entre tablas"""
    
    def __init__(self, progress_callback=None, log_callback=None):
        """
        Inicializar procesador de fusión de datos
        
        Args:
            progress_callback: Función callback para actualizar progreso
            log_callback: Función callback para logs
        """
        # Callbacks
        self.progress_callback = progress_callback or (lambda x, msg="": None)
        self.log_callback = log_callback or (lambda msg: print(msg))

    def detectar_formato_fecha(self, layer, nombre_capa):
        """
        Detecta automáticamente el formato de fecha en una capa
        probando diferentes formatos comunes
        
        Args:
            layer: Capa vectorial
            nombre_capa: Nombre de la capa (para logs)
        
        Returns:
            str: Formato detectado o None si no se pudo detectar
        """
        formatos_comunes = [
            "%Y-%m-%d",  # 2025-09-29
            "%d-%m-%Y",  # 29-09-2025
            "%d/%m/%Y",  # 29/09/2025
            "%Y/%m/%d",  # 2025/09/29
            "%m/%d/%Y",  # 09/29/2025
        ]
        
        # Tomar muestra de fechas para detectar formato
        fechas_muestra = []
        count = 0
        for f in layer.getFeatures():
            if count >= 10:  # Analizar máximo 10 registros
                break
            valor = f["Fecha"]
            if valor and str(valor).strip():
                fechas_muestra.append(str(valor).strip())
                count += 1
        
        if not fechas_muestra:
            self.log_message(f"⚠️ No se encontraron fechas para analizar en {nombre_capa}")
            return None
        
        # Probar cada formato con las fechas de muestra
        for formato in formatos_comunes:
            exitos = 0
            for fecha_str in fechas_muestra:
                try:
                    datetime.strptime(fecha_str, formato)
                    exitos += 1
                except:
                    pass
            
            # Si más del 70% de las fechas coinciden con este formato, lo consideramos válido
            if exitos > len(fechas_muestra) * 0.7:
                self.log_message(f"✅ Formato detectado en {nombre_capa}: {formato}")
                self.log_message(f"   Ejemplos: {fechas_muestra[:3]}")
                return formato
        
        self.log_message(f"❌ No se pudo detectar formato de fecha en {nombre_capa}")
        self.log_message(f"   Fechas encontradas: {fechas_muestra[:5]}")
        return None

    def normalizar_fecha(self, layer, nombre_capa, formato_origen=None):
        """
        Normaliza el formato de fechas en una capa
        Si no se especifica formato_origen, intenta detectarlo automáticamente
        
        Args:
            layer: Capa vectorial
            nombre_capa: Nombre de la capa (para logs)
            formato_origen: Formato de fecha origen (opcional)
        
        Returns:
            bool: True si se completó correctamente, False en caso contrario
        """
        try:
            self.log_message(f"📌 Normalizando fechas en: {nombre_capa}")
            
            # Si no se especifica formato, detectarlo automáticamente
            if not formato_origen:
                formato_origen = self.detectar_formato_fecha(layer, nombre_capa)
                if not formato_origen:
                    self.log_message(f"❌ No se pudo detectar formato de fecha en {nombre_capa}")
                    return False
            
            registros_procesados = 0
            errores = 0
            
            # Verificar si la capa está en modo de edición, si no, activarlo
            editing_started = False
            if not layer.isEditable():
                layer.startEditing()
                editing_started = True
            
            try:
                for f in layer.getFeatures():
                    valor = f["Fecha"]
                    if not valor or str(valor).strip() == "":
                        continue
                    try:
                        fecha_dt = datetime.strptime(str(valor), formato_origen)
                        f["Fecha"] = fecha_dt.strftime("%Y-%m-%d")
                        layer.updateFeature(f)
                        registros_procesados += 1
                    except Exception as e:
                        self.log_message(f"⚠️ Error en registro {f.id()} con valor '{valor}': {e}")
                        errores += 1
            
            finally:
                # Confirmar cambios y salir del modo de edición si lo iniciamos
                if editing_started:
                    layer.commitChanges()
            
            self.log_message(f"✅ Normalización de fechas completada: {registros_procesados} registros procesados, {errores} errores")
            return registros_procesados > 0
            
        except Exception as e:
            self.log_message(f"❌ Error en normalizar_fecha: {e}")
            import traceback
            self.log_message(f"📋 Traceback: {traceback.format_exc()}")
            return False

    def fusionar_datos_historicos(self):
        """
        Transfiere los datos de 'Tabla Base Datos' a 'DATOS HISTORICOS'
        
        Returns:
            dict: Resultado con éxito/error y detalles
        """
        try:
            self.log_message("🔄 Iniciando fusión de datos...")
            self.progress_callback(10, "Buscando tablas requeridas...")
            
            # Buscar las capas requeridas
            project = QgsProject.instance()
            tabla_base = None
            tabla_historicos = None
            
            # Encontrar tablas por nombre exacto
            for layer in project.mapLayers().values():
                if layer.name() == "Tabla Base Datos":
                    tabla_base = layer
                elif layer.name() == "DATOS HISTORICOS":
                    tabla_historicos = layer
            
            # Verificar que ambas tablas existan
            if not tabla_base:
                return {
                    'success': False,
                    'message': 'No se encontró la capa "Tabla Base Datos". Debe ejecutar el proceso de creación de tabla primero.'
                }
            
            if not tabla_historicos:
                return {
                    'success': False,
                    'message': 'No se encontró la capa "DATOS HISTORICOS". Cree esta capa primero.'
                }
            
            # Verificar que Tabla Base tenga registros
            if tabla_base.featureCount() == 0:
                return {
                    'success': False,
                    'message': 'La tabla "Tabla Base Datos" está vacía.'
                }
            
            self.log_message(f"✅ Tablas encontradas:")
            self.log_message(f"   • Tabla Base Datos: {tabla_base.featureCount()} registros")
            self.log_message(f"   • DATOS HISTORICOS: {tabla_historicos.featureCount()} registros")
            
            # Normalizar fechas en ambas tablas con auto-detección de formato
            self.progress_callback(20, "Normalizando fechas...")
            self.normalizar_fecha(tabla_base, "Tabla Base Datos")  # Auto-detectar formato
            self.normalizar_fecha(tabla_historicos, "DATOS HISTORICOS")  # Auto-detectar formato
            
            # Registrar los IDs de los registros históricos antes de la fusión para informe
            ids_antes = set()
            for f in tabla_historicos.getFeatures():
                ids_antes.add(f.id())
            
            # Copiar registros de Tabla Base a DATOS HISTORICOS
            self.progress_callback(50, "Copiando datos...")
            self.log_message("📝 Copiando datos de 'Tabla Base Datos' a 'DATOS HISTORICOS'...")
            
            registros_copiados = 0
            
            # Obtener todos los campos de ambas tablas
            campos_base = tabla_base.fields()
            campos_historicos = tabla_historicos.fields()
            
            # Verificar compatibilidad de campos
            if campos_base.count() != campos_historicos.count():
                self.log_message(f"⚠️ Las tablas tienen diferente número de campos: Base ({campos_base.count()}) vs Históricos ({campos_historicos.count()})")
                self.log_message("⚠️ Se copiarán solo los campos coincidentes por nombre")
            
            # Crear mapa de correspondencia de campos por nombre
            mapa_campos = {}
            for i in range(campos_base.count()):
                campo_base = campos_base.at(i)
                for j in range(campos_historicos.count()):
                    campo_hist = campos_historicos.at(j)
                    if campo_base.name() == campo_hist.name():
                        mapa_campos[i] = j
                        break
            
            self.log_message(f"ℹ️ Se encontraron {len(mapa_campos)} campos coincidentes entre las tablas")
            
            # Identificar índices clave para Upsert
            idx_hist_fecha = campos_historicos.lookupField("Fecha")
            idx_hist_muro = campos_historicos.lookupField("Muro")
            idx_hist_sector = campos_historicos.lookupField("Sector")
            idx_hist_plano = campos_historicos.lookupField("Plano")

            # Mapa de registros existentes para UPSERT
            # Clave: (fecha, muro, sector, nombre_base) -> Valor: feature_id
            registros_existentes = {}
            if idx_hist_fecha != -1 and idx_hist_muro != -1 and idx_hist_sector != -1:
                self.log_message("🔍 Construyendo índice de registros históricos (Fecha, Muro, Sector, Nombre) para Upsert...")
                for f in tabla_historicos.getFeatures():
                    # Extraer el nombre base del campo Plano, ej: P260105_MP_S3 -> 260105_MP_S3
                    nombre_base = ""
                    if idx_hist_plano != -1 and f.attribute(idx_hist_plano):
                        plano_str = str(f.attribute(idx_hist_plano)).strip()
                        nombre_base = plano_str[1:] if plano_str.startswith("P") else plano_str

                    key = (
                        str(f.attribute(idx_hist_fecha)).strip() if f.attribute(idx_hist_fecha) else "",
                        str(f.attribute(idx_hist_muro)).strip() if f.attribute(idx_hist_muro) else "",
                        str(f.attribute(idx_hist_sector)).strip() if f.attribute(idx_hist_sector) else "",
                        nombre_base
                    )
                    registros_existentes[key] = f.id()
            
            # Verificar si la capa está en modo de edición, si no, activarlo
            editing_started_copy = False
            if not tabla_historicos.isEditable():
                tabla_historicos.startEditing()
                editing_started_copy = True
            
            registros_actualizados = 0
            registros_nuevos = 0

            try:
                # Copiar registros (Upsert)
                for f_base in tabla_base.getFeatures():
                    new_f = QgsFeature(tabla_historicos.fields())
                    
                    # Copiar valores de campos coincidentes
                    for idx_base, idx_hist in mapa_campos.items():
                        new_f.setAttribute(idx_hist, f_base.attributes()[idx_base])
                    
                    # Lógica UPSERT
                    if idx_hist_fecha != -1 and idx_hist_muro != -1 and idx_hist_sector != -1:
                        nombre_base_new = ""
                        if idx_hist_plano != -1 and new_f.attribute(idx_hist_plano):
                            plano_str = str(new_f.attribute(idx_hist_plano)).strip()
                            nombre_base_new = plano_str[1:] if plano_str.startswith("P") else plano_str

                        key = (
                            str(new_f.attribute(idx_hist_fecha)).strip() if new_f.attribute(idx_hist_fecha) else "",
                            str(new_f.attribute(idx_hist_muro)).strip() if new_f.attribute(idx_hist_muro) else "",
                            str(new_f.attribute(idx_hist_sector)).strip() if new_f.attribute(idx_hist_sector) else "",
                            nombre_base_new
                        )
                        if key in registros_existentes:
                            fid = registros_existentes[key]
                            tabla_historicos.deleteFeature(fid)
                            registros_actualizados += 1
                        else:
                            registros_nuevos += 1
                    else:
                        registros_nuevos += 1
                    
                    tabla_historicos.addFeature(new_f)
                    registros_copiados += 1
            
            finally:
                # Confirmar cambios y salir del modo de edición si lo iniciamos
                if editing_started_copy:
                    tabla_historicos.commitChanges()
            
            # Registrar los IDs después para calcular nuevos registros
            ids_despues = set()
            for f in tabla_historicos.getFeatures():
                ids_despues.add(f.id())
            
            nuevos_ids_reales = ids_despues - ids_antes
            
            self.progress_callback(100, "¡Fusión completada!")
            self.log_message(f"✅ Fusión completada: {registros_copiados} procesados en total")
            if registros_actualizados > 0:
                self.log_message(f"   🔄 {registros_actualizados} registros antiguos fueron actualizados (Upsert)")
            self.log_message(f"   ➕ {registros_nuevos} registros fueron añadidos como nuevos")
            self.log_message(f"📊 Tabla DATOS HISTORICOS ahora tiene {tabla_historicos.featureCount()} registros totales")
            
            return {
                'success': True,
                'message': f'Datos fusionados exitosamente: {registros_copiados} registros procesados ({registros_actualizados} actualizados, {registros_nuevos} nuevos)',
                'registros_copiados': registros_copiados,
                'nuevos_ids': len(nuevos_ids_reales),
                'total_registros': tabla_historicos.featureCount()
            }
            
        except Exception as e:
            import traceback
            error_msg = f"Error durante la fusión de datos: {str(e)}"
            error_details = traceback.format_exc()
            self.log_message(f"❌ {error_msg}")
            self.log_message(f"📋 Detalles del error:\n{error_details}")
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }
    
    def diagnosticar_formatos_fecha(self):
        """
        Diagnostica los formatos de fecha actuales en ambas tablas
        sin realizar ninguna modificación
        
        Returns:
            dict: Información sobre los formatos detectados
        """
        try:
            self.log_message("🔍 Diagnosticando formatos de fecha en las tablas...")
            
            # Buscar las capas requeridas
            project = QgsProject.instance()
            tabla_base = None
            tabla_historicos = None
            
            for layer in project.mapLayers().values():
                if layer.name() == "Tabla Base Datos":
                    tabla_base = layer
                elif layer.name() == "DATOS HISTORICOS":
                    tabla_historicos = layer
            
            resultados = {}
            
            if tabla_base:
                formato_base = self.detectar_formato_fecha(tabla_base, "Tabla Base Datos")
                resultados["tabla_base"] = {
                    "formato": formato_base,
                    "registros": tabla_base.featureCount()
                }
            else:
                self.log_message("❌ No se encontró 'Tabla Base Datos'")
                resultados["tabla_base"] = None
            
            if tabla_historicos:
                formato_hist = self.detectar_formato_fecha(tabla_historicos, "DATOS HISTORICOS")
                resultados["tabla_historicos"] = {
                    "formato": formato_hist,
                    "registros": tabla_historicos.featureCount()
                }
            else:
                self.log_message("❌ No se encontró 'DATOS HISTORICOS'")
                resultados["tabla_historicos"] = None
            
            return {
                'success': True,
                'message': 'Diagnóstico completado',
                'resultados': resultados
            }
            
        except Exception as e:
            import traceback
            self.log_message(f"❌ Error en diagnóstico: {str(e)}")
            return {
                'success': False,
                'message': f'Error en diagnóstico: {str(e)}',
                'details': traceback.format_exc()
            }

    def normalizar_solo_fechas(self):
        """
        Ejecuta solo la normalización de fechas en ambas tablas
        sin realizar la fusión de datos
        
        Returns:
            dict: Resultado de la operación
        """
        try:
            self.log_message("📅 Ejecutando normalización de fechas solamente...")
            
            # Buscar las capas requeridas
            project = QgsProject.instance()
            tabla_base = None
            tabla_historicos = None
            
            for layer in project.mapLayers().values():
                if layer.name() == "Tabla Base Datos":
                    tabla_base = layer
                elif layer.name() == "DATOS HISTORICOS":
                    tabla_historicos = layer
            
            if not tabla_base and not tabla_historicos:
                return {
                    'success': False,
                    'message': 'No se encontraron las tablas "Tabla Base Datos" o "DATOS HISTORICOS"'
                }
            
            resultados = []
            
            if tabla_base:
                self.log_message(f"🔄 Normalizando 'Tabla Base Datos' ({tabla_base.featureCount()} registros)...")
                exito_base = self.normalizar_fecha(tabla_base, "Tabla Base Datos")
                resultados.append(f"Tabla Base Datos: {'✅ OK' if exito_base else '❌ Error'}")
            
            if tabla_historicos:
                self.log_message(f"🔄 Normalizando 'DATOS HISTORICOS' ({tabla_historicos.featureCount()} registros)...")
                exito_hist = self.normalizar_fecha(tabla_historicos, "DATOS HISTORICOS")
                resultados.append(f"DATOS HISTORICOS: {'✅ OK' if exito_hist else '❌ Error'}")
            
            return {
                'success': True,
                'message': 'Normalización de fechas completada',
                'detalles': resultados
            }
            
        except Exception as e:
            import traceback
            self.log_message(f"❌ Error en normalización: {str(e)}")
            return {
                'success': False,
                'message': f'Error en normalización: {str(e)}',
                'details': traceback.format_exc()
            }

    def log_message(self, message):
        """Enviar mensaje al log a través del callback"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)