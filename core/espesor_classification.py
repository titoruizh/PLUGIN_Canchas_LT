# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Espesor Classification module for Canchas Las Tortolas plugin
                                 A QGIS plugin
 Plugin para procesamiento de canchas Las Tortolas - Linkapsis
                             -------------------
        begin                : 2024-08-13
        git sha              : $Format:%H$
        copyright            : (C) 2024 by Linkapsis
        email                : info@linkapsis.com
 ***************************************************************************/
"""

from qgis.core import QgsProject, QgsField, QgsVectorLayer
from PyQt5.QtCore import QVariant

class EspesorClassificationProcessor:
    """Procesador para clasificación automática de espesores"""
    
    def __init__(self, progress_callback=None, log_callback=None):
        """
        Inicializar procesador de clasificación de espesores
        
        Args:
            progress_callback: Función callback para actualizar progreso
            log_callback: Función callback para logs
        """
        self.progress_callback = progress_callback or (lambda x, msg="": None)
        self.log_callback = log_callback or (lambda msg: print(msg))

    def clasificar_espesor(self, espesor_value):
        """
        Clasifica un valor de espesor según las reglas especificadas:
        
        Mayor a 1.3 = "Triple Capa"
        Mayor a 0.8 = "Doble Capa" 
        Mayor a 0.2 = "Relleno"
        Entre -0.2 a 0.2 = "Corte Relleno"
        Menor a -0.2 = "Corte"
        
        Args:
            espesor_value: Valor numérico del espesor
            
        Returns:
            str: Categoría correspondiente
        """
        if espesor_value is None:
            return ""
        
        try:
            espesor = float(espesor_value)
            
            if espesor > 1.3:
                return "Triple Capa"
            elif espesor > 0.8:
                return "Doble Capa"
            elif espesor > 0.2:
                return "Relleno"
            elif espesor >= -0.2:  # Entre -0.2 y 0.2 (inclusive)
                return "Corte Relleno"
            else:  # < -0.2
                return "Corte"
                
        except (ValueError, TypeError):
            self.log_callback(f"⚠️ Valor de espesor inválido: {espesor_value}")
            return ""

    def agregar_columna_comentarios_espesor(self, tabla_nombre="Tabla Base Datos"):
        """
        Agrega la columna 'Comentarios Espesor' a la tabla especificada y la llena
        con las clasificaciones automáticas basadas en la columna 'Espesor'
        
        Args:
            tabla_nombre: Nombre de la tabla a modificar
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            self.progress_callback(10, "Buscando tabla 'Tabla Base Datos'...")
            
            # Buscar la tabla en el proyecto
            project = QgsProject.instance()
            tabla = None
            
            for layer in project.mapLayers().values():
                if layer.name() == tabla_nombre and isinstance(layer, QgsVectorLayer):
                    tabla = layer
                    break
            
            if not tabla:
                return {
                    'success': False,
                    'message': f'No se encontró la tabla "{tabla_nombre}" en el proyecto.'
                }
            
            # Verificar si la columna 'Espesor' existe
            self.progress_callback(20, "Verificando columna 'Espesor'...")
            idx_espesor = tabla.fields().indexFromName("Espesor")
            if idx_espesor == -1:
                return {
                    'success': False,
                    'message': 'No se encontró la columna "Espesor" en la tabla.'
                }
            
            # Verificar si la columna 'Comentarios Espesor' ya existe
            self.progress_callback(30, "Verificando columna 'Comentarios Espesor'...")
            idx_comentarios = tabla.fields().indexFromName("Comentarios Espesor")
            
            if idx_comentarios == -1:
                # Agregar la nueva columna
                self.progress_callback(40, "Agregando columna 'Comentarios Espesor'...")
                self.log_callback("➕ Agregando columna 'Comentarios Espesor' a la tabla...")
                
                # Crear el nuevo campo
                nuevo_campo = QgsField("Comentarios Espesor", QVariant.String)
                
                # Iniciar edición
                tabla.startEditing()
                
                # Agregar el campo
                if not tabla.dataProvider().addAttributes([nuevo_campo]):
                    tabla.rollBack()
                    return {
                        'success': False,
                        'message': 'No se pudo agregar la columna "Comentarios Espesor".'
                    }
                
                # Actualizar campos
                tabla.updateFields()
                idx_comentarios = tabla.fields().indexFromName("Comentarios Espesor")
                
                self.log_callback("✔️ Columna 'Comentarios Espesor' agregada exitosamente.")
            else:
                # La columna ya existe, iniciar edición para actualizarla
                self.progress_callback(40, "Columna 'Comentarios Espesor' ya existe, actualizando valores...")
                self.log_callback("🔄 La columna 'Comentarios Espesor' ya existe, actualizando valores...")
                tabla.startEditing()
            
            # Procesar todos los registros
            self.progress_callback(50, "Procesando registros...")
            registros_actualizados = 0
            total_registros = tabla.featureCount()
            
            # Diccionario para almacenar los cambios
            cambios = {}
            
            for feature in tabla.getFeatures():
                espesor_value = feature[idx_espesor]
                clasificacion = self.clasificar_espesor(espesor_value)
                
                # Preparar cambio
                cambios[feature.id()] = {idx_comentarios: clasificacion}
                registros_actualizados += 1
                
                # Log detallado para los primeros registros
                if registros_actualizados <= 5:
                    self.log_callback(f"📝 Registro {registros_actualizados}: Espesor={espesor_value} → '{clasificacion}'")
            
            # Aplicar todos los cambios de una vez
            self.progress_callback(80, f"Aplicando cambios a {registros_actualizados} registros...")
            if cambios:
                if not tabla.dataProvider().changeAttributeValues(cambios):
                    tabla.rollBack()
                    return {
                        'success': False,
                        'message': 'Error al aplicar los cambios a la tabla.'
                    }
            
            # Confirmar cambios
            self.progress_callback(90, "Confirmando cambios...")
            if not tabla.commitChanges():
                return {
                    'success': False,
                    'message': 'Error al confirmar los cambios en la tabla.'
                }
            
            # Actualizar la tabla en la interfaz
            tabla.triggerRepaint()
            
            self.progress_callback(100, "¡Clasificación completada!")
            self.log_callback(f"✅ Clasificación de espesores completada: {registros_actualizados} registros procesados.")
            
            # Mostrar resumen de clasificaciones
            if registros_actualizados > 0:
                self.generar_resumen_clasificacion(tabla, idx_comentarios)
            
            return {
                'success': True,
                'message': f'Columna "Comentarios Espesor" creada/actualizada exitosamente.',
                'registros_procesados': registros_actualizados,
                'tabla_nombre': tabla_nombre
            }
            
        except Exception as e:
            import traceback
            error_msg = f"Error durante la clasificación de espesores: {str(e)}"
            error_details = traceback.format_exc()
            self.log_callback(f"❌ {error_msg}")
            self.log_callback(f"📋 Detalles del error:\n{error_details}")
            
            # Si hay una tabla en edición, hacer rollback
            try:
                if 'tabla' in locals() and tabla and tabla.isEditable():
                    tabla.rollBack()
            except:
                pass
            
            return {
                'success': False,
                'message': error_msg,
                'details': error_details
            }

    def generar_resumen_clasificacion(self, tabla, idx_comentarios):
        """
        Genera un resumen de las clasificaciones realizadas
        
        Args:
            tabla: Capa de la tabla
            idx_comentarios: Índice de la columna de comentarios
        """
        try:
            # Contar clasificaciones
            conteos = {}
            for feature in tabla.getFeatures():
                clasificacion = feature[idx_comentarios]
                if clasificacion:
                    conteos[clasificacion] = conteos.get(clasificacion, 0) + 1
            
            # Mostrar resumen
            self.log_callback("📊 RESUMEN DE CLASIFICACIONES:")
            for clasificacion, count in sorted(conteos.items()):
                self.log_callback(f"   • {clasificacion}: {count} registros")
            
            total = sum(conteos.values())
            self.log_callback(f"   📋 Total clasificado: {total} registros")
            
        except Exception as e:
            self.log_callback(f"⚠️ Error al generar resumen: {str(e)}")

    def ejecutar_clasificacion_espesor(self):
        """Método principal para ejecutar la clasificación de espesores"""
        return self.agregar_columna_comentarios_espesor()