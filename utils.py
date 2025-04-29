"""
Hilfsfunktionen für das Desktop-Automatisierungstool.
"""

import os
import sys
import time
import json
import pyautogui
from typing import List, Tuple, Dict, Any, Optional
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QImage, QFont
from PIL import ImageGrab

from constants import *


class RegionSelector(QWidget):
    """Widget zur Auswahl einer Region auf dem Bildschirm"""
    
    def __init__(self, callback=None):
        """
        Initialisiert den Region-Selector
        
        Args:
            callback: Funktion, die mit der ausgewählten Region aufgerufen wird
                     nach der Auswahl. Format: [x, y, width, height]
        """
        super().__init__()
        
        # Bildschirmgeometrie ermitteln
        self.screen_geometry = QApplication.primaryScreen().geometry()
        
        # Widget für die gesamte Bildschirmfläche einrichten
        self.setGeometry(self.screen_geometry)
        self.setWindowTitle("Region auswählen")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Variablen für die Regionauswahl
        self.start_point = None
        self.current_rect = None
        self.is_drawing = False
        
        # Callback-Funktion speichern
        self.callback = callback
        
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
    def paintEvent(self, event):
        """Zeichnet das Overlay für die Regionauswahl"""
        painter = QPainter(self)
        
        # Halbtransparenten Hintergrund zeichnen
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        # Wenn eine Region ausgewählt wird, zeichne sie
        if self.current_rect:
            # Transparentes Inneres für die ausgewählte Region
            painter.fillRect(self.current_rect, QColor(255, 255, 255, 50))
            
            # Rahmen um die Region zeichnen
            pen = QPen(QColor(ACCENT_COLOR), 2)
            painter.setPen(pen)
            painter.drawRect(self.current_rect)
            
            # Abmessungen anzeigen
            width = self.current_rect.width()
            height = self.current_rect.height()
            text = f"{width} x {height}"
            
            # Text mit Hintergrund für bessere Sichtbarkeit
            text_rect = painter.boundingRect(self.current_rect, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, text)
            painter.fillRect(text_rect, QColor(0, 0, 0, 180))
            
            # Text in Weiß zeichnen
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(self.current_rect, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, text)
    
    def mousePressEvent(self, event):
        """Startet die Regionauswahl bei Mausklick"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.position().toPoint()
            self.current_rect = QRect(self.start_point, self.start_point)
            self.is_drawing = True
            self.update()
    
    def mouseMoveEvent(self, event):
        """Aktualisiert die Region während der Mausbewegung"""
        if self.is_drawing:
            end_point = event.position().toPoint()
            self.current_rect = QRect(self.start_point, end_point).normalized()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Beendet die Regionauswahl bei Mausloslassen"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
            end_point = event.position().toPoint()
            self.current_rect = QRect(self.start_point, end_point).normalized()
            self.is_drawing = False
            
            # Wenn eine gültige Region ausgewählt wurde und ein Callback existiert
            if self.current_rect.width() > 5 and self.current_rect.height() > 5 and self.callback:
                region = [
                    self.current_rect.x(),
                    self.current_rect.y(),
                    self.current_rect.width(),
                    self.current_rect.height()
                ]
                self.callback(region)
            
            self.close()
    
    def keyPressEvent(self, event):
        """Ermöglicht das Abbrechen der Auswahl mit Escape"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()


