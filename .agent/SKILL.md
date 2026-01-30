---
description: Arquitectura y funcionamiento del Plugin QGIS para Automatización Topográfica (Canchas Las Tórtolas)
---

# QGIS Automation & Topography Architecture - Las Tortolas Plugin

## 1. Visión General del Sistema
Este plugin es una solución empresarial de automatización para el procesamiento topográfico de "Canchas" (áreas de depósito/trabajo) en minería. Transforma datos crudos de levantamientos (puntos CSV/ASC) en productos entregables complejos: cálculos volumétricos, planos de planta, perfiles transversales, análisis históricos y reportes automatizados.

Como Arquitecto de Software, el sistema ha sido diseñado bajo un patrón **Modular-Jerárquico** con clara separación de responsabilidades (SoC) entre la Capa de Presentación (GUI) y la Capa de Lógica de Negocio (Core).

## 2. Pila Tecnológica
*   **Platform:** QGIS 3.x API (PyQGIS)
*   **GUI:** PyQt5 (Widgets, Signals/Slots)
*   **Data Processing:** NumPy, Pandas (implícito en lógica vectores), QgsProcessing algorithms.
*   **Visualization:** Matplotlib (gráficos estáticos), QGIS Layouts (reportes PDF).
*   **Persistence:** QSettings (configuración de usuario), GeoPackage/Shapefiles (datos espaciales).

## 3. Arquitectura del Software

### 3.1. Patrón de Diseño Principal: Bridge & Orchestrator
El archivo `canchas_dialog.py` actúa como el **Orquestador Principal**. No contiene lógica de procesamiento pesado. Su función es:
1.  Inicializar la GUI principal.
2.  Instanciar las Pestañas (Tabs).
3.  Conectar señales (Signals) de las pestañas con métodos puente (`Bridge Methods`).
4.  Mantener el estado global de la sesión (ej. `proc_root`).

### 3.2. Estructura Modular (File System)

```text
PLUGIN_ROOT/
├── canchas_dialog.py        # Controlador Principal
├── gui/
│   └── tabs/                # Componentes de UI (Vistas)
│       ├── validation_tab.py    # Fase 1: Validar Inputs
│       ├── processing_tab.py    # Fase 2: Generar DEMs/TINs
│       ├── analysis_tab.py      # Fase 3: Contenedor de Sub-tabs
│       │   └── analysis/
│       │       ├── table_subtab.py   # Gestión tabla atributos
│       │       ├── volumes_subtab.py # Cálculo vols + pantallazos
│       │       └── xml_subtab.py     # Exportación LandXML
│       └── reports_tab.py       # Fase 4: Reportes y Histórico
├── core/                    # Lógica de Negocio (Modelos/Servicios)
│   ├── validation.py            # Reglas de validación topológica
│   ├── processing.py            # Algoritmos QGIS (IDW, TIN)
│   ├── volume_screenshot.py     # Motor de cálculo volumétrico y rendering
│   ├── data_merge.py            # Fusión de datasets históricos
│   ├── historical_analysis.py   # Lógica temporal (Crecimiento/Intervención)
│   ├── bar_charts_simple.py     # Generación de gráficos
│   └── ...
└── resources/               # Assets (Iconos, Plantillas QPT)
```

## 4. Flujo de Datos (Data Pipeline)

El sistema procesa la información en 4 fases secuenciales estrictas, garantizando la integridad de los datos topográficos.

### Fase 1: Validación (`ValidationTab` -> `validation.py`)
*   **Input:** Archivos crudos (ASCII/CSV) del levantamiento.
*   **Lógica:** Verifica integridad de archivos, coordenadas válidas y estructura de nombres.
*   **Output:** Archivos validados listos para procesar.

### Fase 2: Procesamiento Espacial (`ProcessingTab` -> `processing.py`)
*   **Process:** Convierte nubes de puntos en superficies continuas.
*   **Algoritmos:**
    *   Generación de TIN (Triangulated Irregular Network) para alta precisión en volúmenes.
    *   Generación de DEM (Digital Elevation Model) para análisis visual y perfiles.
*   **Output:** Rasters (TIF) y Vectores (SHP/GPKG) en `PROC_ROOT`.

### Fase 3: Análisis Topográfico (`AnalysisTab` -> `volume_screenshot.py`)
*   **Core:** Es el corazón matemático del plugin.
*   **Cálculo de Volumen:** Diferencia entre Superficie Actual (TIN Nuevo) vs Superficie Anterior (DEM Muro Base).
    *   *Feature:* Filtrado de outliers estadísticos para eliminar ruido de maquinaria/vegetación.
*   **Screenshots:** Rendering automático de vistas en planta con simbología de calor (Corte/Relleno).
*   **Perfiles:** Generación de líneas de corte transversal automáticas.
*   **Pegado Incremental:** Actualiza el "Muro Maestro" con la nueva superficie, manteniendo un modelo digital del terreno vivo y actualizado.

