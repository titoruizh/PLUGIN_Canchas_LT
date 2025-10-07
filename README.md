# 🏟️ Canchas Las Tortolas - Plugin QGIS Profesional


---

## 📸 Plugin


<img width="390" height="340" alt="SS Main" src="https://github.com/user-attachments/assets/c12f05c1-e482-41ee-bcfe-a2b085c7000a" />


<h2 align="center">📏 Análisis Comparativo de Precisión</h2>

<p align="center">
  <!-- Reemplaza el enlace por tu imagen -->
  <img src="https://github.com/user-attachments/assets/c99afda1-7dbd-4cfd-90ec-15410a1aa050" alt="Comparativa de espesores CAD vs Plugin" width="80%">
</p>

<table align="center">
  <tr>
    <th>Métrica</th>
    <th>Valor (m)</th>
  </tr>
  <tr><td>Promedio</td><td>0.0268</td></tr>
  <tr><td>Desviación estándar</td><td>0.0379</td></tr>
  <tr><td>Mínimo</td><td>0.0006</td></tr>
  <tr><td>Máximo</td><td>0.1723</td></tr>
  <tr><td>Mediana</td><td>0.0102</td></tr>
</table>

<pre>
Diferencia promedio entre métodos ≈ 2.7 cm
────────────────────────────────────────────
Valores estables y consistentes dentro de márgenes aceptables.
</pre>

<p align="center">
📊 <strong>Interpretación:</strong><br>
🔹 Diferencias menores a 3 cm en promedio entre el flujo CAD tradicional y el plugin<br>
🔹 Validación robusta que confirma consistencia volumétrica y precisión topográfica
</p>



---

## ⭐ Características Principales

### 🔍 1. Validación Espacial Avanzada

* ✅ Normalización automática de nombres a mayúsculas
* ✅ Verificación automática de formato CSV/ASC
* ✅ Validación de sistemas de coordenadas (EPSG:32719)
* ✅ Validación inteligente de nomenclatura con GPKG
* ✅ Control de integridad espacial de archivos
* ✅ Filtrado robusto de archivos RTCM / chequeo / INF
* ✅ Detección de errores de formato topográfico
* ✅ Detección y manejo de archivos con múltiples componentes en nombre

### 🔄 2. Procesamiento Visual Inteligente

* 🎯 Generación automática de grupos QGIS con actualización de fecha
* 🔺 Creación de TIN (Triangulated Irregular Network)
* 🔺 Creación de Poligonos
* 🔺 Creación de Puntos
* 📐 Generación de polígonos a partir de puntos topográficos
* 🎨 Simbología automática por categorías

### 📊 3.1 Análisis de Datos Completo

* 📋 Gestión avanzada de tablas con parseo flexible de nombres
* 📋 Extracción automática de vértices extremos
* 📈 Generación de tabla base con metadata completa
* 🔢 Análisis estadístico de elevaciones

### 📏 3.2 Cálculo Volumétrico Profesional + Pantallazos Movimiento de Tierra

* ⚖️ Análisis incremental Cut/Fill con DEM base
* 📊 Cálculo de volúmenes con precisión topográfica
* 📐 Determinación de espesores mínimos y máximos
* 📈 Reportes estadísticos detallados de volúmenes
* 📸 Generación de pantallazos con colores de corte y relleno

### 🗂️ 3.3 Exportación LandXML

* 📤 Exportación completa a formato LandXML con metadatos correctos
* 🔺 Superficies TIN con nomenclatura estandarizada
* 📊 Integración con flujos de trabajo profesionales CAD
* ✅ Compatibilidad total con sistemas de coordenadas **EPSG:32719**

### 📸 4. Generación Semi-Automática de Reportes

* 🖼️ Generacion de nuevas metricas de analisis de datos historicos 
* 📄 Reportes PDF con firma digital y logos corporativos integrados
* 📊 Gráficos de barras (G1) y series temporales (G2) historicos
* 🔥 Heatmaps historicos profesionales
* 📊 Análisis por sector involucrado



---

## 🔄 Flujo de Trabajo Completo

```mermaid
graph TD
    A[📁 Archivos CSV/ASC] --> B[🔍 Validación Espacial]
    B --> C[🔄 Procesamiento Visual]
    C --> D[📊 Análisis de Datos]
    D --> E[📏 Cálculo Volumétrico]
    E --> F[🗂️ Generación LandXML]
    F --> G[📊 Generación Datos reporte Historicos]
    
    B --> H[❌ Errores de Validación]
    C --> I[🎯 Grupos QGIS Organizados]
    D --> J[📋 Tabla Metadata]
    E --> K[⚖️ Análisis Cut/Fill y 📸Planos Mov. Tierra]
    F --> L[🗂️ Archivo .XML]
    G --> M[📋 Uso de plantilla .qpt para Reportes]
```


