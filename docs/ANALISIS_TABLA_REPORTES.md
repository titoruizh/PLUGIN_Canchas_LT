# Análisis: Tabla Base Datos y Generación de Reportes

## 📋 Vista General

Este documento analiza dos funcionalidades críticas del plugin:
1. **Creación de Tabla Base Datos** con extracción de vértices extremos P1-P4
2. **Generación de Datos Reporte** con imágenes auxiliares

---

## 🔷 PARTE 1: Tabla Base Datos - Vértices Extremos P1-P4

### Ubicación
- **Archivo Principal**: `core/table_creation.py`
- **Función Clave**: `extraer_vertices_extremos()` (líneas 273-361)
- **Botón UI**: "📋 Crear Tabla Base Datos" en pestaña "3. Análisis → 3.1 Tabla"

### Funcionamiento de los Vértices Extremos

#### 1. **Extracción de Vértices del Polígono**

```python
# Obtener geometría del polígono
poly_geom = next(poligono_layer.getFeatures()).geometry()

# Convertir a lista de vértices
if poly_geom.isMultipart():
    polygon = poly_geom.asMultiPolygon()[0][0]
else:
    polygon = poly_geom.asPolygon()[0]

vertices = [QgsPointXY(pt) for pt in polygon]
```

#### 2. **Identificación de Extremos**

Los 4 vértices extremos se definen como:

```python
left = min(vertices, key=lambda p: p.x())    # P1: Más al OESTE (menor X)
right = max(vertices, key=lambda p: p.x())   # P2: Más al ESTE (mayor X)
top = max(vertices, key=lambda p: p.y())     # P3: Más al NORTE (mayor Y)
bottom = min(vertices, key=lambda p: p.y())  # P4: Más al SUR (menor Y)

extremos = {
    "P1": left,    # Punto más a la izquierda
    "P2": right,   # Punto más a la derecha
    "P3": top,     # Punto más arriba
    "P4": bottom   # Punto más abajo
}
```

**Visualización:**
```
        P3 (Top/Norte)
           ↑
           |
P1 ←──────●──────→ P2
(Oeste)   |      (Este)
          ↓
        P4 (Bottom/Sur)
```

#### 3. **Búsqueda de Punto Más Cercano en Capa de Puntos**

Para cada vértice extremo del polígono, se busca el punto más cercano en la capa de puntos CSV:

```python
for p, extremo in extremos.items():
    nearest = self.punto_mas_cercano(layer_pts, extremo)
    if nearest:
        geom = nearest.geometry().asPoint()
        este = round(geom.x(), 3)
        norte = round(geom.y(), 3)
        cota = round(nearest[campo_cota], 3)
        datos_extremos[p] = (este, norte, cota)
```

La función `punto_mas_cercano()` calcula la distancia euclidiana:

```python
def punto_mas_cercano(self, layer_pts, extremo):
    min_dist = float('inf')
    nearest_feature = None
    
    for feat in layer_pts.getFeatures():
        pt_geom = feat.geometry().asPoint()
        dist = extremo.distance(pt_geom)
        if dist < min_dist:
            min_dist = dist
            nearest_feature = feat
    
    return nearest_feature
```

#### 4. **Campos Creados en la Tabla**

Para cada vértice P1, P2, P3, P4 se crean 3 campos:

```python
# En crear_tabla_base_datos():
fields.append(QgsField("P1_ESTE", QVariant.Double))
fields.append(QgsField("P1_NORTE", QVariant.Double))
fields.append(QgsField("P1_COTA", QVariant.Double))

fields.append(QgsField("P2_ESTE", QVariant.Double))
fields.append(QgsField("P2_NORTE", QVariant.Double))
fields.append(QgsField("P2_COTA", QVariant.Double))

fields.append(QgsField("P3_ESTE", QVariant.Double))
fields.append(QgsField("P3_NORTE", QVariant.Double))
fields.append(QgsField("P3_COTA", QVariant.Double))

fields.append(QgsField("P4_ESTE", QVariant.Double))
fields.append(QgsField("P4_NORTE", QVariant.Double))
fields.append(QgsField("P4_COTA", QVariant.Double))
```

#### 5. **Población de Datos**

```python
for p, (este, norte, cota) in datos_extremos.items():
    f.setAttribute(f"{p}_ESTE", este)
    f.setAttribute(f"{p}_NORTE", norte)
    f.setAttribute(f"{p}_COTA", cota)
```

**Ejemplo de datos resultantes:**
| Protocolo | P1_ESTE | P1_NORTE | P1_COTA | P2_ESTE | P2_NORTE | P2_COTA | P3_ESTE | P3_NORTE | P3_COTA | P4_ESTE | P4_NORTE | P4_COTA |
|-----------|---------|----------|---------|---------|----------|---------|---------|----------|---------|---------|----------|---------|
| 1 | 345678.123 | 6234567.456 | 234.789 | 345698.234 | 6234577.567 | 235.123 | 345688.345 | 6234587.678 | 235.456 | 345683.456 | 6234557.789 | 234.567 |