class ColorPicker(QWidget):
    """Widget zur Auswahl einer Farbe auf dem Bildschirm"""
    
    def __init__(self, callback=None):
        """
        Initialisiert den Color-Picker
        
        Args:
            callback: Funktion, die mit der ausgewählten Farbe aufgerufen wird
                     nach der Auswahl. Format: (r, g, b)
        """
        super().__init__()
        
        # Bildschirmgeometrie ermitteln
        self.screen = QApplication.primaryScreen()
        self.screen_geometry = self.screen.geometry()
        
        # Widget für die Farbauswahl einrichten
        self.setWindowTitle("Farbe auswählen")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Größe und Position des Widgets
        self.setFixedSize(180, 180)
        
        # Layout erstellen
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Label für Farbe und Werte
        self.color_info = QLabel("")
        self.color_info.setStyleSheet(f"""
            background-color: {PRIMARY_COLOR}; 
            color: {TEXT_COLOR};
            border: 1px solid {ACCENT_COLOR};
            border-radius: 5px;
            padding: 5px;
        """)
        self.color_info.setFont(QFont("Arial", 9))
        self.color_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.color_info)
        
        # Lupe initialisieren
        self.magnifier_size = 150
        self.zoom_factor = 4
        
        self.magnifier = QLabel()
        self.magnifier.setFixedSize(self.magnifier_size, self.magnifier_size)
        self.magnifier.setStyleSheet(f"border: 2px solid {ACCENT_COLOR}; border-radius: 75px;")
        layout.addWidget(self.magnifier)
        
        # Mausposition und aktuell ausgewählte Farbe
        self.mouse_pos = QPoint(0, 0)
        self.current_color = None
        self.pixel_info = {}  # Speichert Informationen über jeden Pixel in der Lupe
        
        # Callback-Funktion speichern
        self.callback = callback
        
        # Timer für regelmäßiges Update
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_magnifier)
        self.update_timer.start(50)  # Alle 50ms aktualisieren
        
        # Maus verfolgen
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
    def update_magnifier(self):
        """Aktualisiert die Lupe mit dem Bildschirminhalt unter dem Mauszeiger"""
        # Aktuelle Mausposition abrufen
        self.mouse_pos = QApplication.primaryScreen().cursor().pos()
        
        # Fensterposition aktualisieren, um dem Mauszeiger zu folgen
        window_pos = QPoint(
            self.mouse_pos.x() + 20,
            self.mouse_pos.y() + 20
        )
        
        # Sicherstellen, dass das Fenster innerhalb des Bildschirms bleibt
        if window_pos.x() + self.width() > self.screen_geometry.width():
            window_pos.setX(self.mouse_pos.x() - 20 - self.width())
        if window_pos.y() + self.height() > self.screen_geometry.height():
            window_pos.setY(self.mouse_pos.y() - 20 - self.height())
            
        self.move(window_pos)
        
        try:
            # Screenshot des Bereichs unter dem Mauszeiger
            x = self.mouse_pos.x() - self.zoom_factor * self.magnifier_size // 2
            y = self.mouse_pos.y() - self.zoom_factor * self.magnifier_size // 2
            width = self.zoom_factor * self.magnifier_size
            height = self.zoom_factor * self.magnifier_size
            
            # Bildschirmkoordinaten korrigieren
            x = max(0, min(x, self.screen_geometry.width() - width))
            y = max(0, min(y, self.screen_geometry.height() - height))
            
            # Screenshot mit PIL machen
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            
            # Farbe des Pixels unter dem Mauszeiger ermitteln
            pixel_x = self.mouse_pos.x() - x
            pixel_y = self.mouse_pos.y() - y
            
            if 0 <= pixel_x < width and 0 <= pixel_y < height:
                self.current_color = screenshot.getpixel((pixel_x, pixel_y))
                
                if len(self.current_color) > 3:  # Bei RGBA-Format das Alpha entfernen
                    self.current_color = self.current_color[:3]
                    
                r, g, b = self.current_color
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                
                # Farb-Info aktualisieren
                self.color_info.setText(f"RGB: {r}, {g}, {b}\nHEX: {hex_color}")
                
                # Rahmenfarbe basierend auf Helligkeit anpassen
                brightness = (0.299 * r + 0.587 * g + 0.114 * b)
                self.magnifier.setStyleSheet(f"""
                    border: 2px solid {'#ffffff' if brightness < 128 else '#000000'};
                    border-radius: 75px;
                """)
            
            # Screenshot in QImage konvertieren und anzeigen
            screenshot = screenshot.resize((self.magnifier_size, self.magnifier_size))
            qim = screenshot.tobytes("raw", "RGB")
            qimg = QImage(qim, screenshot.width, screenshot.height, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            
            # Overlay mit Fadenkreuz zeichnen
            painter = QPainter(pixmap)
            pen = QPen(QColor(255, 255, 255))
            pen.setWidth(1)
            painter.setPen(pen)
            
            # Horizontale Linie
            painter.drawLine(0, self.magnifier_size // 2, self.magnifier_size, self.magnifier_size // 2)
            
            # Vertikale Linie
            painter.drawLine(self.magnifier_size // 2, 0, self.magnifier_size // 2, self.magnifier_size)
            
            # Zentralen Punkt markieren
            pen.setColor(QColor(0, 0, 0))
            painter.setPen(pen)
            painter.drawEllipse(
                self.magnifier_size // 2 - 2,
                self.magnifier_size // 2 - 2,
                4, 4
            )
            
            painter.end()
            
            # Aktualisierte Lupe anzeigen
            self.magnifier.setPixmap(pixmap)
            
        except Exception as e:
            print(f"Fehler beim Aktualisieren der Lupe: {e}")
        
    def mousePressEvent(self, event):
        """Wählt die Farbe unter dem Mauszeiger aus"""
        if event.button() == Qt.MouseButton.LeftButton and self.current_color:
            if self.callback:
                self.callback(self.current_color)
            self.close()
    
    def keyPressEvent(self, event):
        """Ermöglicht das Abbrechen der Auswahl mit Escape"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()


def get_platform():
    """Gibt das aktuelle Betriebssystem zurück"""
    if sys.platform.startswith('darwin'):
        return 'macos'
    elif sys.platform.startswith('win'):
        return 'windows'
    else:
        return 'linux'


def get_default_tesseract_path():
    """Gibt den standardmäßigen Tesseract-Pfad für das aktuelle Betriebssystem zurück"""
    platform = get_platform()
    if platform == 'macos':
        return TESSERACT_PATH_MAC
    elif platform == 'windows':
        return TESSERACT_PATH_WINDOWS
    else:
        return TESSERACT_PATH_LINUX


def validate_color(color_str: str) -> Tuple[bool, Optional[List[int]]]:
    """
    Überprüft, ob ein Farbstring gültig ist und konvertiert ihn in RGB-Werte
    
    Args:
        color_str: Farbstring im Format "r, g, b" oder "#rrggbb"
        
    Returns:
        Tuple[bool, Optional[List[int]]]: (ist_gültig, [r, g, b])
    """
    try:
        # Versuche, als RGB zu parsen
        if ',' in color_str:
            rgb = [int(c.strip()) for c in color_str.split(',')]
            if len(rgb) >= 3 and all(0 <= c <= 255 for c in rgb[:3]):
                return True, rgb[:3]
        
        # Versuche, als Hex zu parsen
        elif color_str.startswith('#') and len(color_str) == 7:
            r = int(color_str[1:3], 16)
            g = int(color_str[3:5], 16)
            b = int(color_str[5:7], 16)
            return True, [r, g, b]
    except:
        pass
        
    return False, None


def validate_region(region_str: str) -> Tuple[bool, Optional[List[int]]]:
    """
    Überprüft, ob ein Regions-String gültig ist und konvertiert ihn in eine Liste
    
    Args:
        region_str: Regions-String im Format "x, y, width, height"
        
    Returns:
        Tuple[bool, Optional[List[int]]]: (ist_gültig, [x, y, width, height])
    """
    try:
        values = [int(v.strip()) for v in region_str.split(',')]
        if len(values) == 4 and values[2] > 0 and values[3] > 0:
            return True, values
    except:
        pass
        
    return False, None


def load_settings() -> Dict[str, Any]:
    """
    Lädt die Einstellungen aus der Einstellungsdatei
    
    Returns:
        Dict[str, Any]: Einstellungen
    """
    default_settings = {
        "tesseract_path": get_default_tesseract_path(),
        "failsafe": True,
        "between_actions_delay": DEFAULT_BETWEEN_ACTIONS_DELAY,
        "recent_workflows": [],
        "recent_directories": []
    }
    
    if not os.path.exists(SETTINGS_FILE):
        return default_settings
        
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
        
        # Stelle sicher, dass alle erforderlichen Einstellungen vorhanden sind
        for key, value in default_settings.items():
            if key not in settings:
                settings[key] = value
                
        return settings
    except:
        return default_settings


def save_settings(settings: Dict[str, Any]):
    """
    Speichert die Einstellungen in der Einstellungsdatei
    
    Args:
        settings: Einstellungen
    """
    try:
        # Stelle sicher, dass das Verzeichnis existiert
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Fehler beim Speichern der Einstellungen: {e}")


def add_recent_workflow(filename: str, max_entries: int = 10):
    """
    Fügt einen Workflow zur Liste der zuletzt verwendeten Workflows hinzu
    
    Args:
        filename: Pfad zur Workflow-Datei
        max_entries: Maximale Anzahl der Einträge in der Liste
    """
    settings = load_settings()
    recent = settings.get("recent_workflows", [])
    
    # Entferne den Eintrag, falls er bereits vorhanden ist
    if filename in recent:
        recent.remove(filename)
    
    # Füge den Eintrag am Anfang der Liste hinzu
    recent.insert(0, filename)
    
    # Begrenze die Anzahl der Einträge
    settings["recent_workflows"] = recent[:max_entries]
    
    save_settings(settings)
