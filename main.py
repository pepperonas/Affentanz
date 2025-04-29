#!/usr/bin/env python3
"""
Desktop-Automatisierungstool

Dieses Tool ermöglicht die Automatisierung von Benutzerinteraktionen auf macOS,
inklusive Mausbewegungen, Klicks, Tastatureingaben und Wartezeiten.
Unterstützt Farbmustererkennung und OCR zur Bildschirmerkennung.
"""

import os
import sys
import time
import json
import pyautogui
import pytesseract
from PIL import Image, ImageGrab
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QListWidget, QLabel, QLineEdit,
                             QSpinBox, QDoubleSpinBox, QComboBox, QFileDialog, QMessageBox,
                             QCheckBox, QScrollArea, QGridLayout, QFrame, QSplitter, QMenu,
                             QToolBar, QStatusBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint, QSize, QRect
from PyQt6.QtGui import QAction, QIcon, QColor, QPalette, QFont, QPixmap, QImage, QShortcut, QKeySequence

# Eigene Module
from models import Action, ActionType
from automation_engine import AutomationEngine
from threads import WorkflowThread, RecordingThread
from utils import RegionSelector, ColorPicker, load_settings, save_settings, get_default_tesseract_path
from workflow_tab import WorkflowTab
from constants import *


class MainWindow(QMainWindow):
    """Hauptfenster der Anwendung"""

    def __init__(self):
        super().__init__()

        # Grundlegende Einstellungen
        pyautogui.FAILSAFE = True  # Sicherheitsfunktion: Maus in die Ecke bewegen stoppt Programm
        self.settings = load_settings()
        pytesseract.pytesseract.tesseract_cmd = self.settings.get("tesseract_path",
                                                                  get_default_tesseract_path())

        # Automatisierungs-Engine initialisieren
        self.engine = AutomationEngine()

        # Threads für Aufzeichnung und Ausführung
        self.workflow_thread = None
        self.recording_thread = None

        # UI-Status
        self.current_file = None
        self.is_modified = False

        # UI einrichten
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        """Richtet die Benutzeroberfläche ein"""
        self.setWindowTitle("Desktop-Automatisierungstool")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        # Material Design Farbschema
        self.apply_theme()

        # Haupt-Widget und Layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Toolbar erstellen
        self.create_toolbar()

        # Tab-Widget erstellen
        self.tab_widget = QTabWidget()

        # Tab 1: Workflow-Editor
        self.workflow_tab = WorkflowTab(self.engine)
        self.workflow_tab.workflow_changed.connect(self.on_workflow_changed)
        self.workflow_tab.status_message.connect(self.show_status_message)
        self.tab_widget.addTab(self.workflow_tab, "Workflow")

        # TODO: Tab 2: Bildschirmerkennung (später implementieren)
        # TODO: Tab 3: Einstellungen (später implementieren)

        # Tabs zum Hauptlayout hinzufügen
        main_layout.addWidget(self.tab_widget)

        # Statusleiste
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Bereit")

        # Zentrales Widget setzen
        self.setCentralWidget(central_widget)

    def apply_theme(self):
        """Wendet das Material Design Farbschema an"""
        app = QApplication.instance()

        # Palette für die App erstellen
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(PRIMARY_COLOR))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_COLOR))
        palette.setColor(QPalette.ColorRole.Base, QColor(SECONDARY_BG))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(PRIMARY_COLOR))
        palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_COLOR))
        palette.setColor(QPalette.ColorRole.Button, QColor(PRIMARY_COLOR))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT_COLOR))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT_COLOR))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(TEXT_COLOR))

        app.setPalette(palette)

        # Stylesheet für weitere Anpassungen
        self.setStyleSheet(f"""
            QMainWindow, QDialog, QWidget, QTabWidget::pane, QTabBar::tab {{
                background-color: {PRIMARY_COLOR};
                color: {TEXT_COLOR};
            }}

            QTabBar::tab:selected {{
                background-color: {ACCENT_COLOR};
            }}

            QPushButton {{
                background-color: {ACCENT_COLOR};
                color: {TEXT_COLOR};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: {BUTTON_MIN_WIDTH}px;
            }}

            QPushButton:hover {{
                background-color: {ACCENT_COLOR}BB;
            }}

            QPushButton:pressed {{
                background-color: {ACCENT_COLOR}99;
            }}

            QPushButton:disabled {{
                background-color: {SECONDARY_BG};
                color: {TEXT_COLOR}99;
            }}

            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: {SECONDARY_BG};
                color: {TEXT_COLOR};
                border: 1px solid {ACCENT_COLOR};
                border-radius: 4px;
                padding: 4px;
            }}

            QListWidget {{
                background-color: {SECONDARY_BG};
                color: {TEXT_COLOR};
                border: 1px solid {ACCENT_COLOR};
                border-radius: 4px;
            }}

            QScrollBar {{
                background-color: {SECONDARY_BG};
            }}

            QLabel {{
                color: {TEXT_COLOR};
            }}

            QToolBar {{
                background-color: {PRIMARY_COLOR};
                spacing: 5px;
                border: none;
            }}

            QStatusBar {{
                background-color: {SECONDARY_BG};
                color: {TEXT_COLOR};
            }}
        """)

    def create_toolbar(self):
        """Erstellt die Werkzeugleiste"""
        # Toolbar
        toolbar = QToolBar("Hauptwerkzeugleiste")
        toolbar.setIconSize(QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Dateioperationen
        new_action = QAction("Neu", self)
        new_action.setShortcut(QKeySequence(SHORTCUT_NEW))
        new_action.triggered.connect(self.new_workflow)
        toolbar.addAction(new_action)

        open_action = QAction("Öffnen", self)
        open_action.setShortcut(QKeySequence(SHORTCUT_OPEN))
        open_action.triggered.connect(self.load_workflow)
        toolbar.addAction(open_action)

        save_action = QAction("Speichern", self)
        save_action.setShortcut(QKeySequence(SHORTCUT_SAVE))
        save_action.triggered.connect(self.save_workflow)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        # Workflow-Steuerung
        self.record_action = QAction("Aufnahme", self)
        self.record_action.setCheckable(True)
        self.record_action.setShortcut(QKeySequence(SHORTCUT_RECORD))
        self.record_action.triggered.connect(self.toggle_recording)
        toolbar.addAction(self.record_action)

        self.play_action = QAction("Abspielen", self)
        self.play_action.setShortcut(QKeySequence(SHORTCUT_PLAY))
        self.play_action.triggered.connect(self.play_workflow)
        toolbar.addAction(self.play_action)

        self.stop_action = QAction("Stopp", self)
        self.stop_action.setShortcut(QKeySequence(SHORTCUT_STOP))
        self.stop_action.triggered.connect(self.stop_workflow)
        self.stop_action.setEnabled(False)
        toolbar.addAction(self.stop_action)

    def setup_shortcuts(self):
        """Richtet zusätzliche Tastaturkürzel ein"""
        # ESC-Taste zum Abbrechen von Aufzeichnung oder Ausführung
        esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc_shortcut.activated.connect(self.emergency_stop)

    def new_workflow(self):
        """Erstellt einen neuen, leeren Workflow"""
        # Prüfen, ob es ungespeicherte Änderungen gibt
        if self.is_modified and not self._confirm_discard_changes():
            return

        # Workflow leeren
        self.engine.clear_workflow()
        self.workflow_tab.refresh_workflow_list()

        # Status zurücksetzen
        self.current_file = None
        self.is_modified = False
        self.workflow_tab.set_modified(False)

        # Statusmeldung
        self.show_status_message("Neuer Workflow erstellt")

    def load_workflow(self):
        """Lädt einen Workflow aus einer Datei"""
        # Prüfen, ob es ungespeicherte Änderungen gibt
        if self.is_modified and not self._confirm_discard_changes():
            return

        # Dateiauswahldialog
        filename, _ = QFileDialog.getOpenFileName(
            self, "Workflow laden", "", "JSON-Dateien (*.json)"
        )

        if not filename:
            return

        try:
            # Workflow laden
            count = self.engine.load_workflow(filename)

            # UI aktualisieren
            self.workflow_tab.refresh_workflow_list()

            # Status aktualisieren
            self.current_file = filename
            self.is_modified = False
            self.workflow_tab.set_modified(False)

            # Zu den zuletzt verwendeten Workflows hinzufügen
            add_recent_workflow(filename)

            # Statusmeldung
            self.show_status_message(f"{count} Aktionen geladen aus {os.path.basename(filename)}")

        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Laden",
                                 f"Der Workflow konnte nicht geladen werden: {str(e)}")

    def save_workflow(self):
        """Speichert den aktuellen Workflow"""
        # Prüfen, ob es etwas zu speichern gibt
        if not self.engine.workflow:
            QMessageBox.warning(self, "Leerer Workflow",
                                "Es gibt keine Aktionen zum Speichern.")
            return

        # Wenn es noch keine Datei gibt, "Speichern unter" aufrufen
        if not self.current_file:
            return self.save_workflow_as()

        try:
            # Workflow speichern
            self.engine.save_workflow(self.current_file)

            # Status aktualisieren
            self.is_modified = False
            self.workflow_tab.set_modified(False)

            # Zu den zuletzt verwendeten Workflows hinzufügen
            add_recent_workflow(self.current_file)

            # Statusmeldung
            self.show_status_message(f"Workflow gespeichert als {os.path.basename(self.current_file)}")

        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Speichern",
                                 f"Der Workflow konnte nicht gespeichert werden: {str(e)}")

    def save_workflow_as(self):
        """Speichert den aktuellen Workflow unter einem neuen Namen"""
        # Prüfen, ob es etwas zu speichern gibt
        if not self.engine.workflow:
            QMessageBox.warning(self, "Leerer Workflow",
                                "Es gibt keine Aktionen zum Speichern.")
            return

        # Dateiauswahldialog
        filename, _ = QFileDialog.getSaveFileName(
            self, "Workflow speichern", "", "JSON-Dateien (*.json)"
        )

        if not filename:
            return

        # Sicherstellen, dass die Datei die Endung .json hat
        if not filename.lower().endswith('.json'):
            filename += '.json'

        try:
            # Workflow speichern
            self.engine.save_workflow(filename)

            # Status aktualisieren
            self.current_file = filename
            self.is_modified = False
            self.workflow_tab.set_modified(False)

            # Zu den zuletzt verwendeten Workflows hinzufügen
            add_recent_workflow(filename)

            # Statusmeldung
            self.show_status_message(f"Workflow gespeichert als {os.path.basename(filename)}")
            return True

        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Speichern",
                                 f"Der Workflow konnte nicht gespeichert werden: {str(e)}")
            return False

    def toggle_recording(self, checked=None):
        """Startet oder stoppt die Aufzeichnung"""
        if checked is None:
            checked = not self.engine.is_recording
            self.record_action.setChecked(checked)

        if checked:
            # Aufnahme starten
            self.engine.start_recording()

            # Thread für die Aufzeichnung starten
            self.recording_thread = RecordingThread(self.engine)
            self.recording_thread.action_recorded.connect(self.on_action_recorded)
            self.recording_thread.error_occurred.connect(self.on_recording_error)

            self.recording_thread.start()

            # UI-Status aktualisieren
            self.record_action.setText("Aufnahme stoppen")
            self.play_action.setEnabled(False)

            # Statusmeldung
            self.show_status_message("Aufnahme gestartet... Drücke erneut zum Beenden")

        else:
            # Aufnahme stoppen
            self.engine.stop_recording()

            # Thread beenden
            if self.recording_thread:
                self.recording_thread.stop()
                self.recording_thread = None

            # UI-Status aktualisieren
            self.record_action.setText("Aufnahme")
            self.play_action.setEnabled(True)

            # Statusmeldung
            self.show_status_message("Aufnahme beendet")

    def on_action_recorded(self, action: Action):
        """Wird aufgerufen, wenn eine Aktion aufgezeichnet wurde"""
        # Aktion zum Workflow hinzufügen
        self.engine.add_action(action)

        # UI aktualisieren
        self.workflow_tab.refresh_workflow_list()

        # Status aktualisieren
        self.is_modified = True
        self.workflow_tab.set_modified(True)

        # Statusmeldung
        self.show_status_message(f"Aktion aufgezeichnet: {action.get_description()}")

    def on_recording_error(self, error_message: str):
        """Wird aufgerufen, wenn ein Fehler bei der Aufzeichnung auftritt"""
        self.toggle_recording(False)  # Aufzeichnung stoppen
        QMessageBox.warning(self, "Aufzeichnungsfehler", error_message)

    def play_workflow(self):
        """Führt den aktuellen Workflow aus"""
        # Prüfen, ob es einen Workflow gibt
        if not self.engine.workflow:
            QMessageBox.warning(self, "Leerer Workflow",
                                "Es gibt keine Aktionen zum Ausführen.")
            return

        # Prüfen, ob bereits eine Ausführung läuft
        if self.engine.is_playing:
            return

        # Thread für die Ausführung starten
        self.workflow_thread = WorkflowThread(self.engine)
        self.workflow_thread.progress_updated.connect(self.update_playback_progress)
        self.workflow_thread.error_occurred.connect(self.on_playback_error)
        self.workflow_thread.finished.connect(self.on_playback_finished)

        self.workflow_thread.start()

        # UI-Status aktualisieren
        self.play_action.setEnabled(False)
        self.record_action.setEnabled(False)
        self.stop_action.setEnabled(True)

        # Statusmeldung
        self.show_status_message("Workflow wird ausgeführt...")

    def stop_workflow(self):
        """Stoppt die Ausführung des aktuellen Workflows"""
        if self.workflow_thread:
            # Thread stoppen
            self.workflow_thread.stop()

            # Warte maximal 1 Sekunde
            if not self.workflow_thread.wait(1000):
                # Im Notfall terminieren
                self.workflow_thread.terminate()
                self.workflow_thread.wait()

            # Thread-Objekt aufräumen
            self.workflow_thread = None

        # UI-Status aktualisieren
        self.play_action.setEnabled(True)
        self.record_action.setEnabled(True)
        self.stop_action.setEnabled(False)

        # Statusmeldung
        self.show_status_message("Workflow-Ausführung gestoppt")

    def emergency_stop(self):
        """Nothalt für alle laufenden Prozesse"""
        # Aufzeichnung stoppen
        if self.engine.is_recording:
            self.toggle_recording(False)

        # Ausführung stoppen
        if self.engine.is_playing:
            self.stop_workflow()

        # Statusmeldung
        self.show_status_message("Notfall-Stopp ausgeführt!", 5000)

    def update_playback_progress(self, index: int):
        """Aktualisiert die Fortschrittsanzeige während der Ausführung"""
        if 0 <= index < len(self.engine.workflow):
            # Aktion in der Liste auswählen
            self.workflow_tab.workflow_list.setCurrentRow(index)

            # Statusmeldung
            action = self.engine.workflow[index]
            self.show_status_message(f"Führe aus: {action.get_description()}")

    def on_playback_error(self, error_message: str):
        """Wird aufgerufen, wenn ein Fehler bei der Ausführung auftritt"""
        # Thread-Objekt aufräumen und UI zurücksetzen
        if self.workflow_thread:
            # Thread stoppen
            self.workflow_thread.stop()

            # Warte maximal 1 Sekunde
            if not self.workflow_thread.wait(1000):
                # Im Notfall terminieren
                self.workflow_thread.terminate()
                self.workflow_thread.wait()

            # Thread-Objekt aufräumen
            self.workflow_thread = None

        # UI-Status aktualisieren
        self.play_action.setEnabled(True)
        self.record_action.setEnabled(True)
        self.stop_action.setEnabled(False)

        # Fehlermeldung anzeigen
        QMessageBox.warning(self, "Ausführungsfehler", error_message)

    def on_playback_finished(self):
        """Wird aufgerufen, wenn die Workflow-Ausführung beendet wurde"""
        # Thread aufräumen
        if self.workflow_thread:
            # Stellen sicher, dass alles ordnungsgemäß beendet ist
            if self.workflow_thread.isRunning():
                self.workflow_thread.stop()

                # Warte maximal 1 Sekunde
                if not self.workflow_thread.wait(1000):
                    # Im Notfall terminieren
                    self.workflow_thread.terminate()
                    self.workflow_thread.wait()

        # Thread-Objekt aufräumen
        self.workflow_thread = None

        # UI-Status aktualisieren
        self.play_action.setEnabled(True)
        self.record_action.setEnabled(True)
        self.stop_action.setEnabled(False)

        # Statusmeldung
        self.show_status_message("Workflow-Ausführung abgeschlossen")

    def on_workflow_changed(self):
        """Wird aufgerufen, wenn der Workflow geändert wurde"""
        self.is_modified = True

    def show_status_message(self, message: str, timeout: int = STATUSBAR_TIMEOUT):
        """Zeigt eine Nachricht in der Statusleiste an"""
        self.statusBar.showMessage(message, timeout)

    def _confirm_discard_changes(self) -> bool:
        """
        Fragt den Benutzer, ob ungespeicherte Änderungen verworfen werden sollen

        Returns:
            bool: True, wenn die Änderungen verworfen werden können, False sonst
        """
        response = QMessageBox.question(
            self,
            "Ungespeicherte Änderungen",
            "Es gibt ungespeicherte Änderungen. Möchtest du diese speichern?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
        )

        if response == QMessageBox.StandardButton.Save:
            return self.save_workflow_as()
        elif response == QMessageBox.StandardButton.Discard:
            return True
        else:  # Cancel
            return False

    def closeEvent(self, event):
        """Wird aufgerufen, wenn das Fenster geschlossen werden soll"""
        # Prüfen, ob es ungespeicherte Änderungen gibt
        if self.is_modified and not self._confirm_discard_changes():
            event.ignore()
            return

        # Aufräumen
        if self.recording_thread:
            self.recording_thread.stop()

            # Warte maximal 1 Sekunde
            if not self.recording_thread.wait(1000):
                # Im Notfall terminieren
                self.recording_thread.terminate()
                self.recording_thread.wait()

        if self.workflow_thread:
            self.workflow_thread.stop()

            # Warte maximal 1 Sekunde
            if not self.workflow_thread.wait(1000):
                # Im Notfall terminieren
                self.workflow_thread.terminate()
                self.workflow_thread.wait()

        # Einstellungen speichern
        save_settings(self.settings)

        # Event akzeptieren (Fenster schließen)
        event.accept()


def main():
    """Hauptfunktion der Anwendung"""
    app = QApplication(sys.argv)

    # Stellen sicher, dass die erforderlichen Bibliotheken verfügbar sind
    try:
        import pyautogui
        import pytesseract
    except ImportError as e:
        QMessageBox.critical(None, "Fehlende Abhängigkeit",
                             f"Bitte installiere die erforderlichen Bibliotheken: {str(e)}")
        return 1

    # Anwendung starten
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())