# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Core modules for Canchas Las Tortolas plugin
                                 A QGIS plugin
 Plugin para procesamiento de canchas Las Tortolas - Linkapsis
                             -------------------
        begin                : 2024-08-13
        git sha              : $Format:%H$
        copyright            : (C) 2024 by Linkapsis
        email                : info@linkapsis.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

# Core processing modules for Canchas Las Tortolas
__version__ = "1.1.0"
__author__ = "Linkapsis"

# Core modules
from . import validation
from . import processing
from . import table_creation
from . import volume_screenshot
from . import xml_export
from . import pdf_reports
from . import data_merge  # Module for data merge functionality
from . import historical_analysis  # Module for historical data analysis
from . import bar_charts  # Module for generating bar charts
from . import bar_charts_new  # New module for generating bar charts (fixed version)
from . import bar_charts_simple  # Simple module based on working script
from . import time_series_charts  # Module for generating time series charts
from . import heatmap_screenshots  # Module for generating heatmap screenshots
from . import espesor_classification  # Module for espesor thickness classification