---

## 🔷 PARTE 2: Generación de Datos Reporte - Carpeta Aux

### Ubicación
- **Botón UI**: "📊 Generar Datos Reporte" en pestaña "4. Datos Reporte"
- **Función**: `abrir_compositor_plantilla()` en `canchas_dialog.py` (línea 1734)

### Estructura de Carpeta Aux Reporte

```
PROC_ROOT/
└── Aux Reporte/
    ├── Grafico Barras/      ← Gráficos de barras (G1)
    ├── Grafico Series/       ← Gráficos de series temporales (G2)
    └── Pantallazos Heatmap/  ← Mapas de calor (PH)
```

### Generadores de Imágenes

#### 1. **Gráficos de Barras** (`bar_charts_simple.py`)

**Función:** `generar_graficos_barras()`

**Proceso:**
1. Lee cada registro de "Tabla Base Datos"
2. Consulta datos históricos filtrados por Muro + Sector + Relleno
3. Genera gráfico de barras con matplotlib

**Nomenclatura:**
```python
# Formato: G1{protocolo}_{fecha}_{muro}_{sector}_{relleno}.png
# Ejemplo: G1250820_MP_S1_Arenafina.png
nombre_archivo = f"G1{protocolo}_{fecha_procesada}_{muro_procesado}_{sector_procesado}_{relleno_procesado}.png"
```

**Carpeta destino:**
```python
carpeta_aux = os.path.join(self.proc_root, "Aux Reporte")
carpeta_graficos_barras = os.path.join(carpeta_aux, "Grafico Barras")
```

**Campo actualizado en tabla:**
```python
# Se actualiza el campo "G1" con el nombre del archivo
f.setAttribute("G1", nombre_archivo)
```

#### 2. **Gráficos de Series Temporales** (`time_series_charts.py`)

**Función:** `generar_graficos_series()`

**Proceso:**
1. Lee cada registro de "Tabla Base Datos"
2. Consulta tendencias temporales de espesores por Muro + Sector + Relleno
3. Genera gráfico de líneas con matplotlib

**Nomenclatura:**
```python
# Formato: G2{protocolo}_{fecha}_{muro}_{sector}_{relleno}.png
# Ejemplo: G2250820_MP_S1_Arenafina.png
nombre_archivo = f"G2{protocolo}_{fecha_procesada}_{muro_procesado}_{sector_procesado}_{relleno_procesado}.png"
```

**Carpeta destino:**
```python
carpeta_graficos_series = os.path.join(carpeta_aux, "Grafico Series")
```

**Campo actualizado en tabla:**
```python
f.setAttribute("G2", nombre_archivo)
```

#### 3. **Pantallazos Heatmap** (`heatmap_screenshots.py`)

**Función:** `generar_pantallazos_heatmap()`

**Proceso:**
1. Lee cada registro de "Tabla Base Datos"
2. Extrae centroides de históricos usando P1-P4:
   ```python
   def calculate_centroid(self, p1_este, p1_norte, p2_este, p2_norte, 
                          p3_este, p3_norte, p4_este, p4_norte):
       centroid_x = (p1_este + p2_este + p3_este + p4_este) / 4.0
       centroid_y = (p1_norte + p2_norte + p3_norte + p4_norte) / 4.0
       return centroid_x, centroid_y
   ```
3. Crea heatmap con densidad de puntos usando gaussian_filter
4. Superpone heatmap sobre imagen de fondo (TIF)
5. Genera imagen PNG

**Nomenclatura:**
```python
# Formato: PH{protocolo}_{fecha}_{muro}_{sector}_{relleno}.png
# Ejemplo: PH250820_MP_S1_Arenafina.png
nombre_archivo = f"PH{protocolo}_{fecha_procesada}_{muro_procesado}_{sector_procesado}_{relleno_procesado}.png"
```

**Carpeta destino:**
```python
carpeta_pantallazos = os.path.join(carpeta_aux, "Pantallazos Heatmap")
```

**Campo actualizado en tabla:**
```python
f.setAttribute("PH", nombre_archivo)
```

