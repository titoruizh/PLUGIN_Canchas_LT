    def create_historical_tab(self):
        """Pestaña 5: Análisis Histórico"""
        tab = QtWidgets.QWidget()
        layout = QVBoxLayout()
        
        # Header principal
        header_layout = QHBoxLayout()
        icon_label = QLabel("📈")
        icon_label.setStyleSheet("font-size: 24px; margin-right: 10px;")
        title_label = QLabel("ANÁLISIS HISTÓRICO")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #5F4B8B;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc = QLabel("Realiza análisis de datos históricos para calcular fechas de intervención y crecimiento anual")
        desc.setStyleSheet("color: gray; margin-bottom: 15px; font-size: 12px;")
        layout.addWidget(desc)
        
        # Configuración del análisis histórico
        config_group = QtWidgets.QGroupBox("⚙️ Configuración de Análisis")
        config_layout = QVBoxLayout()
        
        # Periodo para crecimiento anual
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Periodo para crecimiento anual:"))
        self.dias_crecimiento = QtWidgets.QSpinBox()
        self.dias_crecimiento.setMinimum(30)
        self.dias_crecimiento.setMaximum(730)  # 2 años
        self.dias_crecimiento.setValue(365)    # 1 año por defecto
        self.dias_crecimiento.setSuffix(" días")
        period_layout.addWidget(self.dias_crecimiento)
        period_layout.addStretch()
        config_layout.addLayout(period_layout)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Columnas generadas
        columnas_group = QtWidgets.QGroupBox("📊 Columnas que se Generarán")
        columnas_layout = QVBoxLayout()
        
        columnas_info = QLabel("""1️⃣ "Ultima Intervencion": Fecha de la última intervención en el mismo Muro y Sector
    • Input: Muro, Sector y Fecha de cada registro
    • Busca en DATOS HISTORICOS intervenciones anteriores
    • Formato: YYYY-MM-DD (ej: 2025-05-15)

2️⃣ "Ultimo Crecimiento Anual": Suma de espesores en el periodo configurado
    • Input: Muro, Sector y Fecha de cada registro
    • Calcula suma de espesores en el periodo definido
    • Formato: Número decimal (ej: 24.464)""")
        columnas_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #f8f8f8; padding: 10px; border: 1px solid #5F4B8B; border-radius: 3px;")
        columnas_layout.addWidget(columnas_info)
        
        columnas_group.setLayout(columnas_layout)
        layout.addWidget(columnas_group)
        
        # Proceso detallado
        proceso_group = QtWidgets.QGroupBox("🔄 Proceso de Análisis")
        proceso_layout = QVBoxLayout()
        
        proceso_info = QLabel("""El proceso de análisis realiza dos cálculos principales:

1. ÚLTIMA INTERVENCIÓN:
   • Para cada registro de "Tabla Base Datos"
   • Busca en "DATOS HISTORICOS" registros con el mismo Muro y Sector
   • Identifica la fecha más reciente anterior a la fecha del registro
   • Guarda esta fecha como "Ultima Intervencion"

2. CRECIMIENTO ANUAL:
   • Para cada registro de "Tabla Base Datos"
   • Busca en "DATOS HISTORICOS" registros con el mismo Muro y Sector
   • Dentro del periodo configurado (365 días por defecto)
   • Suma todos los espesores encontrados
   • Guarda este valor como "Ultimo Crecimiento Anual"
""")
        proceso_info.setStyleSheet("font-family: 'Courier New'; color: #555; background-color: #f0f0ff; padding: 10px; border: 1px solid #5F4B8B; border-radius: 3px;")
        proceso_layout.addWidget(proceso_info)
        
        proceso_group.setLayout(proceso_layout)
        layout.addWidget(proceso_group)
        
        layout.addStretch()
        
        # Botón ejecutar
        self.btn_historical = QPushButton("📈 Ejecutar Análisis Histórico")
        self.btn_historical.setStyleSheet("""
            QPushButton {
                background-color: #5F4B8B; 
                color: white; 
                font-weight: bold; 
                padding: 12px; 
                border: none; 
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #483A6A;
            }
            QPushButton:pressed {
                background-color: #372A54;
            }
        """)
        self.btn_historical.clicked.connect(self.ejecutar_analisis_historico)
        layout.addWidget(self.btn_historical)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "5. Análisis Histórico")
        
    def ejecutar_analisis_historico(self):
        """Ejecutar proceso de análisis histórico"""
        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.log_message("📈 Iniciando análisis histórico...")
        self.log_message(f"⚙️ Periodo crecimiento anual: {self.dias_crecimiento.value()} días")
        
        try:
            # Importar el procesador
            from .core.historical_analysis import HistoricalAnalysisProcessor
            
            # Crear procesador
            processor = HistoricalAnalysisProcessor(
                progress_callback=self.update_progress,
                log_callback=self.log_message
            )
            
            # Ejecutar análisis histórico
            resultado = processor.ejecutar_analisis_historico_completo(
                dias_crecimiento_anual=self.dias_crecimiento.value()
            )
            
            if resultado['success']:
                self.log_message("🎉 ¡Análisis histórico completado exitosamente!")
                
                # Mostrar resumen de intervenciones
                resultado_interv = resultado.get('resultado_intervencion', {})
                self.log_message(f"📅 Análisis de intervenciones:")
                self.log_message(f"  • Registros con intervención: {resultado_interv.get('registros_actualizados', 0)}")
                self.log_message(f"  • Registros sin intervención previa: {resultado_interv.get('registros_sin_intervencion', 0)}")
                
                # Mostrar resumen de crecimiento
                resultado_crec = resultado.get('resultado_crecimiento', {})
                self.log_message(f"📏 Análisis de crecimiento anual:")
                self.log_message(f"  • Registros con crecimiento calculado: {resultado_crec.get('registros_actualizados', 0)}")
                self.log_message(f"  • Registros sin datos suficientes: {resultado_crec.get('registros_sin_datos', 0)}")
                
                self.log_message(f"🔄 Total de registros procesados: {resultado.get('registros_totales', 0)}")
                self.save_settings()
            else:
                self.log_message(f"❌ Error: {resultado['message']}")
                if 'details' in resultado:
                    self.log_message("📋 Ver detalles del error arriba")
                
        except ImportError as e:
            self.log_message(f"❌ Error de importación: {e}")
            self.log_message("ℹ️ Asegúrese de que el archivo historical_analysis.py exista en la carpeta core/")
        except Exception as e:
            self.log_message(f"❌ Error inesperado: {e}")
        finally:
            self.progress_bar.setVisible(False)