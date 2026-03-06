# -*- coding: utf-8 -*-
"""
Pipeline Dialog — Ventana Lineal Unificada
==========================================
Reemplaza la interfaz de 4 pestañas con una única ventana de configuración
que ejecuta los 6 pasos del pipeline en secuencia usando los mismos
procesadores core existentes. No hay lógica nueva: solo orquestación.

IMPORTANTE: El pipeline se ejecuta en el HILO PRINCIPAL (main thread).
QGIS y las librerías de procesamiento (processing.run, QgsProject, GDAL)
NO son thread-safe y provocan access violations si se llaman desde QThread.
Se usa QApplication.processEvents() en los callbacks para mantener la UI
responsiva durante la ejecución.

Layout:
  ┌──────────────────────┬─────────────────────────────┐
  │  PANEL CONFIGURACIÓN │  CONSOLA + BARRA PROGRESO   │
  └──────────────────────┴─────────────────────────────┘
"""

import os
import traceback

from qgis.PyQt.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel,
    QLineEdit, QPushButton, QCheckBox, QSpinBox, QDoubleSpinBox,
    QComboBox, QTextEdit, QProgressBar, QFileDialog, QSizePolicy,
    QScrollArea, QWidget, QFrame, QMessageBox, QApplication
)
from qgis.PyQt.QtCore import Qt, QSettings, QTime, QTimer
from qgis.PyQt.QtGui import QFont
from qgis.core import QgsProject

from .styles import Styles


