# 🏟️ Canchas Las Tortolas - Plugin QGIS Profesional


**Plugin especializado para procesamiento topográfico integral de canchas Las Tortolas desarrollado por Linkapsis**

> 🚀 **Automatiza completamente** el flujo de trabajo topográfico desde validación hasta reportes finales con exportación LandXML

---

## 📸 Reporte Topográfico

<img width="631" height="685" alt="SS reporte" src="https://github.com/user-attachments/assets/282819f9-b3c6-4cda-a45a-d5efd3a9264a" />


---

## ⭐ Características Principales

### 🔍 **1. Validación Espacial Avanzada**
- ✅ Verificación automática de formato CSV/ASC
- ✅ Validación de sistemas de coordenadas (EPSG:32719)
- ✅ Control de integridad espacial de archivos
- ✅ Detección de errores de formato topográfico

### 🔄 **2. Procesamiento Visual Inteligente**
- 🎯 Generación automática de grupos QGIS organizados por fecha
- 🔺 Creación de TIN (Triangulated Irregular Network)
- 📐 Generación de polígonos a partir de puntos topográficos
- 🎨 Simbología automática por categorías

### 📊 **3.1 Análisis de Datos Completo**
- 📋 Extracción automática de vértices extremos
- 📈 Generación de tabla base con metadata completa
- 🔢 Análisis estadístico de elevaciones
- 📍 Cálculo de coordenadas de referencia

### 📏 **3.2 Cálculo Volumétrico Profesional**
- ⚖️ Análisis incremental Cut/Fill con DEM base
- 📊 Cálculo de volúmenes con precisión topográfica
- 📐 Determinación de espesores mínimos y máximos
- 📈 Reportes estadísticos detallados

  ### 🗂️ **3.3 Exportación LandXML**
- 📤 Exportación completa a formato LandXML estándar
- 🔺 Superficies TIN con metadatos completos
- 📊 Compatibilidad con software CAD/topográfico
- ✅ Validación automática de exportación

### 📸 **4. Generación Semi-Automática de Reportes**
- 🖼️ Pantallazos automáticos con prefijo "P"
- 📄 Exportación a formato PDF profesional
- 🔍 Factor de zoom configurable (1.3x por defecto)
- 🎨 Layout automático optimizado



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

*[Placeholder para screenshot de tabla de datos]*

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

- **Imágenes JPG**: Prefijo "P" + ID levantamiento
- **Resolución**: 300 DPI para impresión profesional
- **Zoom**: Factor 1.3x automático para contexto óptimo
- **Georeferenciación**: Incluida en metadatos EXIF

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

---


### **🧠 Módulos Core Detallados**

#### **validation.py** 🔍
- Validación espacial de archivos CSV/ASC
- Verificación de sistemas de coordenadas
- Control de integridad de datos topográficos
- Detección de errores de formato

#### **processing.py** 🔄
- Generación de grupos QGIS organizados
- Creación de TIN (Triangulated Irregular Network)
- Procesamiento de polígonos a partir de puntos
- Simbología automática por categorías

#### **table_creation.py** 📋
- Extracción de coordenadas extremas
- Generación de metadata completa
- Cálculos de áreas 2D y 3D
- Análisis estadístico de elevaciones

#### **volume_screenshot.py** �📸
- Módulo unificado de cálculo volumétrico y generación de pantallazos
- Análisis incremental Cut/Fill con pegado automático de TINs sobre DEMs
- Generación simultánea de pantallazos regulares y de diferencias DEM
- Simbología automática para visualización de corte/relleno
- Validación y limpieza de archivos temporales

#### **xml_export.py** 🗂️
- Exportación formato LandXML estándar
- Superficies TIN con metadatos completos
- Compatibilidad software CAD/topográfico
- Validación automática de exportación

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
