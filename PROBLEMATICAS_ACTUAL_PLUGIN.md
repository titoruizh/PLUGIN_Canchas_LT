# PROBLEMÁTICAS ACTUALES DEL PLUGIN

## 1. UI con Pestañas Manuales
El pipeline siempre es 1→2→3→4, nunca se salta un paso. Las pestañas obligan al usuario a ejecutar manualmente cada paso uno por uno. Es ineficiente y solo el creador sabe el orden correcto.

## 2. Capa de Fondo (Paso 3.2) — Pre-fusión Manual de DEMs
El paso 3.2 pide una "capa de fondo" que es un raster .tif. Para tenerla, el usuario debe abrir otro programa (Global Mapper), cargar los 3 DEMs (MP, MO, ME), exportarlos como 1 solo .tif, y recién ahí cargarlo al proyecto QGIS. Idealmente el usuario selecciona los rasters y se fusionan automáticamente durante el proceso.

## 3. DATOS HISTORICOS (Paso 4) — Copia Manual
La tabla "DATOS HISTORICOS" (CSV) debe copiarse manualmente al root del proyecto y luego cargarse al .qgz antes de ejecutar el paso 4. Este proceso se realiza mes a mes y no se quiere mezclar datos entre meses. La tabla se guarda en carpeta root mes por mes para auditoría/trazabilidad.

## 4. No se Guarda el Proyecto .qgz
Al terminar el pipeline, no se guarda un .qgz en la carpeta root. Si el usuario quiere volver a ver qué pasó en ese proceso, no puede. Debería poder abrir el proyecto, ver las capas, modificar pequeños datos (Tabla Base Datos) y re-exportar la plantilla.

## 5. DEMs No se Guardan en Root
Los DEM (DEM_MP, DEM_MO, DEM_ME .tif) no quedan guardados en la carpeta root para referencia futura.

## 6. Capas Geoespaciales No Quedan en Root
En paso 2 se generan puntos, polígonos y triangulaciones pero no se guardan en el root. Cuando se guarde el .qgz final, estas capas deberían estar referenciadas y disponibles al reabrir.

## 7. Tabla Base Datos No se Exporta
"Tabla Base Datos" no se guarda automáticamente en el root al terminar el pipeline.

## 8. Plugin Solo Usable por el Creador
La herramienta funciona pero está armada como "Frankenstein". Solo el creador sabe cómo operarla. Debería ser más intuitiva, más fácil, menos enredada para cualquier operador.
