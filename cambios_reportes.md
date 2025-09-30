# Cambios en la funcionalidad de reportes

## Cambios realizados

1. Se ha modificado el flujo de trabajo para la generación de reportes:
   - Antes: El plugin generaba los reportes PDF automáticamente
   - Ahora: El plugin prepara los datos, y el usuario crea los reportes manualmente en el compositor de QGIS

2. Cambios en la interfaz:
   - La pestaña "4. Reportes" ahora se llama "4. Datos Reporte"
   - El botón "Generar Reportes PDF por Muro" ahora dice "Generar Datos Reporte"

3. Nueva funcionalidad:
   - El botón ahora ejecuta una operación de fusión de datos
   - Copia datos de "Tabla Base Datos" a "DATOS HISTORICOS"
   - Normaliza las fechas en ambas tablas
   - La tabla "DATOS HISTORICOS" contiene todos los datos y debe usarse como fuente para los reportes manuales

## Flujo de trabajo actualizado

1. Ejecutar los procesos de validación, procesamiento y análisis normalmente
2. Cuando llegue a la pestaña "4. Datos Reporte", haga clic en "Generar Datos Reporte"
3. Esto actualizará la tabla "DATOS HISTORICOS" con todos los datos
4. Use el compositor de impresiones de QGIS para crear sus reportes manualmente
5. Seleccione "DATOS HISTORICOS" como fuente de datos en el compositor

## Beneficios

- Mayor control sobre el diseño de los reportes
- Posibilidad de personalizar cada reporte según las necesidades
- Flujo de trabajo más flexible
- Conservación de datos históricos en una sola tabla