## 📈 Resultados Generados

### **🎯 Grupos QGIS Organizados**

*[Placeholder para screenshot de grupos generados en QGIS]*

```
Procesamiento_YYYY-MM-DD/
├── 📍 Puntos/
│   ├── Levantamiento_001_puntos
│   ├── Levantamiento_002_puntos
│   └── ...
├── 📐 Polígonos/
│   ├── Levantamiento_001_poligono
│   ├── Levantamiento_002_poligono
│   └── ...
└── 🔺 Triangulaciones/
    ├── Levantamiento_001_TIN
    ├── Levantamiento_002_TIN
    └── ...
```

### **📋 Tabla Base de Datos con Metadata**

<img width="607" height="424" alt="SS tabla" src="https://github.com/user-attachments/assets/5c1d0f54-657d-49b9-b98c-b58b8352277c" />


| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_levantamiento` | Integer | ID único del levantamiento |
| `fecha_procesamiento` | Date | Fecha de procesamiento |
| `norte_min/max` | Double | Coordenadas extremas Norte |
| `este_min/max` | Double | Coordenadas extremas Este |
| `cota_min/max` | Double | Elevaciones extremas |
| `area_2d` | Double | Área proyectada (m²) |
| `area_3d` | Double | Área superficie real (m²) |
| `num_puntos` | Integer | Cantidad de puntos |
| `archivo_origen` | Text | Nombre archivo CSV original |

### **⚖️ Análisis Volumétrico Cut/Fill**

```
Levantamiento: 001
================
Volumen Cut:    +1,234.56 m³
Volumen Fill:   -567.89 m³
Volumen Neto:   +666.67 m³
Espesor Mín:    -2.45 m
Espesor Máx:    +3.78 m
Área Análisis:  5,678.90 m²
```

### **📸 Reportes Visuales Automáticos**

<!-- Imagen grande arriba -->

<p align="center">
  <img src="https://github.com/user-attachments/assets/2237aba3-3d8b-4781-8a73-3799b37612f8" alt="P250925_MP_S5_TALUDSUPERIOR" width="100%">
</p>

<!-- Tres imágenes pequeñas abajo, alineadas en fila -->

<p align="center">
  <img src="https://github.com/user-attachments/assets/27dc6742-722d-4af4-8e0a-b2340424c3f2" alt="G1250901_MP_S5_PLAT1" width="32%">
  <img src="https://github.com/user-attachments/assets/77e61583-cadf-4627-b3cf-6a97da7e2f18" alt="G2250901_MP_S7_PLAT1" width="32%">
  <img src="https://github.com/user-attachments/assets/c30e3d3d-b0dd-4c71-8ba9-935b6d760ba6" alt="PH250904_MP_S6_talud" width="32%">
</p>



### **🗂️ Exportación LandXML Profesional**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2">
  <Project name="Canchas Las Tortolas">
    <Surface name="Levantamiento_001">
      <SourceData>
        <Breaklines>
          <Breakline>
            <PntList3D>345678.25 7543210.50 1245.67 ...</PntList3D>
          </Breakline>
        </Breaklines>
      </SourceData>
      <Definition surfType="TIN">
        <Pnts>
          <P id="1">345678.25 7543210.50 1245.67</P>
          ...
        </Pnts>
        <Faces>
          <F>1 2 3</F>
          ...
        </Faces>
      </Definition>
    </Surface>
  </Project>
</LandXML>
```
### **🗂️ Reporte Final**


<img width="631" height="685" alt="SS reporte" src="https://github.com/user-attachments/assets/8cdd6986-8eb5-4ac1-b6fb-cb7f42d963ab" />


---

## 🤝 Soporte

### **📧 Información de Contacto Linkapsis**

**🏢 Empresa:** Linkapsis  
**👨‍💻 Desarrollador:** Tito Ruiz - Analista de Desarrollo y Procesos  
**📧 Email:** [truizh@linkapsis.com](mailto:truizh@linkapsis.com)  
**🌐 Website:** [www.linkapsis.com](https://www.linkapsis.com)  
**📅 Fecha Desarrollo:** Agosto 2025  



<div align="center">

**🏟️ Canchas Las Tortolas Plugin QGIS**  
*Desarrollado con ❤️ por [Linkapsis](https://www.linkapsis.com)*

[![GitHub Stars](https://img.shields.io/github/stars/titoruizh/PLUGIN_Canchas_LT?style=social)](https://github.com/titoruizh/PLUGIN_Canchas_LT/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/titoruizh/PLUGIN_Canchas_LT?style=social)](https://github.com/titoruizh/PLUGIN_Canchas_LT/network/members)

</div>
