# PLAN: Pipeline Lineal — Ventana Unificada

> **Objetivo**: Reemplazar las 4 pestañas por una sola ventana con 2 vistas: **Configuración** y **Ejecución**. Al finalizar la ejecución se abre el Compositor (lo que hoy hace el último botón de la pestaña 4).
> 
> **Regla de oro**: No destruir la app. El `canchas_dialog.py` actual se mantiene intacto como respaldo. La nueva ventana llama a los **mismos procesadores core** existentes.

---

## Diseño de la Ventana

```
┌─────────────────────────────────────────────────────────────────────┐
│  🏗️ CANCHAS LAS TORTOLAS — Pipeline Topográfico                    │
├──────────────────────────────────┬──────────────────────────────────┤
│   PANEL CONFIGURACIÓN            │   CONSOLA (sidebar derecha)     │
│                                  │   📋 Historial de Operaciones   │
│   ═══ RUTAS PRINCIPALES ═══     │   ┌────────────────────────┐    │
│   📁 PROC_ROOT:      [....] 📂  │   │ [11:02:03] ⚙️ Inician.│    │
│   📦 GPKG Original:  [....] 📂  │   │ [11:02:07] ✅ DEM_MP..│    │
│   📂 CSV-ASC:        [....] 📂  │   │ [11:02:08] 📊 Filtrad.│    │
│   📂 Imágenes:       [....] 📂  │   │ ...                    │    │
│                                  │   └────────────────────────┘    │
│   ═══ PROCESAMIENTO ═══         │                                  │
│   ☑ Puntos (.csv)               │                                  │
│   ☑ Polígonos (.shp)            │                                  │
│   ☑ Triangulaciones (.tif)      │                                  │
│                                  │                                  │
│   ═══ TABLA BASE ═══            │                                  │
│   � Protocolo inicial: [1]     │                                  │
│                                  │                                  │
│   ═══ VOLÚMENES + PANTALLAZOS ══│                                  │
│   Puntos aleatorios:    [20]     │                                  │
│   Espesor mínimo:      [0.01] m │                                  │
│   Algoritmo remuestreo: [bilin] │                                  │
│   Dimensiones: [800]x[500] px   │                                  │
│   Factor expansión:    [1.3]     │                                  │
│   Capa de fondo:       [tif]     │                                  │
│                                  │                                  │
│   ═══ DATOS REPORTE ═══         │                                  │
│   Días crec. anual:    [365]     │                                  │
│                                  │                                  │
│   ──────────────────────         │                                  │
│   [▶️ EJECUTAR PIPELINE COMPLETO]│   [████████░░░░] 65%            │
│   [🖨️ Abrir Compositor]          │   Paso 4/6: Datos Reporte...   │
│                                  │                                  │
│   [Cerrar Plugin]                │                                  │
└──────────────────────────────────┴──────────────────────────────────┘
```

---

## Parámetros Configurables (todos los que existen hoy)

| Sección | Widget | Default | Origen actual |
|---------|--------|---------|--------------|
| **Rutas** | | | `validation_tab.py` |
| PROC_ROOT | QLineEdit + folder picker | `""` | `self.proc_root` |
| GPKG Original | QLineEdit + file picker (.gpkg) | `""` | `self.gpkg_path` |
| Carpeta CSV-ASC | QLineEdit + folder picker | `""` | `self.csv_folder` |
| Carpeta Imágenes | QLineEdit + folder picker | `""` | `self.img_folder` |
| **Procesamiento** | | | `processing_tab.py` |
| Exportar Puntos (.csv) | QCheckBox | `False` | `self.chk_points` |
| Exportar Polígonos (.shp) | QCheckBox | `True` | `self.chk_polygons` |
| Exportar Triangulaciones (.tif) | QCheckBox | `True` | `self.chk_tin` |
| **Tabla Base** | | | `table_subtab.py` |
| Protocolo topográfico inicial | QSpinBox (1-9999) | `1` | `self.protocolo_inicio` |
| **Volúmenes + Pantallazos** | | | `volumes_subtab.py` |
| Puntos aleatorios | QSpinBox (5-100) | `20` | `self.num_random_points` |
| Espesor mínimo (m) | QLineEdit | `0.01` | `self.min_espesor` |
| Algoritmo remuestreo | QComboBox | `bilinear` | `self.resample_algorithm` |
| Ancho pantallazo (px) | QSpinBox (400-2000) | `800` | `self.screenshot_width` |
| Alto pantallazo (px) | QSpinBox (300-1500) | `500` | `self.screenshot_height` |
| Factor expansión | QDoubleSpinBox (1.0-3.0) | `1.3` | `self.expansion_factor` |
| Capa de fondo | QLineEdit | `tif` | `self.background_layer` |
| **XML** | | | `xml_subtab.py` |
| *(sin parámetros configurables)* | — | — | Hardcoded |
| **Datos Reporte** | | | `reports_tab.py` |
| Días crecimiento anual | QSpinBox (30-730) | `365` | `self.dias_crecimiento` |

---

## Secuencia de Ejecución del Pipeline

Al presionar **"▶️ Ejecutar Pipeline Completo"**, se ejecutan en orden:

