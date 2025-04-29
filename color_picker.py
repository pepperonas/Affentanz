"""
Color-Picker Modul

Dieses Modul ermöglicht die Auswahl einer Farbe auf dem Bildschirm
mit der Maus für die Farberkennungsfunktion des Desktop-Automatisierungstools.
"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QImage, QFont
from PIL import ImageGrab


class ColorPicker(QWidget):
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


# Konstanten (müssen mit main.py übereinstimmen)
PRIMARY_COLOR = "#2C2E3B"  # Dunkles Blaugrau (Hauptfarbschema)
ACCENT_COLOR = "#5D5FEF"   # Helles Blau für Akzente
TEXT_COLOR = "#FFFFFF"     # Weiß für Text


# Beispielnutzung
if __name__ == "__main__":
    def on_color_selected(color):
        print(f"Ausgewählte Farbe: RGB {color}")
        
    app = QApplication(sys.argv)
    picker = ColorPicker(callback=on_color_selected)
    picker.show()
    sys.exit(app.exec())
