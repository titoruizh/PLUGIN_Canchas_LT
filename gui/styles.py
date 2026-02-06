# -*- coding: utf-8 -*-
"""
Las Tortolas UI Design System
---------------------------------------------------------------------
Centralized storage for QSS (Qt Style Sheets) and Design Tokens.
Implements the "Native Plus" aesthetic.
"""

class Styles:
    """QSS Generator Methods"""

    class Theme:
        """Palette Definition (Minería Moderna)"""
        
        # Primary Brand Colors (Bronce/Cobre & Azul Técnico)
        PRIMARY = "#F18F01"         # Naranja (Cobre/Acción)
        PRIMARY_HOVER = "#D67D00"   # Naranja oscuro
        PRIMARY_TEXT = "#FFFFFF"
        
        SECONDARY = "#2C3E50"       # Azul Acero Oscuro (Estructura/Sidebar)
        ACCENT = "#3498DB"          # Azul Clásico (Links/Info)
        
        # Status Colors
        SUCCESS = "#27AE60"         # Verde Esmeralda
        DANGER = "#E74c3C"          # Rojo Alizarin
        WARNING = "#F39C12"         # Amarillo Sol
        
        # Neutrals (Backgrounds & Surfaces)
        BG_APP = "#F5F6FA"          # Blanco Hueso (Fondo general)
        BG_WHITE = "#FFFFFF"        # Blanco Puro (Cards)
        BG_SIDEBAR = "#ECF0F1"      # Gris Perla (Sidebar)
        
        # Text
        TEXT_MAIN = "#2C3E50"       # Gris Oscuro (Casi negro)
        TEXT_MUTED = "#7F8C8D"      # Gris Medio
        
        # Borders
        BORDER_LIGHT = "#BDC3C7"    # Gris Claro
        
        # Typos
        FONT_FAMILY = "Segoe UI, Roboto, Helvetica, Arial, sans-serif"

    @staticmethod
    def get_main_window_style():
        """Applies to the main QDialog"""
        return f"""
            QDialog {{
                background-color: {Styles.Theme.BG_APP};
                font-family: {Styles.Theme.FONT_FAMILY};
                color: {Styles.Theme.TEXT_MAIN};
            }}
        """

    @staticmethod
    def get_sidebar_style():
        """Style for the Right Console Panel"""
        return f"""
            QFrame {{
                background-color: {Styles.Theme.BG_SIDEBAR};
                border-left: 1px solid {Styles.Theme.BORDER_LIGHT};
            }}
            QLabel {{
                color: {Styles.Theme.TEXT_MUTED};
                font-weight: bold;
                font-size: 11px;
                text-transform: uppercase;
                margin-top: 5px;
            }}
        """

    @staticmethod
    def get_console_style():
        """Style for the Log TextEdit"""
        return f"""
            QTextEdit {{
                background-color: {Styles.Theme.BG_WHITE};
                border: 1px solid {Styles.Theme.BORDER_LIGHT};
                border-radius: 4px;
                padding: 5px;
                color: {Styles.Theme.TEXT_MAIN};
                font-family: Consolas, 'Courier New', monospace;
                font-size: 11px;
            }}
        """

    @staticmethod
    def get_danger_button_style():
        """Style for Close/Cancel buttons"""
        return f"""
            QPushButton {{
                background-color: {Styles.Theme.BG_WHITE};
                border: 1px solid {Styles.Theme.DANGER};
                color: {Styles.Theme.DANGER};
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Styles.Theme.DANGER};
                color: white;
            }}
            QPushButton:pressed {{
                background-color: #C0392B;
                color: white;
            }}
        """

    @staticmethod
    def get_tab_widget_style():
        """Modern Tabs Style"""
        return f"""
            QTabWidget::pane {{
                border: 1px solid {Styles.Theme.BORDER_LIGHT};
                background: {Styles.Theme.BG_WHITE};
                border-radius: 4px;
                /* Eliminamos el borde superior para fusionarlo con los tabs */
                top: -1px; 
            }}
            
            QTabBar::tab {{
                background: #E0E0E0;
                color: {Styles.Theme.TEXT_MUTED};
                border: 1px solid {Styles.Theme.BORDER_LIGHT};
                border-bottom-color: {Styles.Theme.BORDER_LIGHT}; /* Borde inferior visible en inactivos */
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 120px;
                padding: 8px 12px;
                margin-right: 2px;
                font-weight: 500;
            }}

            QTabBar::tab:selected, QTabBar::tab:hover {{
                background: {Styles.Theme.BG_WHITE};
                color: {Styles.Theme.PRIMARY};
                border-bottom-color: {Styles.Theme.BG_WHITE}; /* Fusión visual */
                font-weight: bold;
            }}
            
            QTabBar::tab:selected {{
                border-top: 2px solid {Styles.Theme.PRIMARY}; /* Indicador de selección */
            }}
        """

    @staticmethod
    def get_card_style():
        """Common container style for internal tabs"""
        return f"""
            QGroupBox {{
                background-color: {Styles.Theme.BG_WHITE};
                border: 1px solid {Styles.Theme.BORDER_LIGHT};
                border-radius: 6px;
                margin-top: 20px; /* Space for title */
                font-weight: bold;
                color: {Styles.Theme.SECONDARY};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                left: 10px;
                color: {Styles.Theme.PRIMARY};
            }}
        """

    @staticmethod
    def get_input_style():
        """Modern Text Input"""
        return f"""
            QLineEdit {{
                padding: 8px;
                border: 1px solid {Styles.Theme.BORDER_LIGHT};
                border-radius: 4px;
                background-color: {Styles.Theme.BG_APP};
                font-size: 13px;
                color: {Styles.Theme.TEXT_MAIN};
            }}
            QLineEdit:focus {{
                border: 2px solid {Styles.Theme.PRIMARY};
                background-color: {Styles.Theme.BG_WHITE};
            }}
            QLineEdit:read-only {{
                background-color: #EEE;
                color: {Styles.Theme.TEXT_MUTED};
            }}
        """

    @staticmethod
    def get_tool_button_style():
        """Small buttons (for browsing files)"""
        return f"""
            QPushButton {{
                background-color: {Styles.Theme.SECONDARY}; 
                color: white; 
                border: none; 
                border-radius: 4px; 
                padding: 6px 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #34495E;
            }}
            QPushButton:pressed {{
                background-color: #2C3E50;
                padding-top: 7px;
            }}
        """

    @staticmethod
    def get_primary_button_style():
        """Hero/Main Action Button"""
        return f"""
            QPushButton {{
                background-color: {Styles.Theme.PRIMARY}; 
                color: white; 
                font-weight: bold; 
                padding: 12px 24px; 
                border: none; 
                border-radius: 6px;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: {Styles.Theme.PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #BF6F00;
                padding-top: 13px; /* Efecto click 3D */
            }}
            QPushButton:disabled {{
                background-color: #BDC3C7;
                color: #7F8C8D;
            }}
        """

    @staticmethod
    def get_spinbox_style():
        """Style for QSpinBox and QDoubleSpinBox"""
        return f"""
            QSpinBox, QDoubleSpinBox {{
                padding: 6px;
                border: 1px solid {Styles.Theme.BORDER_LIGHT};
                border-radius: 4px;
                background-color: {Styles.Theme.BG_APP};
                font-size: 13px;
                color: {Styles.Theme.TEXT_MAIN};
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {Styles.Theme.PRIMARY};
                background-color: {Styles.Theme.BG_WHITE};
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 16px;
                border-left: 1px solid {Styles.Theme.BORDER_LIGHT};
                background-color: {Styles.Theme.BG_SIDEBAR};
                border-top-right-radius: 4px;
            }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 16px;
                border-left: 1px solid {Styles.Theme.BORDER_LIGHT};
                background-color: {Styles.Theme.BG_SIDEBAR};
                border-bottom-right-radius: 4px;
            }}
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
                background-color: {Styles.Theme.BORDER_LIGHT};
            }}
        """

    @staticmethod
    def get_combobox_style():
        """Style for QComboBox"""
        return f"""
            QComboBox {{
                padding: 6px;
                border: 1px solid {Styles.Theme.BORDER_LIGHT};
                border-radius: 4px;
                background-color: {Styles.Theme.BG_APP};
                font-size: 13px;
                color: {Styles.Theme.TEXT_MAIN};
                min-width: 6em;
            }}
            QComboBox:focus {{
                border: 2px solid {Styles.Theme.PRIMARY};
                background-color: {Styles.Theme.BG_WHITE};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: {Styles.Theme.BORDER_LIGHT};
                border-left-style: solid;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }}
            QComboBox::down-arrow {{
                image: none; /* Podemos usar una imagen o dejar el default si es native */
                border: none;
                width: 0; 
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {Styles.Theme.TEXT_MUTED};
                margin-top: 2px;
                margin-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {Styles.Theme.BORDER_LIGHT};
                selection-background-color: {Styles.Theme.PRIMARY};
                selection-color: white;
            }}
        """