```
Paso 1/6: Validación
  → ValidationProcessor.ejecutar_validacion_completa()
  → Usa: proc_root, gpkg_path, csv_folder, img_folder

Paso 2/6: Procesamiento Espacial
  → ProcessingProcessor.ejecutar_procesamiento_completo(export_options)
  → Usa: proc_root, chk_points, chk_polygons, chk_tin

Paso 3/6: Crear Tabla Base Datos
  → TableCreationProcessor.ejecutar_creacion_tabla_completa()
  → Usa: proc_root, protocolo_inicio

Paso 4/6: Volúmenes + Pantallazos
  → VolumeScreenshotProcessor.ejecutar_calculo_volumenes_con_pantallazos()
  → Usa: proc_root, num_random_points, min_espesor, resample_algorithm,
          screenshot_width, screenshot_height, expansion_factor, background_layer

Paso 5/6: Exportar XML
  → XMLExportProcessor.ejecutar_exportacion_xml_completa()
  → Usa: proc_root

Paso 6/6: Datos Reporte
  → DataMergeProcessor + HistoricalAnalysis + Charts + Heatmap + Classification
  → Usa: proc_root, dias_crecimiento

── Pipeline terminado ──
  → Botón "Abrir Compositor" se habilita
  → Al presionarlo: ejecuta reports_tab.abrir_compositor_plantilla(proc_root)
```

---

## Archivos a Crear / Modificar

### [NEW] `gui/pipeline_dialog.py`
Ventana principal nueva. Contiene:
- Panel izquierdo: todos los widgets de configuración agrupados por sección
- Panel derecho: consola de log (idéntica a la actual)
- Barra de progreso global con indicador de paso actual
- Botón "Ejecutar Pipeline Completo" 
- Botón "Abrir Compositor" (habilitado solo después de ejecutar)
- Botón "Cerrar Plugin"
- Persistencia de settings con QSettings (mismas keys actuales)

### [MODIFY] `canchas_las_tortolas.py`
- Cambiar el punto de entrada para abrir `PipelineDialog` en vez de `CanchasDialog`
- Mantener `CanchasDialog` accesible (opcionalmente como atajo)

### SIN CAMBIOS
- **Todos los archivos `core/`** — No se toca ningún procesador
- **`canchas_dialog.py`** — Se mantiene intacto como respaldo
- **Todos los `gui/tabs/`** — No se modifican, se reusan sus procesadores

---

## Interacción con Procesadores Core

La nueva ventana **NO reimplementa lógica**. Solo llama a los mismos procesadores con los mismos parámetros:

```python
# Ejemplo de cómo el pipeline llama a cada paso (pseudo-código)

def ejecutar_pipeline(self):
    proc_root = self.proc_root.text()
    
    # Paso 1
    self.log("📋 Paso 1/6: Validación...")
    from ..core.validation import ValidationProcessor
    vp = ValidationProcessor(proc_root, self.gpkg.text(), self.csv.text(), self.img.text(), 
                             progress_callback=..., log_callback=...)
    if not vp.ejecutar_validacion_completa()['success']:
        return self.log("❌ Falló paso 1")
    
    # Paso 2
    self.log("🗺️ Paso 2/6: Procesamiento Espacial...")
    from ..core.processing import ProcessingProcessor
    pp = ProcessingProcessor(proc_root, pixel_size=0.25, ...)
    export_opts = {'points': self.chk_points.isChecked(), ...}
    if not pp.ejecutar_procesamiento_completo(export_opts)['success']:
        return self.log("❌ Falló paso 2")
    
    # Paso 3 → TableCreationProcessor
    # Paso 4 → VolumeScreenshotProcessor  
    # Paso 5 → XMLExportProcessor
    # Paso 6 → DataMerge + Historical + Charts + Heatmap + Classification
    
    self.log("🎉 PIPELINE COMPLETO")
    self.btn_compositor.setEnabled(True)
```

---

## Manejo de Errores

- Si un paso falla, el pipeline **SE DETIENE** y muestra el error en la consola
- El usuario puede corregir y re-ejecutar desde el principio
- El botón "Abrir Compositor" **solo se habilita** si el pipeline llegó hasta el final

---

## Persistencia de Configuración

Se reusan las mismas QSettings keys actuales:
```
canchas/proc_root
canchas/gpkg_path
canchas/csv_folder
canchas/img_folder
```

Se agregan keys para los parámetros que actualmente no se persisten:
```
canchas/protocolo_inicio
canchas/min_espesor
canchas/screenshot_width
canchas/screenshot_height
canchas/expansion_factor
canchas/background_layer
canchas/dias_crecimiento
canchas/chk_points
canchas/chk_polygons
canchas/chk_tin
```

---

## Validación Pre-Ejecución

Antes de iniciar el pipeline, validar que todas las rutas obligatorias estén configuradas:
- ✅ PROC_ROOT no vacío y carpeta existe
- ✅ GPKG path no vacío y archivo existe
- ✅ CSV folder no vacío y carpeta existe
- ✅ IMG folder no vacío y carpeta existe

Si falta alguna → mostrar error y no ejecutar.
