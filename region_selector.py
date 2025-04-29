"""
Region-Selector Modul

Dieses Modul ermöglicht die Auswahl einer Region auf dem Bildschirm
mit der Maus für die OCR-Funktion des Desktop-Automatisierungstools.
"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor, QScreen


class RegionSelector(QWidget):
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


# Konstanten
ACCENT_COLOR = "#5D5FEF"  # Helles Blau für Akzente (muss mit main.py übereinstimmen)


# Beispielnutzung
if __name__ == "__main__":
    def on_region_selected(region):
        print(f"Ausgewählte Region: {region}")
        
    app = QApplication(sys.argv)
    selector = RegionSelector(callback=on_region_selected)
    selector.show()
    sys.exit(app.exec())
