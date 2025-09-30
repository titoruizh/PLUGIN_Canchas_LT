    def ejecutar_fusion_y_analisis(self):
        """Ejecutar proceso de fusión de datos y análisis histórico"""
        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Paso 1: Fusionar datos
        self.log_message("🔄 Iniciando proceso completo (fusión + análisis)...")
        
        try:
            # Importar el procesador
            from .core.data_merge import DataMergeProcessor
            
            # Crear procesador
            processor = DataMergeProcessor(
                progress_callback=self.update_progress,
                log_callback=self.log_message
            )
            
            # Ejecutar fusión de datos
            self.log_message("📋 Paso 1: Fusión de datos históricos...")
            resultado = processor.fusionar_datos_historicos()
            
            if resultado['success']:
                self.log_message("✅ Fusión de datos completada")
                self.log_message(f"📊 Registros copiados: {resultado.get('registros_copiados', 0)}")
                self.log_message(f"📊 Nuevos registros: {resultado.get('nuevos_ids', 0)}")
                self.log_message(f"📋 Total de registros en DATOS HISTORICOS: {resultado.get('total_registros', 0)}")
                
                # Paso 2: Análisis histórico
                self.log_message("📈 Paso 2: Iniciando análisis histórico...")
                self.log_message(f"⚙️ Periodo crecimiento anual: {self.dias_crecimiento.value()} días")
                
                try:
                    # Importar el procesador
                    from .core.historical_analysis import HistoricalAnalysisProcessor
                    
                    # Crear procesador
                    processor_hist = HistoricalAnalysisProcessor(
                        progress_callback=self.update_progress,
                        log_callback=self.log_message
                    )
                    
                    # Ejecutar análisis histórico
                    resultado_hist = processor_hist.ejecutar_analisis_historico_completo(
                        dias_crecimiento_anual=self.dias_crecimiento.value()
                    )
                    
                    if resultado_hist['success']:
                        self.log_message("🎉 ¡Análisis histórico completado exitosamente!")
                        
                        # Mostrar resumen de intervenciones
                        resultado_interv = resultado_hist.get('resultado_intervencion', {})
                        self.log_message(f"📅 Análisis de intervenciones:")
                        self.log_message(f"  • Registros con intervención: {resultado_interv.get('registros_actualizados', 0)}")
                        self.log_message(f"  • Registros sin intervención previa: {resultado_interv.get('registros_sin_intervencion', 0)}")
                        
                        # Mostrar resumen de crecimiento
                        resultado_crec = resultado_hist.get('resultado_crecimiento', {})
                        self.log_message(f"📏 Análisis de crecimiento anual:")
                        self.log_message(f"  • Registros con crecimiento calculado: {resultado_crec.get('registros_actualizados', 0)}")
                        self.log_message(f"  • Registros sin datos suficientes: {resultado_crec.get('registros_sin_datos', 0)}")
                        
                        self.log_message(f"🔄 Total de registros procesados: {resultado_hist.get('registros_totales', 0)}")
                        self.log_message("✅ PROCESO COMPLETO FINALIZADO CON ÉXITO")
                        self.save_settings()
                    else:
                        self.log_message(f"❌ Error en análisis histórico: {resultado_hist['message']}")
                        if 'details' in resultado_hist:
                            self.log_message("📋 Ver detalles del error arriba")
                        
                except ImportError as e:
                    self.log_message(f"❌ Error de importación: {e}")
                    self.log_message("ℹ️ Asegúrese de que el archivo historical_analysis.py exista en la carpeta core/")
                except Exception as e:
                    self.log_message(f"❌ Error inesperado en análisis histórico: {e}")
            else:
                self.log_message(f"❌ Error en fusión: {resultado['message']}")
                if 'details' in resultado:
                    self.log_message("📋 Ver detalles del error arriba")
                
        except ImportError as e:
            self.log_message(f"❌ Error de importación: {e}")
            self.log_message("ℹ️ Asegúrese de que el archivo data_merge.py exista en la carpeta core/")
        except Exception as e:
            self.log_message(f"❌ Error inesperado en fusión: {e}")
        finally:
            self.progress_bar.setVisible(False)