---
description: Expert guide for designing Modern, High-End User Interfaces in QGIS Plugins (PyQt5)
---

# QGIS UI Design Expert Skill

This skill provides a comprehensive design system and technical guide for building "Premium" User Interfaces within the QGIS environment.

## 1. Design Philosophy: "Native Plus"
The goal is to create UIs that feel native to QGIS (respecting the host environment) but offer a significantly upgraded, modern aesthetic ("WOW factor").

*   **Structure:** Use standard `QLayouts` (HBox, VBox, Grid) for robust responsiveness.
*   **Styling:** Use **QSS (Qt Style Sheets)** for all visual attributes (colors, radius, transparency).
*   **Interaction:** Micro-animations on hover/click using generic QSS pseudo-states (`:hover`, `:pressed`).

## 2. The Tech Stack
*   **Structure:** `PyQt5.QtWidgets` (QVBoxLayout, QFrame, QScrollArea).
*   **Style:** Native QSS (CSS 2.1 subset).
*   **Icons:** Scalable SVGs (`QIcon`). DO NOT use raster images for UI elements.

## 3. Design System (Copy-Paste Ready)

### 3.1. Fundamental Variables (Concept)
*Define these as constants in your Python code or simulate them in QSS.*

| Token | Scoped Value | Usage |
| :--- | :--- | :--- |
| `Primary` | `#2563EB` (Royal Blue) | Main Actions, Active States |
| `Surface` | `#FFFFFF` (White) | Cards, Modals |
| `Background` | `#F3F4F6` (Light Gray) | App Background |
| `Text` | `#1F2937` (Dark Gray) | Primary Content |
| `Muted` | `#6B7280` (Gray) | Secondary Text, Borders |
| `Radius` | `6px` | Standard Corner Radius |
| `Shadow` | `1px 2px 4px rgba(0,0,0,0.1)` | Subtle Depth |

### 3.2. Surface & Structure (The "Card" Pattern)
Create modern grouping by placing controls inside styled `QFrame`s ("Cards").

```python
# Python Setup
card = QFrame()
card.setObjectName("card")
layout.addWidget(card)
```

```css
/* QSS */
QFrame#card {
    background-color: white;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 16px;
}
```

### 3.3. Typography
Avoid default system fonts if possible. Use a clean sans-serif stack.

```css
QWidget {
    font-family: "Segoe UI", "Roboto", "Helvetica Neue", sans-serif;
    font-size: 13px;
    color: #374151;
}
QLabel#header {
    font-size: 18px;
    font-weight: bold;
    color: #111827;
    margin-bottom: 8px;
}
```

### 3.4. Modern Buttons (Gradient & Interactive)

```css
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3B82F6, stop:1 #2563EB);
    color: white;
    border: 1px solid #2563EB;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #60A5FA, stop:1 #3B82F6);
    border-color: #60A5FA;
}
QPushButton:pressed {
    background-color: #1D4ED8; /* Solid color for instant feedback */
    padding-top: 9px; /* Pseudo-3D click effect */
}
```

## 4. Advanced Techniques

### 4.1. "Glassmorphism" (Simulation)
True blur is hard in QWidgets, but transparency is easy.
```css
QFrame#glass {
    background-color: rgba(255, 255, 255, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.5);
    border-radius: 12px;
}
```

### 4.2. Status Indicators (Pills)
Use `QLabel` with rounding equal to height/2.
```css
QLabel#status_pill {
    background-color: #D1FAE5; /* Light Green */
    color: #065F46; /* Dark Green Text */
    border-radius: 12px; /* Pill shape */
    padding: 4px 12px;
    font-weight: bold;
}
```

## 5. Tailwind CSS Integration (Experimental)
While not native, you can use the **Atomic CSS** methodology in QTS.
*   **Concept:** Create a helper function that maps Tailwind-like strings to QSS.

```python
def apply_tw(widget, classes):
    """
    Applies a simplified mapping of Tailwind classes to QSS.
    Example: apply_tw(btn, "bg-blue-500 text-white p-2 rounded")
    """
    qss = ""
    tokens = classes.split()
    if "bg-blue-500" in tokens: qss += "background-color: #3B82F6; "
    if "text-white" in tokens: qss += "color: white; "
    if "p-2" in tokens: qss += "padding: 8px; "
    if "rounded" in tokens: qss += "border-radius: 4px; "
    
    current = widget.styleSheet()
    widget.setStyleSheet(current + qss)
```

## 6. Implementation Workflow
1.  **Sketch:** Define layout using Boxes (VBox/HBox).
2.  **Structure:** Code the layout in `tabs/your_tab.py`. Assign `objectName` to key containers.
3.  **Style:** Create a `styles.qss` file (or string).
4.  **Load:** Apply `setStyleSheet(load_qss())` to the main Dialog/Widget at init.