**Uso de vértices P1-P4 en Heatmap:**
```python
# Se extraen de DATOS HISTORICOS para calcular centroides
for feature in datos_historicos_layer.getFeatures():
    p1_este = feature["P1_ESTE"]
    p1_norte = feature["P1_NORTE"]
    p2_este = feature["P2_ESTE"]
    p2_norte = feature["P2_NORTE"]
    p3_este = feature["P3_ESTE"]
    p3_norte = feature["P3_NORTE"]
    p4_este = feature["P4_ESTE"]
    p4_norte = feature["P4_NORTE"]
    
    centroid_x, centroid_y = self.calculate_centroid(
        p1_este, p1_norte, p2_este, p2_norte,
        p3_este, p3_norte, p4_este, p4_norte
    )
    
    centroids.append([centroid_x, centroid_y])
```

---

## 📊 Integración con Plantilla de Reporte

### Archivo: `resources/templates/Plantilla_Protocolos_LT.qpt`

La plantilla utiliza **expresiones QGIS** para cargar dinámicamente las imágenes:

#### **Gráfico de Barras (G1):**
```xml
<expression>
'E:/CANCHAS_QFIELD/.../Aux Reporte/Grafico Barras/' || "G1"
</expression>
```

#### **Pantallazos Heatmap (PH):**
```xml
<expression>
'E:/CANCHAS_QFIELD/.../Aux Reporte/Pantallazos Heatmap/' || "PH"
</expression>
```

#### **Gráfico de Series (G2):**
```xml
<expression>
'E:/CANCHAS_QFIELD/.../Aux Reporte/Grafico Series/' || "G2"
</expression>
```

**El plugin reemplaza dinámicamente las rutas** con PROC_ROOT cuando abre el compositor:

```python
# En abrir_compositor_plantilla()
proc_root_normalized = proc_root_text.replace('\\', '/')

patrones_rutas = [
    r"'[A-Z]:/[^']*?/Aux Reporte/Grafico Barras/'",
    r"'[A-Z]:/[^']*?/Aux Reporte/Grafico Series/'",
    r"'[A-Z]:/[^']*?/Aux Reporte/Pantallazos Heatmap/'"
]

reemplazos_rutas = [
    f"'{proc_root_normalized}/Aux Reporte/Grafico Barras/'",
    f"'{proc_root_normalized}/Aux Reporte/Grafico Series/'",
    f"'{proc_root_normalized}/Aux Reporte/Pantallazos Heatmap/'"
]
```

---

## 🎯 Resumen de Flujo Completo

### **Flujo de Trabajo:**

1. **Pestaña 3.1 - Crear Tabla Base Datos**
   - Extrae vértices extremos P1-P4 de polígonos
   - Busca puntos más cercanos en capa CSV
   - Guarda coordenadas (ESTE, NORTE, COTA) × 4 vértices
   - Crea campos: P1_ESTE, P1_NORTE, P1_COTA, ..., P4_COTA

2. **Pestaña 4 - Generar Datos Reporte**
   - **Gráficos de Barras**: Analiza históricos filtrados → `G1*.png`
   - **Gráficos de Series**: Analiza tendencias temporales → `G2*.png`
   - **Heatmaps**: Usa P1-P4 para calcular centroides → `PH*.png`
   - Actualiza campos G1, G2, PH en la tabla

3. **Compositor de Impresión**
   - Abre plantilla QPT
   - Reemplaza rutas con PROC_ROOT
   - Las expresiones cargan imágenes dinámicamente: `ruta + campo`
   - Genera reportes PDF Atlas por cada registro

---

## 📝 Campos de la Tabla Base Datos

### Campos Generados:

| Grupo | Campos |
|-------|--------|
| **Vértices P1** | P1_ESTE, P1_NORTE, P1_COTA |
| **Vértices P2** | P2_ESTE, P2_NORTE, P2_COTA |
| **Vértices P3** | P3_ESTE, P3_NORTE, P3_COTA |
| **Vértices P4** | P4_ESTE, P4_NORTE, P4_COTA |
| **Imágenes Aux** | G1 (gráfico barras), G2 (series), PH (heatmap) |
| **Imágenes Básicas** | Foto (F*.jpg), Plano (P*.jpg) |
| **Metadata** | Protocolo, Muro, Fecha, Sector Relleno |
| **Geometría** | Area, Ancho, Largo |
| **Volúmenes** | Cut, Fill, Espesor min/max |

---

## 💡 Puntos Clave para Implementaciones Futuras

1. **Vértices P1-P4 son calculados geométricamente** desde el polígono boundary box
2. **NOT** son los 4 primeros puntos del CSV, sino los extremos espaciales
3. **Heatmap usa centroides** calculados promediando P1-P4 de datos históricos
4. **Todas las imágenes se nombran con formato consistente**: `{prefijo}{protocolo}_{fecha}_{muro}_{sector}_{relleno}.png`
5. **La plantilla QPT usa expresiones dinámicas** que concatenan ruta + campo de la tabla
6. **El plugin modifica la plantilla en tiempo real** reemplazando rutas hardcoded con PROC_ROOT