# ---------------------------------------------------------------------------
# PipelineDialog — Ventana Principal
# ---------------------------------------------------------------------------
class PipelineDialog(QDialog):
    """
    Ventana unificada del pipeline lineal.
    Panel izquierdo: configuración.
    Panel derecho: consola de log + progreso.

    El pipeline se ejecuta sincrónicamente en el hilo principal para
    compatibilidad total con las APIs de QGIS (processing, GDAL, etc.).
    """

    SETTINGS_KEY = "canchas"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏗️  CANCHAS LAS TORTOLAS — Pipeline Topográfico")
        self.setMinimumSize(1100, 680)
        self.resize(1200, 720)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self._pipeline_running = False
        self._params = {}

        self.setStyleSheet(Styles.get_main_window_style() + """
            QDialog {
                background-color: #F5F6FA;
            }
        """)

        self._build_ui()
        self._load_settings()

    # ================================================================ LOG/PROGRESS (main thread)
    def _log(self, msg: str):
        """Agrega mensaje a la consola y procesa eventos para no congelar la UI."""
        ts = QTime.currentTime().toString("HH:mm:ss")
        self.console.append(f"[{ts}] {msg}")
        sb = self.console.verticalScrollBar()
        sb.setValue(sb.maximum())
        QApplication.processEvents()

    def _progress(self, value: int, msg: str = ""):
        """Actualiza barra de progreso y procesa eventos."""
        self.progress_bar.setValue(max(0, min(100, value)))
        if msg:
            self.lbl_progress_step.setText(msg)
        QApplication.processEvents()

    # ================================================================ BUILD UI
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Left: config panel (scrollable) ----
        left_frame = QFrame()
        left_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border-right: 1px solid #BDC3C7; }")
        left_frame.setFixedWidth(430)
        left_vbox = QVBoxLayout(left_frame)
        left_vbox.setContentsMargins(0, 0, 0, 0)
        left_vbox.setSpacing(0)

        # Header del panel izquierdo
        header = QLabel("  ⚙️  CONFIGURACIÓN DEL PIPELINE")
        header.setStyleSheet("""
            background-color: #2C3E50;
            color: white;
            font-weight: bold;
            font-size: 13px;
            padding: 12px 8px;
            letter-spacing: 1px;
        """)
        left_vbox.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(12, 12, 12, 12)
        scroll_layout.setSpacing(10)

        scroll_layout.addWidget(self._build_rutas_section())
        scroll_layout.addWidget(self._build_procesamiento_section())
        scroll_layout.addWidget(self._build_tabla_section())
        scroll_layout.addWidget(self._build_volumenes_section())
        scroll_layout.addWidget(self._build_reporte_section())
        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        left_vbox.addWidget(scroll, 1)

        # Bottom buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("QFrame { background: #F5F6FA; border-top: 1px solid #BDC3C7; }")
        btn_layout = QVBoxLayout(btn_frame)
        btn_layout.setContentsMargins(12, 10, 12, 10)
        btn_layout.setSpacing(6)

        self.btn_run = QPushButton("▶  EJECUTAR PIPELINE COMPLETO")
        self.btn_run.setStyleSheet(Styles.get_primary_button_style())
        self.btn_run.setFixedHeight(44)
        self.btn_run.clicked.connect(self._on_run_clicked)
        btn_layout.addWidget(self.btn_run)

        self.btn_compositor = QPushButton("🖨️  Abrir Compositor de Impresión")
        self.btn_compositor.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                font-weight: bold;
                padding: 9px;
                border: none;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #219A52; }
            QPushButton:disabled { background-color: #BDC3C7; color: #7F8C8D; }
        """)
        self.btn_compositor.setFixedHeight(38)
        self.btn_compositor.setEnabled(False)
        self.btn_compositor.clicked.connect(self._on_abrir_compositor)
        btn_layout.addWidget(self.btn_compositor)

        btn_close = QPushButton("✕  Cerrar Plugin")
        btn_close.setStyleSheet(Styles.get_danger_button_style())
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)

        left_vbox.addWidget(btn_frame)
        root.addWidget(left_frame)

        # ---- Right: console panel ----
        right_frame = QFrame()
        right_frame.setStyleSheet("QFrame { background-color: #ECF0F1; }")
        right_vbox = QVBoxLayout(right_frame)
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(0)

        console_header = QLabel("  📋  HISTORIAL DE OPERACIONES")
        console_header.setStyleSheet("""
            background-color: #2C3E50;
            color: #ECF0F1;
            font-weight: bold;
            font-size: 13px;
            padding: 12px 8px;
            letter-spacing: 1px;
        """)
        right_vbox.addWidget(console_header)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet(Styles.get_console_style() + """
            QTextEdit {
                border: none;
                border-radius: 0px;
            }
        """)
        right_vbox.addWidget(self.console, 1)

        # Progress bar at bottom of console
        progress_frame = QFrame()
        progress_frame.setStyleSheet("QFrame { background: #2C3E50; }")
        progress_frame.setFixedHeight(48)
        prog_layout = QVBoxLayout(progress_frame)
        prog_layout.setContentsMargins(12, 6, 12, 6)
        prog_layout.setSpacing(2)

        self.lbl_progress_step = QLabel("Listo para ejecutar")
        self.lbl_progress_step.setStyleSheet("color: #BDC3C7; font-size: 11px;")
        prog_layout.addWidget(self.lbl_progress_step)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #34495E;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #F18F01;
                border-radius: 4px;
            }
        """)
        prog_layout.addWidget(self.progress_bar)
        right_vbox.addWidget(progress_frame)

        root.addWidget(right_frame, 1)

    # ================================================== SECTION BUILDERS
    def _make_group(self, title: str) -> tuple:
        g = QGroupBox(title)
        g.setStyleSheet(Styles.get_card_style())
        layout = QVBoxLayout(g)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(6)
        return g, layout

    def _make_path_row(self, label: str, placeholder: str, is_file: bool = False, filter_str: str = "") -> tuple:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)

        lbl = QLabel(label)
        lbl.setFixedWidth(82)
        lbl.setStyleSheet("font-size: 11px; color: #2C3E50;")
        h.addWidget(lbl)

        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setStyleSheet(Styles.get_input_style())
        h.addWidget(edit, 1)

        btn = QPushButton("📂")
        btn.setFixedSize(30, 30)
        btn.setStyleSheet(Styles.get_tool_button_style())
        if is_file:
            btn.clicked.connect(lambda: self._browse_file(edit, filter_str))
        else:
            btn.clicked.connect(lambda: self._browse_folder(edit))
        h.addWidget(btn)

        return row, edit

    def _build_rutas_section(self) -> QGroupBox:
        g, lay = self._make_group("📁  Rutas Principales")
        row1, self.proc_root  = self._make_path_row("PROC ROOT", "Carpeta de procesamiento")
        row2, self.gpkg_path  = self._make_path_row("GPKG Orig.", "Archivo GeoPackage original", is_file=True, filter_str="GeoPackage (*.gpkg)")
        row3, self.csv_folder = self._make_path_row("CSV / ASC", "Carpeta de archivos CSV/ASC")
        row4, self.img_folder = self._make_path_row("Imágenes", "Carpeta de imágenes")
        for row in [row1, row2, row3, row4]:
            lay.addWidget(row)
        return g

    def _build_procesamiento_section(self) -> QGroupBox:
        g, lay = self._make_group("🗺️  Exportación de Capas (Paso 2)")
        self.chk_points   = QCheckBox("📍 Puntos (.csv)")
        self.chk_polygons = QCheckBox("⬡ Polígonos (.shp)")
        self.chk_tin      = QCheckBox("🔺 Triangulaciones (.tif)")
        for chk in [self.chk_points, self.chk_polygons, self.chk_tin]:
            chk.setStyleSheet("font-size: 12px; color: #2C3E50;")
            lay.addWidget(chk)
        self.chk_tin.setChecked(True)
        self.chk_polygons.setChecked(True)
        self.chk_points.setChecked(False)
        return g

    def _build_tabla_section(self) -> QGroupBox:
        g, lay = self._make_group("📋  Tabla Base Datos (Paso 3)")
        row = QHBoxLayout()
        lbl = QLabel("Protocolo topográfico inicial:")
        lbl.setStyleSheet("font-size: 12px;")
        row.addWidget(lbl)
        self.protocolo_inicio = QSpinBox()
        self.protocolo_inicio.setRange(1, 9999)
        self.protocolo_inicio.setValue(1)
        self.protocolo_inicio.setStyleSheet(Styles.get_spinbox_style())
        self.protocolo_inicio.setFixedWidth(80)
        row.addWidget(self.protocolo_inicio)
        row.addStretch()
        lay.addLayout(row)
        return g

    def _build_volumenes_section(self) -> QGroupBox:
        g, lay = self._make_group("📊  Volúmenes + Pantallazos (Paso 4)")

        def spin_row(label, widget):
            h = QHBoxLayout()
            l = QLabel(label)
            l.setStyleSheet("font-size: 12px;")
            l.setFixedWidth(168)
            h.addWidget(l)
            h.addWidget(widget)
            h.addStretch()
            lay.addLayout(h)

        self.num_random_points = QSpinBox()
        self.num_random_points.setRange(5, 100)
        self.num_random_points.setValue(20)
        self.num_random_points.setStyleSheet(Styles.get_spinbox_style())
        self.num_random_points.setFixedWidth(80)
        spin_row("Puntos aleatorios:", self.num_random_points)

        self.min_espesor = QLineEdit("0.01")
        self.min_espesor.setFixedWidth(80)
        self.min_espesor.setStyleSheet(Styles.get_input_style())
        spin_row("Espesor mínimo (m):", self.min_espesor)

        self.resample_algorithm = QComboBox()
        self.resample_algorithm.addItems(["bilinear", "nearest", "cubic", "cubicspline", "lanczos"])
        self.resample_algorithm.setStyleSheet(Styles.get_combobox_style())
        self.resample_algorithm.setFixedWidth(120)
        spin_row("Algoritmo remuestreo:", self.resample_algorithm)

        # Dimensiones en una sola fila
        dim_h = QHBoxLayout()
        dim_lbl = QLabel("Dimensiones (px):")
        dim_lbl.setStyleSheet("font-size: 12px;")
        dim_lbl.setFixedWidth(168)
        dim_h.addWidget(dim_lbl)
        self.screenshot_width = QSpinBox()
        self.screenshot_width.setRange(400, 2000)
        self.screenshot_width.setValue(800)
        self.screenshot_width.setStyleSheet(Styles.get_spinbox_style())
        self.screenshot_width.setFixedWidth(72)
        dim_h.addWidget(self.screenshot_width)
        dim_h.addWidget(QLabel("x"))
        self.screenshot_height = QSpinBox()
        self.screenshot_height.setRange(300, 1500)
        self.screenshot_height.setValue(500)
        self.screenshot_height.setStyleSheet(Styles.get_spinbox_style())
        self.screenshot_height.setFixedWidth(72)
        dim_h.addWidget(self.screenshot_height)
        dim_h.addStretch()
        lay.addLayout(dim_h)

        self.expansion_factor = QDoubleSpinBox()
        self.expansion_factor.setRange(1.0, 3.0)
        self.expansion_factor.setSingleStep(0.1)
        self.expansion_factor.setValue(1.3)
        self.expansion_factor.setStyleSheet(Styles.get_spinbox_style())
        self.expansion_factor.setFixedWidth(80)
        spin_row("Factor expansión:", self.expansion_factor)

        self.background_layer = QLineEdit("tif")
        self.background_layer.setFixedWidth(150)
        self.background_layer.setStyleSheet(Styles.get_input_style())
        spin_row("Nombre capa fondo:", self.background_layer)

        return g

    def _build_reporte_section(self) -> QGroupBox:
        g, lay = self._make_group("📈  Datos Reporte (Paso 6)")
        row = QHBoxLayout()
        lbl = QLabel("Días crecimiento anual:")
        lbl.setStyleSheet("font-size: 12px;")
        lbl.setFixedWidth(168)
        row.addWidget(lbl)
        self.dias_crecimiento = QSpinBox()
        self.dias_crecimiento.setRange(30, 730)
        self.dias_crecimiento.setValue(365)
        self.dias_crecimiento.setStyleSheet(Styles.get_spinbox_style())
        self.dias_crecimiento.setFixedWidth(80)
        row.addWidget(self.dias_crecimiento)
        row.addStretch()
        lay.addLayout(row)
        return g

    # ================================================== BROWSE HELPERS
    def _browse_folder(self, edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta", edit.text() or "")
        if path:
            edit.setText(path)
            self._save_settings()

    def _browse_file(self, edit: QLineEdit, filter_str: str):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", edit.text() or "", filter_str)
        if path:
            edit.setText(path)
            self._save_settings()

    # ================================================== SETTINGS
    def _load_settings(self):
        s = QSettings()
        s.beginGroup(self.SETTINGS_KEY)
        self.proc_root.setText(s.value("proc_root", ""))
        self.gpkg_path.setText(s.value("gpkg_path", ""))
        self.csv_folder.setText(s.value("csv_folder", ""))
        self.img_folder.setText(s.value("img_folder", ""))
        self.chk_points.setChecked(s.value("chk_points", False, type=bool))
        self.chk_polygons.setChecked(s.value("chk_polygons", True, type=bool))
        self.chk_tin.setChecked(s.value("chk_tin", True, type=bool))
        self.protocolo_inicio.setValue(int(s.value("protocolo_inicio", 1)))
        self.num_random_points.setValue(int(s.value("num_random_points", 20)))
        self.min_espesor.setText(s.value("min_espesor", "0.01"))
        idx = self.resample_algorithm.findText(s.value("resample_algorithm", "bilinear"))
        if idx >= 0:
            self.resample_algorithm.setCurrentIndex(idx)
        self.screenshot_width.setValue(int(s.value("screenshot_width", 800)))
        self.screenshot_height.setValue(int(s.value("screenshot_height", 500)))
        self.expansion_factor.setValue(float(s.value("expansion_factor", 1.3)))
        self.background_layer.setText(s.value("background_layer", "tif"))
        self.dias_crecimiento.setValue(int(s.value("dias_crecimiento", 365)))
        s.endGroup()

    def _save_settings(self):
        s = QSettings()
        s.beginGroup(self.SETTINGS_KEY)
        s.setValue("proc_root",          self.proc_root.text())
        s.setValue("gpkg_path",          self.gpkg_path.text())
        s.setValue("csv_folder",         self.csv_folder.text())
        s.setValue("img_folder",         self.img_folder.text())
        s.setValue("chk_points",         self.chk_points.isChecked())
        s.setValue("chk_polygons",       self.chk_polygons.isChecked())
        s.setValue("chk_tin",            self.chk_tin.isChecked())
        s.setValue("protocolo_inicio",   self.protocolo_inicio.value())
        s.setValue("num_random_points",  self.num_random_points.value())
        s.setValue("min_espesor",        self.min_espesor.text())
        s.setValue("resample_algorithm", self.resample_algorithm.currentText())
        s.setValue("screenshot_width",   self.screenshot_width.value())
        s.setValue("screenshot_height",  self.screenshot_height.value())
        s.setValue("expansion_factor",   self.expansion_factor.value())
        s.setValue("background_layer",   self.background_layer.text())
        s.setValue("dias_crecimiento",   self.dias_crecimiento.value())
        s.endGroup()

    # ================================================== VALIDATION
    def _validate_inputs(self) -> bool:
        errors = []
        proc_root  = self.proc_root.text().strip()
        gpkg_path  = self.gpkg_path.text().strip()
        csv_folder = self.csv_folder.text().strip()
        img_folder = self.img_folder.text().strip()

        if not proc_root:
            errors.append("• PROC ROOT: campo vacío")
        elif not os.path.isdir(proc_root):
            errors.append(f"• PROC ROOT: carpeta no encontrada → {proc_root}")
        if not gpkg_path:
            errors.append("• GPKG Original: campo vacío")
        elif not os.path.isfile(gpkg_path):
            errors.append(f"• GPKG Original: archivo no encontrado → {gpkg_path}")
        if not csv_folder:
            errors.append("• Carpeta CSV/ASC: campo vacío")
        elif not os.path.isdir(csv_folder):
            errors.append(f"• Carpeta CSV/ASC: no encontrada → {csv_folder}")
        if not img_folder:
            errors.append("• Carpeta Imágenes: campo vacío")
        elif not os.path.isdir(img_folder):
            errors.append(f"• Carpeta Imágenes: no encontrada → {img_folder}")
        try:
            float(self.min_espesor.text())
        except ValueError:
            errors.append("• Espesor mínimo: debe ser un número decimal (ej: 0.01)")

        if errors:
            QMessageBox.warning(self, "⚠️  Configuración incompleta",
                                "Corrija los siguientes campos antes de ejecutar:\n\n" + "\n".join(errors))
            return False
        return True

    # ================================================== EXECUTION ENTRY POINT
    def _on_run_clicked(self):
        if self._pipeline_running:
            return
        if not self._validate_inputs():
            return

        self._save_settings()

        # Capturar parámetros antes de arrancar
        self._params = {
            'proc_root':          self.proc_root.text().strip(),
            'gpkg_path':          self.gpkg_path.text().strip(),
            'csv_folder':         self.csv_folder.text().strip(),
            'img_folder':         self.img_folder.text().strip(),
            'chk_points':         self.chk_points.isChecked(),
            'chk_polygons':       self.chk_polygons.isChecked(),
            'chk_tin':            self.chk_tin.isChecked(),
            'protocolo_inicio':   self.protocolo_inicio.value(),
            'num_random_points':  self.num_random_points.value(),
            'min_espesor':        float(self.min_espesor.text()),
            'resample_algorithm': self.resample_algorithm.currentText(),
            'screenshot_width':   self.screenshot_width.value(),
            'screenshot_height':  self.screenshot_height.value(),
            'expansion_factor':   self.expansion_factor.value(),
            'background_layer':   self.background_layer.text().strip(),
            'dias_crecimiento':   self.dias_crecimiento.value(),
        }

        # Preparar UI
        self._pipeline_running = True
        self.btn_run.setEnabled(False)
        self.btn_run.setText("⏳  Ejecutando...")
        self.btn_compositor.setEnabled(False)
        self.console.clear()
        self.progress_bar.setValue(0)
        self.lbl_progress_step.setText("Iniciando...")
        QApplication.processEvents()

        ts = QTime.currentTime().toString("HH:mm:ss")
        self.console.append(f"[{ts}] 🚀 Iniciando pipeline completo...")
        self.console.append(f"[{ts}] 📁 PROC_ROOT: {self._params['proc_root']}")
        self.console.append("")

        # Diferir ejecución un ciclo de event-loop para que el cambio de UI
        # (botón deshabilitado, consola limpia) se pinte antes de arrancar.
        QTimer.singleShot(0, self._run_pipeline_sync)

    # ================================================== SYNCHRONOUS PIPELINE
    def _run_pipeline_sync(self):
        """
        Ejecuta los 6 pasos del pipeline SINCRÓNICAMENTE en el hilo principal.
        Esto es correcto para QGIS: processing.run() y QgsProject DEBEN correr
        en el main thread. QApplication.processEvents() en _log()/_progress()
        mantiene la UI responsiva.
        """
        p = self._params
        success = False
        try:
            # ----------------------------------------------------------
            # PASO 1/6 — Validación
            # ----------------------------------------------------------
            self._log("━━━ PASO 1/6 — Validación ━━━")
            self._progress(0, "Paso 1/6: Validación...")
            from ..core.validation import ValidationProcessor
            vp = ValidationProcessor(
                proc_root=p['proc_root'],
                orig_gpkg=p['gpkg_path'],
                dir_csv_orig=p['csv_folder'],
                dir_img_orig=p['img_folder'],
                progress_callback=self._progress,
                log_callback=self._log
            )
            res = vp.ejecutar_validacion_completa()
            if not res.get('success'):
                self._log(f"❌ Falló Paso 1: {res.get('message', 'Error desconocido')}")
                return
            self._log("✅ Paso 1 completado")

            # ----------------------------------------------------------
            # PASO 2/6 — Procesamiento Espacial
            # ----------------------------------------------------------
            self._log("━━━ PASO 2/6 — Procesamiento Espacial ━━━")
            self._progress(16, "Paso 2/6: Procesamiento Espacial...")
            from ..core.processing import ProcessingProcessor
            pp = ProcessingProcessor(
                proc_root=p['proc_root'],
                pixel_size=0.25,
                suavizado_tolerance=1.0,
                min_dist_vertices=2.0,
                progress_callback=self._progress,
                log_callback=self._log
            )
            export_options = {
                'points':   p['chk_points'],
                'polygons': p['chk_polygons'],
                'tin':      p['chk_tin'],
            }
            res = pp.ejecutar_procesamiento_completo(export_options)
            if not res.get('success'):
                self._log(f"❌ Falló Paso 2: {res.get('message', 'Error desconocido')}")
                return
            self._log("✅ Paso 2 completado")

            # ----------------------------------------------------------
            # PASO 3/6 — Tabla Base Datos
            # ----------------------------------------------------------
            self._log("━━━ PASO 3/6 — Tabla Base Datos ━━━")
            self._progress(32, "Paso 3/6: Creando Tabla Base...")
            from ..core.table_creation import TableCreationProcessor
            tp = TableCreationProcessor(
                proc_root=p['proc_root'],
                protocolo_topografico_inicio=p['protocolo_inicio'],
                debug_mode=False,
                progress_callback=self._progress,
                log_callback=self._log
            )
            res = tp.ejecutar_creacion_tabla_completa()
            if not res.get('success'):
                self._log(f"❌ Falló Paso 3: {res.get('message', 'Error desconocido')}")
                return
            self._log("✅ Paso 3 completado")

            # ----------------------------------------------------------
            # PASO 4/6 — Volúmenes + Pantallazos
            # ----------------------------------------------------------
            self._log("━━━ PASO 4/6 — Volúmenes + Pantallazos ━━━")
            self._progress(48, "Paso 4/6: Calculando volúmenes...")
            from ..core.volume_screenshot import VolumeScreenshotProcessor
            vsp = VolumeScreenshotProcessor(
                proc_root=p['proc_root'],
                num_random_points=p['num_random_points'],
                min_espesor=p['min_espesor'],
                resample_algorithm=p['resample_algorithm'],
                screenshot_width=p['screenshot_width'],
                screenshot_height=p['screenshot_height'],
                expansion_factor=p['expansion_factor'],
                background_layer=p['background_layer'],
                progress_callback=self._progress,
                log_callback=self._log
            )
            res = vsp.ejecutar_calculo_volumenes_con_pantallazos()
            if not res.get('success'):
                self._log(f"❌ Falló Paso 4: {res.get('message', 'Error desconocido')}")
                return
            self._log("✅ Paso 4 completado")

            # ----------------------------------------------------------
            # PASO 5/6 — Exportación XML
            # ----------------------------------------------------------
            self._log("━━━ PASO 5/6 — Exportación XML ━━━")
            self._progress(64, "Paso 5/6: Exportando a LandXML...")
            from ..core.xml_export import XMLExportProcessor
            xp = XMLExportProcessor(
                proc_root=p['proc_root'],
                progress_callback=self._progress,
                log_callback=self._log
            )
            res = xp.ejecutar_exportacion_xml_completa()
            if not res.get('success'):
                self._log(f"❌ Falló Paso 5: {res.get('message', 'Error desconocido')}")
                return
            self._log("✅ Paso 5 completado")

            # ----------------------------------------------------------
            # PASO 6/6 — Datos Reporte
            # ----------------------------------------------------------
            self._log("━━━ PASO 6/6 — Datos Reporte ━━━")
            self._progress(80, "Paso 6/6: Datos Reporte...")
            self._run_paso6(p)

            # ----------------------------------------------------------
            # GUARDAR PROYECTO .qgz
            # ----------------------------------------------------------
            self._log("💾 Guardando proyecto QGIS (.qgz)...")
            try:
                self._guardar_proyecto_qgz(p['proc_root'])
            except Exception as e:
                self._log(f"⚠️ Error al guardar proyecto: {e}")
                self._log(traceback.format_exc())

            # ----------------------------------------------------------
            # COMPLETADO
            # ----------------------------------------------------------
            self._progress(100, "¡Pipeline completado!")
            self._log("🎉 ══════════════════════════════════════")
            self._log("🎉  PIPELINE COMPLETO FINALIZADO CON ÉXITO")
            self._log("🎉 ══════════════════════════════════════")
            success = True

        except Exception as e:
            self._log(f"❌ Error crítico en pipeline: {e}")
            self._log(traceback.format_exc())

        finally:
            # Restaurar UI siempre, haya éxito o error
            self._pipeline_running = False
            self.btn_run.setEnabled(True)
            if success:
                self.btn_run.setText("✅  PIPELINE COMPLETADO — Ejecutar de nuevo")
                self.btn_compositor.setEnabled(True)
                self.lbl_progress_step.setText("✅ Pipeline completado exitosamente")
            else:
                self.btn_run.setText("▶  EJECUTAR PIPELINE COMPLETO")
                self.lbl_progress_step.setText("❌ Pipeline falló — revise el log")

    # ================================================== PASO 6 DETAIL
    def _run_paso6(self, p: dict):
        """
        Replica la lógica de reports_tab.ejecutar_fusion_y_analisis()
        sin modificar ese módulo. Llama a los mismos procesadores core.
        """
        proc_root = p['proc_root']
        dias = p['dias_crecimiento']

        from ..core.data_merge import DataMergeProcessor
        from ..core.historical_analysis import HistoricalAnalysisProcessor
        from ..core.bar_charts_simple import SimpleBarChartGenerator
        from ..core.time_series_charts import TimeSeriesChartGenerator
        from ..core.heatmap_screenshots import HeatmapScreenshotGenerator
        from ..core.espesor_classification import EspesorClassificationProcessor

        # 6.1 Fusión
        self._log("📋 6.1: Fusión de datos históricos...")
        dm = DataMergeProcessor(progress_callback=self._progress, log_callback=self._log)
        res = dm.fusionar_datos_historicos()
        if not res.get('success'):
            self._log(f"⚠️ Aviso en fusión: {res.get('message')} (continuando...)")
        else:
            self._log(f"✅ Fusión OK — registros: {res.get('total_registros', 0)}")

        # 6.2 Lab Excel (opcional)
        self._log("🧪 6.2: Buscando reporte de laboratorio...")
        try:
            from ..core.lab_report import LabReportLoader
            plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            report_folder = os.path.join(plugin_dir, "update N Informe")
            excel_path = None
            if os.path.exists(report_folder):
                for f in os.listdir(report_folder):
                    if f.endswith(".xlsx") and not f.startswith("~$"):
                        excel_path = os.path.join(report_folder, f)
                        break
            if excel_path:
                self._log(f"🧪 Detectado: {os.path.basename(excel_path)}")
                layer_base = next(
                    (lyr for lyr in QgsProject.instance().mapLayers().values()
                     if lyr.name() == "Tabla Base Datos"), None)
                if layer_base:
                    loader = LabReportLoader(log_callback=self._log)
                    ok, msg, _ = loader.load_excel_and_enrich(excel_path, layer_base)
                    self._log(f"{'✅' if ok else '⚠️'} {msg}")
                else:
                    self._log("⚠️ Capa 'Tabla Base Datos' no encontrada, saltando lab.")
            else:
                self._log("ℹ️ Sin reporte Excel en 'update N Informe', saltando.")
        except Exception as e:
            self._log(f"⚠️ Error en paso lab: {e}")

        # 6.3 Análisis histórico
        self._log(f"📈 6.3: Análisis histórico (días={dias})...")
        ha = HistoricalAnalysisProcessor(progress_callback=self._progress, log_callback=self._log)
        res = ha.ejecutar_analisis_historico_completo(dias_crecimiento_anual=dias)
        if not res.get('success'):
            self._log(f"⚠️ Aviso: {res.get('message')} (continuando...)")
        else:
            self._log("✅ Análisis histórico OK")

        # 6.4 Gráficos de barras
        self._log("📊 6.4: Generando gráficos de barras...")
        try:
            cg = SimpleBarChartGenerator(proc_root=proc_root, progress_callback=self._progress, log_callback=self._log)
            res = cg.generar_graficos_barras()
            self._log(f"{'✅' if res.get('success') else '⚠️'} Barras: {res.get('graficos_generados', 0)} gráficos")
        except Exception as e:
            self._log(f"⚠️ Error gráficos barras: {e}")

        # 6.5 Series temporales
        self._log("📈 6.5: Generando series temporales...")
        try:
            sg = TimeSeriesChartGenerator(proc_root=proc_root, progress_callback=self._progress, log_callback=self._log)
            res = sg.generar_graficos_series_temporales()
            self._log(f"{'✅' if res.get('success') else '⚠️'} Series: {res.get('graficos_generados', 0)} gráficos")
        except Exception as e:
            self._log(f"⚠️ Error series temporales: {e}")

        # 6.6 Heatmap
        self._log("📷 6.6: Generando pantallazos heatmap...")
        try:
            hg = HeatmapScreenshotGenerator(
                proc_root=proc_root,
                background_layer_name=p.get('background_layer', 'tif'),
                progress_callback=self._progress,
                log_callback=self._log
            )
            res = hg.generar_pantallazos_heatmap()
            self._log(f"{'✅' if res.get('success') else '⚠️'} Heatmap: {res.get('graficos_generados', 0)} imágenes")
        except Exception as e:
            self._log(f"⚠️ Error heatmap: {e}")

        # 6.7 Clasificación espesores
        self._log("📏 6.7: Clasificando espesores...")
        try:
            ec = EspesorClassificationProcessor(progress_callback=self._progress, log_callback=self._log)
            res = ec.ejecutar_clasificacion_espesor()
            self._log(f"{'✅' if res.get('success') else '⚠️'} Clasificación: {res.get('registros_procesados', 0)} registros")
        except Exception as e:
            self._log(f"⚠️ Error clasificación: {e}")

    # ================================================== GUARDAR PROYECTO
    def _guardar_proyecto_qgz(self, proc_root: str):
        """
        Guarda el proyecto QGIS como .qgz en proc_root al finalizar el pipeline.
        Pasos:
          1. Exporta memory layers (Tabla Base Datos, DATOS HISTORICOS) a GeoPackage en proc_root.
          2. Copia los DEMs finales (posiblemente en /Temp) a proc_root/MODELOS/.
          3. Redirige los layers DEM a los archivos permanentes.
          4. Guarda el proyecto como <nombre_carpeta>.qgz.
        """
        import shutil
        from qgis.core import (
            QgsProject, QgsVectorFileWriter, QgsVectorLayer,
            QgsRasterLayer, QgsExpressionContextUtils, QgsCoordinateTransformContext
        )

        project = QgsProject.instance()

        # ---- 1. Exportar memory layers a GeoPackage ----
        gpkg_path = os.path.join(proc_root, "Tabla Base Datos.gpkg")
        memory_layer_names = ["Tabla Base Datos", "DATOS HISTORICOS"]

        for lname in memory_layer_names:
            layers = project.mapLayersByName(lname)
            if not layers:
                self._log(f"ℹ️ Layer '{lname}' no encontrado, saltando.")
                continue
            layer = layers[0]

            # Solo exportar si es memory layer
            if layer.dataProvider().name() != "memory":
                self._log(f"ℹ️ '{lname}' ya tiene fuente permanente, saltando.")
                continue

            # Nombre de tabla dentro del GPKG (sin espacios para compatibilidad)
            table_name = lname.replace(" ", "_").replace("°", "N")
            layer_gpkg_path = f"{gpkg_path}|layername={table_name}"

            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "GPKG"
            options.layerName = table_name
            options.actionOnExistingFile = (
                QgsVectorFileWriter.CreateOrOverwriteLayer
                if os.path.exists(gpkg_path)
                else QgsVectorFileWriter.CreateOrOverwriteFile
            )

            write_result = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                gpkg_path,
                QgsCoordinateTransformContext(),
                options
            )
            # writeAsVectorFormatV3 devuelve (error, errMsg, newFilename, newLayer) en QGIS 3.x
            error = write_result[0]
            err_msg = write_result[1] if len(write_result) > 1 else ""

            if error == QgsVectorFileWriter.NoError:
                self._log(f"✅ '{lname}' exportado a GPKG: {table_name}")
                # Redirigir el layer del proyecto al GPKG
                # Primero removemos el layer memory y lo reemplazamos con el de archivo
                layer_id = layer.id()
                new_layer = QgsVectorLayer(layer_gpkg_path, lname, "ogr")
                if new_layer.isValid():
                    project.removeMapLayer(layer_id)
                    project.addMapLayer(new_layer, False)
                    # Agregar al root en la misma posición top-level
                    root = project.layerTreeRoot()
                    root.insertLayer(0, new_layer)
                    self._log(f"✅ Layer '{lname}' redirigido al GPKG permanente")
                else:
                    self._log(f"⚠️ No se pudo cargar '{lname}' desde GPKG tras exportar")
            else:
                self._log(f"⚠️ Error exportando '{lname}' a GPKG: {err_msg}")

        # ---- 2+3. Copiar DEMs finales y redirigir layers ----
        modelos_dir = os.path.join(proc_root, "MODELO FINAL")
        os.makedirs(modelos_dir, exist_ok=True)

        dem_names = ["DEM_MP", "DEM_ME", "DEM_MO"]
        proj_var_prefix = "dem_work_path_"



        for dem_name in dem_names:
            # Buscar el layer DEM en el proyecto
            dem_layers = project.mapLayersByName(dem_name)
            if not dem_layers:
                self._log(f"ℹ️ Layer '{dem_name}' no encontrado en proyecto, saltando.")
                continue
            dem_layer = dem_layers[0]

            # Obtener el path actual (puede ser temp) desde variable de proyecto
            var_key = proj_var_prefix + dem_name
            current_path = QgsExpressionContextUtils.projectScope(project).variable(var_key)

            if not current_path or not os.path.exists(str(current_path)):
                # Fallback: usar el dataSourceUri del layer
                current_path = dem_layer.dataProvider().dataSourceUri()
                self._log(f"ℹ️ Variable proyecto '{var_key}' no encontrada, usando dataSourceUri: {current_path}")

            current_path = str(current_path).split("|")[0]  # quitar params extra
            if not os.path.exists(current_path):
                self._log(f"⚠️ No se pudo encontrar el archivo DEM para '{dem_name}': {current_path}")
                continue

            dest_path = os.path.join(modelos_dir, f"{dem_name}_final.tif")
            try:
                shutil.copy2(current_path, dest_path)
                self._log(f"✅ '{dem_name}' copiado a: {dest_path}")
            except Exception as e:
                self._log(f"⚠️ No se pudo copiar '{dem_name}' ({e}). El proyecto apuntará al archivo temporal.")
                dest_path = current_path  # fallback: apuntar al temp

            # Redirigir el layer al archivo permanente
            try:
                dem_layer.setDataSource(dest_path, dem_name, "gdal")
                dem_layer.triggerRepaint()
                self._log(f"✅ Layer '{dem_name}' redirigido a ruta permanente")
            except Exception as e:
                self._log(f"⚠️ No se pudo redirigir layer '{dem_name}': {e}")

        # ---- 4. Guardar proyecto como .qgz ----
        qgz_path = os.path.join(proc_root, "PROCESAMIENTO.qgz")
        project.setFileName(qgz_path)
        ok = project.write()
        if ok:
            self._log(f"✅ Proyecto guardado: {qgz_path}")
        else:
            self._log(f"⚠️ Fallo al guardar proyecto en: {qgz_path}")

    # ================================================== COMPOSITOR
    def _on_abrir_compositor(self):
        """Delega al reports_tab.abrir_compositor_plantilla() sin duplicar lógica."""
        try:
            from .tabs.reports_tab import ReportsTab
            rt = ReportsTab()
            rt.log_signal.connect(lambda m: self._log(m))
            rt.abrir_compositor_plantilla(self.proc_root.text().strip())
        except Exception as e:
            self._log(f"❌ Error abriendo compositor: {e}")
            self._log(traceback.format_exc())

    # ================================================== CLOSE
    def closeEvent(self, event):
        if self._pipeline_running:
            reply = QMessageBox.question(
                self, "Pipeline en ejecución",
                "El pipeline está en ejecución. ¿Desea cerrar?\n"
                "(El proceso no se interrumpirá, QGIS puede quedar bloqueado momentáneamente)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
        self._save_settings()
        event.accept()