### Fase 4: Inteligencia y Reportes (`ReportsTab` -> `historical_analysis.py`)
*   **Data Warehousing:** Fusiona los datos del levantamiento actual con el histórico (`DATOS HISTORICOS`).
*   **Business Logic:**
    *   *Crecimiento Anual:* Sumatoria de espesores en ventana de tiempo (ej. 365 días).
    *   *Movimiento de Tierra:* Balance neto (Relleno - Corte).
*   **Visualization:** Genera gráficos de barras y series de tiempo para la evolución de la cancha.
*   **Final Output:** Atlas de QGIS (PDF Automatizado) usando plantillas `.qpt`.

## 5. Decisiones de Diseño Críticas

### 5.1. Manejo de Recursos QGIS
QGIS bloquea archivos raster si las capas están cargadas.
*   **Solución:** Se implementó una gestión agresiva de limpieza (`cleanup_temp_files`) y cierre de proveedores de datos (`QgsRasterLayer` references) para permitir la sobrescritura de archivos temporales en Windows.

### 5.2. Persistencia de Sesión
El uso de `QSettings` permite que el Ingeniero Topógrafo mantenga su contexto de trabajo (`PROC_ROOT`) entre reinicios del plugin, vital para flujos de trabajo que duran horas.

### 5.3. Interfaz No Bloqueante
Todas las operaciones pesadas emiten señales de progreso (`progress_signal`) que actualizan la UI sin congelarla (aunque actualmente corre en el hilo principal por limitaciones de la API de gráfica de QGIS, está preparado para moverse a `QTask` en el futuro).

---

## 6. Algoritmos Avanzados (Topografía de Precisión)

### 6.1. Slope Projection v6.3 (Smart Cut & Fill)
Implementado en `volume_screenshot.volume_screenshot_tool._apply_transition_skirt`.
Este algoritmo resuelve el problema de la integración de "Parches" (nuevos levantamientos) sobre el "Muro Base" (topografía existente), eliminando artefactos visuales y huecos.

**Lógica del Algoritmo:**
1.  **Detección de Contexto (Bidireccional):**
    *   No asume solo Relleno (Terraplén). Analiza la topografía circundante.
    *   Si el terreno vecino es más BAJO que el parche -> Proyecta **Relleno** (Talud hacia abajo).
    *   Si el terreno vecino es más ALTO que el parche -> Proyecta **Corte** (Talud hacia arriba/Excavación).
    
2.  **Proyección Geométrica (1:1):**
    *   Proyecta un talud físico real con pendiente 1:1 (45°) desde el borde del parche.
    *   Formula: `Z_proj = Z_borde + (Dirección * Distancia * 1.0)`
    *   Esto genera una estética de "movimiento de tierras" realista, simulando maquinaria pesada.

3.  **Cierre de Gaps (Void Filling):**
    *   Rellena vacíos de información (NoData) entre la cancha y el cerro usando la proyección calculada.
    *   Extiende la búsqueda hasta **100 px** para asegurar conexión sólida.

### 6.2. Gestión de Resolución Adaptativa (Upsampling v6.1)
El sistema garantiza que la calidad visual del talud generado sea siempre Alta Definición (HD), independiente de la calidad del Muro Base.

*   **Detección:** Compara la resolución del Muro vs el Parche.
*   **Acción:** Si el Muro tiene menor resolución (ej. 1.0m) que el Parche (ej. 0.25m), realiza un **Upsampling Automático** del Muro a 0.25m usando interpolación Bilineal.
*   **Resultado:** El talud se dibuja con la densidad de píxeles del parche, evitando el "pixelado" en las pendientes.

### 6.3. Optimización de Compresión (GDAL Predictor)
Debido al aumento de resolución (Upsampling), el tamaño de archivo puede dispararse. Se implementó una estrategia de compresión agresiva:

*   **Formato:** GTiff (BigTIFF enabled)
*   **Compresión:** `DEFLATE` (Lossless)
*   **Predictor:** `3` (Floating Point Predictor).
    *   *Impacto:* Reduce el peso de archivos de elevación (float32) drásticamente (ej. de 400MB a ~80-100MB) al predecir valores decimales secuenciales.

### 6.4. Cálculo de Dimensiones Geométrico (Robustez V3)
Implementado en `core/table_creation.py` (Enero 2026).
Resuelve la inconsistencia de mediciones en canchas con orientaciones complejas o geometrías curvas ("banana shape").

*   **Problema Anterior:** Los algoritmos basados en Bounding Box (AABB) o Transectas fallaban en rotaciones específicas (ej. Azimuth ~64°), reportando anchos incorrectos (ej. 49m vs 9m).
*   **Solución V3 (Geometría Pura):**
    1.  **Largo (Diámetro Geodésico):** Se calcula la distancia euclidiana máxima entre cualquier par de vértices del polígono (fuerza bruta optimizada). Esto es invariante a la rotación.
    2.  **Ancho (Derivado del Área):** `Ancho = Area / Largo`.
    *   *Principio:* Matemáticamente infalible. Si el área y el largo máximo son correctos, el ancho promedio derivado es exacto, eliminando artefactos de muestreo espacial.

---
*Documentado por Antigravity Agent, Senior Software Architect.*
