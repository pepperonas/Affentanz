"""
Editor für einzelne Aktionen im Workflow.
"""

import threading
import time
import pyautogui
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                           QLabel, QSpinBox, QDoubleSpinBox, QLineEdit,
                           QComboBox, QPushButton, QDialog, QDialogButtonBox,
                           QMessageBox, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut

from models import Action, ActionType
from utils import validate_color, validate_region


class ActionParameterChangeEvent:
    """Ereignisobjekt für Parameteränderungen"""
    def __init__(self, param_name: str, old_value, new_value):
        self.param_name = param_name
        self.old_value = old_value
        self.new_value = new_value


class ActionEditor(QWidget):
    """Editor-Widget für eine einzelne Aktion"""

    # Signale
    parameter_changed = pyqtSignal(ActionParameterChangeEvent)
    type_changed = pyqtSignal(ActionType)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.action = None
        self.edit_mode = False
        self.parameter_widgets = {}

        self.main_layout = QVBoxLayout(self)
        self.form_layout = QGridLayout()

        # Platzhaltertext, wenn keine Aktion ausgewählt ist
        self.placeholder = QLabel("Wähle eine Aktion aus, um Details anzuzeigen")
        self.main_layout.addWidget(self.placeholder)

        # Timer und Status für Mausposition-Tracking
        self.tracking_timer = None
        self.tracking_active = False
        self.tracking_target_widget = None
        self.position_display_label = None
        self.tracking_screen_combo = None

        # Anfangs kein Action-Editor anzeigen
        self.clear_editor()

    def edit_action(self, action: Action):
        """
        Bereitet den Editor für die Bearbeitung einer Aktion vor

        Args:
            action: Die zu bearbeitende Aktion
        """
        # Speichere eine Kopie der Aktion, um rückgängig zu machen
        self.action = action

        # Bestehende Widgets entfernen
        self.clear_editor()

        # Edit-Modus aktivieren
        self.edit_mode = True

        # Typ-Auswahl erstellen
        type_label = QLabel("Typ:")
        self.form_layout.addWidget(type_label, 0, 0)

        type_combo = QComboBox()
        for action_type in ActionType:
            type_combo.addItem(action_type.value)
        type_combo.setCurrentText(action.action_type.value)
        type_combo.currentTextChanged.connect(self._on_type_changed)
        self.form_layout.addWidget(type_combo, 0, 1)

        # Parameter-Widgets erstellen
        self._create_parameter_widgets(action)

        # Form-Layout einfügen
        self.main_layout.addLayout(self.form_layout)

        # Button einfügen
        apply_button = QPushButton("Änderungen anwenden")
        apply_button.clicked.connect(self._apply_changes)
        self.main_layout.addWidget(apply_button)

        # Streckbaren Platz einfügen
        self.main_layout.addStretch()

        # Tastaturkürzel für Enter bei aktivem Tracking einrichten
        self.enter_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        self.enter_shortcut.activated.connect(self.apply_tracked_position)
        self.enter_shortcut.setEnabled(False)

    def clear_editor(self):
        """Leert den Editor und zeigt den Platzhaltertext an"""
        # Bestehende Widgets entfernen
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    subitem = item.layout().takeAt(0)
                    if subitem.widget():
                        subitem.widget().deleteLater()

        # Parameter-Widgets zurücksetzen
        self.parameter_widgets = {}

        # Edit-Modus zurücksetzen
        self.edit_mode = False

        # Tracking beenden, falls aktiv
        self.stop_position_tracking()

        # Neues Platzhalter-Label erstellen und anzeigen
        self.placeholder = QLabel("Wähle eine Aktion aus, um Details anzuzeigen")
        self.main_layout.addWidget(self.placeholder)

    def get_available_screens(self):
        """Gibt eine Liste der verfügbaren Bildschirme zurück"""
        screens = []
        for i, screen in enumerate(QApplication.screens()):
            geometry = screen.geometry()
            screens.append({
                "id": i,
                "name": screen.name(),
                "width": geometry.width(),
                "height": geometry.height(),
                "x": geometry.x(),
                "y": geometry.y()
            })
        return screens

    def _create_parameter_widgets(self, action: Action):
        """
        Erstellt die Widgets für die Parameter der Aktion

        Args:
            action: Die Aktion, deren Parameter bearbeitet werden sollen
        """
        row = 1  # Row 0 ist für den Typ reserviert

        if action.action_type in [ActionType.MOUSE_MOVE, ActionType.MOUSE_CLICK,
                                ActionType.MOUSE_DOUBLE_CLICK, ActionType.MOUSE_RIGHT_CLICK]:
            # Bildschirm-Auswahl
            self.form_layout.addWidget(QLabel("Bildschirm:"), row, 0)
            screen_combo = QComboBox()
            for screen in self.get_available_screens():
                screen_combo.addItem(
                    f"Bildschirm {screen['id']} ({screen['width']}×{screen['height']})"
                )
            screen_combo.setCurrentIndex(action.params.get("screen_id", 0))
            self.form_layout.addWidget(screen_combo, row, 1)
            self.parameter_widgets["screen_id"] = screen_combo
            row += 1

            # X-Koordinate
            self.form_layout.addWidget(QLabel("X:"), row, 0)
            x_spinbox = QSpinBox()
            x_spinbox.setRange(0, 9999)
            x_spinbox.setValue(action.params.get("x", 0))
            self.form_layout.addWidget(x_spinbox, row, 1)
            self.parameter_widgets["x"] = x_spinbox
            row += 1

            # Y-Koordinate
            self.form_layout.addWidget(QLabel("Y:"), row, 0)
            y_spinbox = QSpinBox()
            y_spinbox.setRange(0, 9999)
            y_spinbox.setValue(action.params.get("y", 0))
            self.form_layout.addWidget(y_spinbox, row, 1)
            self.parameter_widgets["y"] = y_spinbox
            row += 1

            # Mausposition-Display für Live-Tracking
            self.position_display_label = QLabel("Aktuelle Mausposition: ---, ---")
            self.form_layout.addWidget(self.position_display_label, row, 0, 1, 2)
            row += 1

            # Position loggen Button
            track_position_btn = QPushButton("Mausposition loggen (Enter = übernehmen)")
            track_position_btn.clicked.connect(
                lambda: self.toggle_position_tracking(x_spinbox, y_spinbox, screen_combo)
            )
            self.form_layout.addWidget(track_position_btn, row, 0, 1, 2)
            row += 1

            # Test-Button für Mausposition
            test_position_btn = QPushButton("Position testen")
            test_position_btn.clicked.connect(
                lambda: self._test_mouse_position(x_spinbox.value(), y_spinbox.value(),
                                              screen_combo.currentIndex())
            )
            self.form_layout.addWidget(test_position_btn, row, 0, 1, 2)
            row += 1

            # Maustaste (nur für Klick-Aktionen)
            if action.action_type != ActionType.MOUSE_MOVE:
                self.form_layout.addWidget(QLabel("Taste:"), row, 0)
                button_combo = QComboBox()
                button_combo.addItems(["left", "middle", "right"])
                button_combo.setCurrentText(action.params.get("button", "left"))
                self.form_layout.addWidget(button_combo, row, 1)
                self.parameter_widgets["button"] = button_combo
                row += 1

            # Dauer
            self.form_layout.addWidget(QLabel("Dauer (s):"), row, 0)
            duration_spinbox = QDoubleSpinBox()
            duration_spinbox.setRange(0, 10)
            duration_spinbox.setSingleStep(0.1)
            duration_spinbox.setDecimals(1)
            duration_spinbox.setValue(action.params.get("duration", 0.1))
            self.form_layout.addWidget(duration_spinbox, row, 1)
            self.parameter_widgets["duration"] = duration_spinbox
            row += 1

        elif action.action_type == ActionType.MOUSE_DRAG:
            # Bildschirm-Auswahl
            self.form_layout.addWidget(QLabel("Bildschirm:"), row, 0)
            screen_combo = QComboBox()
            for screen in self.get_available_screens():
                screen_combo.addItem(
                    f"Bildschirm {screen['id']} ({screen['width']}×{screen['height']})"
                )
            screen_combo.setCurrentIndex(action.params.get("screen_id", 0))
            self.form_layout.addWidget(screen_combo, row, 1)
            self.parameter_widgets["screen_id"] = screen_combo
            row += 1

            # Start X-Koordinate
            self.form_layout.addWidget(QLabel("Start X:"), row, 0)
            start_x_spinbox = QSpinBox()
            start_x_spinbox.setRange(0, 9999)
            start_x_spinbox.setValue(action.params.get("start_x", 0))
            self.form_layout.addWidget(start_x_spinbox, row, 1)
            self.parameter_widgets["start_x"] = start_x_spinbox
            row += 1

            # Start Y-Koordinate
            self.form_layout.addWidget(QLabel("Start Y:"), row, 0)
            start_y_spinbox = QSpinBox()
            start_y_spinbox.setRange(0, 9999)
            start_y_spinbox.setValue(action.params.get("start_y", 0))
            self.form_layout.addWidget(start_y_spinbox, row, 1)
            self.parameter_widgets["start_y"] = start_y_spinbox
            row += 1

            # Mausposition-Display für Live-Tracking
            self.position_display_label = QLabel("Aktuelle Mausposition: ---, ---")
            self.form_layout.addWidget(self.position_display_label, row, 0, 1, 2)
            row += 1

            # Start-Position loggen Button
            track_start_position_btn = QPushButton("Start-Position loggen (Enter = übernehmen)")
            track_start_position_btn.clicked.connect(
                lambda: self.toggle_position_tracking(start_x_spinbox, start_y_spinbox, screen_combo)
            )
            self.form_layout.addWidget(track_start_position_btn, row, 0, 1, 2)
            row += 1

            # Test-Button für Start-Position
            test_start_btn = QPushButton("Start-Position testen")
            test_start_btn.clicked.connect(
                lambda: self._test_mouse_position(start_x_spinbox.value(), start_y_spinbox.value(),
                                              screen_combo.currentIndex())
            )
            self.form_layout.addWidget(test_start_btn, row, 0, 1, 2)
            row += 1

            # End X-Koordinate
            self.form_layout.addWidget(QLabel("End X:"), row, 0)
            end_x_spinbox = QSpinBox()
            end_x_spinbox.setRange(0, 9999)
            end_x_spinbox.setValue(action.params.get("end_x", 0))
            self.form_layout.addWidget(end_x_spinbox, row, 1)
            self.parameter_widgets["end_x"] = end_x_spinbox
            row += 1

            # End Y-Koordinate
            self.form_layout.addWidget(QLabel("End Y:"), row, 0)
            end_y_spinbox = QSpinBox()
            end_y_spinbox.setRange(0, 9999)
            end_y_spinbox.setValue(action.params.get("end_y", 0))
            self.form_layout.addWidget(end_y_spinbox, row, 1)
            self.parameter_widgets["end_y"] = end_y_spinbox
            row += 1

            # End-Position loggen Button
            track_end_position_btn = QPushButton("End-Position loggen (Enter = übernehmen)")
            track_end_position_btn.clicked.connect(
                lambda: self.toggle_position_tracking(end_x_spinbox, end_y_spinbox, screen_combo)
            )
            self.form_layout.addWidget(track_end_position_btn, row, 0, 1, 2)
            row += 1

            # Test-Button für End-Position
            test_end_btn = QPushButton("End-Position testen")
            test_end_btn.clicked.connect(
                lambda: self._test_mouse_position(end_x_spinbox.value(), end_y_spinbox.value(),
                                              screen_combo.currentIndex())
            )
            self.form_layout.addWidget(test_end_btn, row, 0, 1, 2)
            row += 1

            # Maustaste
            self.form_layout.addWidget(QLabel("Taste:"), row, 0)
            button_combo = QComboBox()
            button_combo.addItems(["left", "middle", "right"])
            button_combo.setCurrentText(action.params.get("button", "left"))
            self.form_layout.addWidget(button_combo, row, 1)
            self.parameter_widgets["button"] = button_combo
            row += 1

            # Dauer
            self.form_layout.addWidget(QLabel("Dauer (s):"), row, 0)
            duration_spinbox = QDoubleSpinBox()
            duration_spinbox.setRange(0, 10)
            duration_spinbox.setSingleStep(0.1)
            duration_spinbox.setDecimals(1)
            duration_spinbox.setValue(action.params.get("duration", 0.5))
            self.form_layout.addWidget(duration_spinbox, row, 1)
            self.parameter_widgets["duration"] = duration_spinbox
            row += 1

        elif action.action_type == ActionType.KEY_PRESS:
            # Taste
            self.form_layout.addWidget(QLabel("Taste:"), row, 0)
            key_edit = QLineEdit(action.params.get("key", "enter"))
            self.form_layout.addWidget(key_edit, row, 1)
            self.parameter_widgets["key"] = key_edit
            row += 1

        elif action.action_type == ActionType.KEY_COMBO:
            # Tasten (als kommaseparierte Liste)
            self.form_layout.addWidget(QLabel("Tasten (mit Komma getrennt):"), row, 0)
            keys_edit = QLineEdit(",".join(action.params.get("keys", ["ctrl", "c"])))
            self.form_layout.addWidget(keys_edit, row, 1)
            self.parameter_widgets["keys"] = keys_edit
            row += 1

        elif action.action_type == ActionType.TEXT_WRITE:
            # Text
            self.form_layout.addWidget(QLabel("Text:"), row, 0)
            text_edit = QLineEdit(action.params.get("text", "Beispieltext"))
            self.form_layout.addWidget(text_edit, row, 1)
            self.parameter_widgets["text"] = text_edit
            row += 1

            # Verzögerung zwischen Tastendrücken
            self.form_layout.addWidget(QLabel("Verzögerung (s):"), row, 0)
            interval_spinbox = QDoubleSpinBox()
            interval_spinbox.setRange(0, 1)
            interval_spinbox.setSingleStep(0.01)
            interval_spinbox.setDecimals(2)
            interval_spinbox.setValue(action.params.get("interval", 0))
            self.form_layout.addWidget(interval_spinbox, row, 1)
            self.parameter_widgets["interval"] = interval_spinbox
            row += 1

        elif action.action_type == ActionType.WAIT:
            # Wartezeit in Sekunden
            self.form_layout.addWidget(QLabel("Sekunden:"), row, 0)
            seconds_spinbox = QDoubleSpinBox()
            seconds_spinbox.setRange(0, 600)
            seconds_spinbox.setSingleStep(0.5)
            seconds_spinbox.setDecimals(1)
            seconds_spinbox.setValue(action.params.get("seconds", 1))
            self.form_layout.addWidget(seconds_spinbox, row, 1)
            self.parameter_widgets["seconds"] = seconds_spinbox
            row += 1

        elif action.action_type == ActionType.WAIT_FOR_COLOR:
            # Bildschirm-Auswahl
            self.form_layout.addWidget(QLabel("Bildschirm:"), row, 0)
            screen_combo = QComboBox()
            for screen in self.get_available_screens():
                screen_combo.addItem(
                    f"Bildschirm {screen['id']} ({screen['width']}×{screen['height']})"
                )
            screen_combo.setCurrentIndex(action.params.get("screen_id", 0))
            self.form_layout.addWidget(screen_combo, row, 1)
            self.parameter_widgets["screen_id"] = screen_combo
            row += 1

            # X-Koordinate
            self.form_layout.addWidget(QLabel("X:"), row, 0)
            x_spinbox = QSpinBox()
            x_spinbox.setRange(0, 9999)
            x_spinbox.setValue(action.params.get("x", 0))
            self.form_layout.addWidget(x_spinbox, row, 1)
            self.parameter_widgets["x"] = x_spinbox
            row += 1

            # Y-Koordinate
            self.form_layout.addWidget(QLabel("Y:"), row, 0)
            y_spinbox = QSpinBox()
            y_spinbox.setRange(0, 9999)
            y_spinbox.setValue(action.params.get("y", 0))
            self.form_layout.addWidget(y_spinbox, row, 1)
            self.parameter_widgets["y"] = y_spinbox
            row += 1

            # Mausposition-Display für Live-Tracking
            self.position_display_label = QLabel("Aktuelle Mausposition: ---, ---")
            self.form_layout.addWidget(self.position_display_label, row, 0, 1, 2)
            row += 1

            # Position loggen Button
            track_position_btn = QPushButton("Mausposition loggen (Enter = übernehmen)")
            track_position_btn.clicked.connect(
                lambda: self.toggle_position_tracking(x_spinbox, y_spinbox, screen_combo)
            )
            self.form_layout.addWidget(track_position_btn, row, 0, 1, 2)
            row += 1

            # Test-Button für Mausposition
            test_position_btn = QPushButton("Position testen")
            test_position_btn.clicked.connect(
                lambda: self._test_mouse_position(x_spinbox.value(), y_spinbox.value(),
                                              screen_combo.currentIndex())
            )
            self.form_layout.addWidget(test_position_btn, row, 0, 1, 2)
            row += 1

            # Farbe
            self.form_layout.addWidget(QLabel("Farbe (R,G,B):"), row, 0)
            color = action.params.get("color", [255, 0, 0])
            color_edit = QLineEdit(",".join(map(str, color)))
            self.form_layout.addWidget(color_edit, row, 1)

            # Farbe auswählen-Button
            pick_color_btn = QPushButton("Auswählen")
            pick_color_btn.clicked.connect(lambda: self._pick_color(color_edit))
            self.form_layout.addWidget(pick_color_btn, row, 2)

            self.parameter_widgets["color"] = color_edit
            row += 1

            # Toleranz
            self.form_layout.addWidget(QLabel("Toleranz:"), row, 0)
            tolerance_spinbox = QSpinBox()
            tolerance_spinbox.setRange(0, 100)
            tolerance_spinbox.setValue(action.params.get("tolerance", 10))
            self.form_layout.addWidget(tolerance_spinbox, row, 1)
            self.parameter_widgets["tolerance"] = tolerance_spinbox
            row += 1

            # Timeout
            self.form_layout.addWidget(QLabel("Timeout (s):"), row, 0)
            timeout_spinbox = QSpinBox()
            timeout_spinbox.setRange(1, 300)
            timeout_spinbox.setValue(action.params.get("timeout", 10))
            self.form_layout.addWidget(timeout_spinbox, row, 1)
            self.parameter_widgets["timeout"] = timeout_spinbox
            row += 1

        elif action.action_type == ActionType.WAIT_FOR_TEXT:
            # Bildschirm-Auswahl
            self.form_layout.addWidget(QLabel("Bildschirm:"), row, 0)
            screen_combo = QComboBox()
            for screen in self.get_available_screens():
                screen_combo.addItem(
                    f"Bildschirm {screen['id']} ({screen['width']}×{screen['height']})"
                )
            screen_combo.setCurrentIndex(action.params.get("screen_id", 0))
            self.form_layout.addWidget(screen_combo, row, 1)
            self.parameter_widgets["screen_id"] = screen_combo
            row += 1

            # Region
            self.form_layout.addWidget(QLabel("Region [x,y,breite,höhe]:"), row, 0)
            region = action.params.get("region", [0, 0, 200, 100])
            region_edit = QLineEdit(",".join(map(str, region)))
            self.form_layout.addWidget(region_edit, row, 1)

            # Region auswählen-Button
            pick_region_btn = QPushButton("Auswählen")
            pick_region_btn.clicked.connect(lambda: self._pick_region(region_edit, screen_combo.currentIndex()))
            self.form_layout.addWidget(pick_region_btn, row, 2)

            self.parameter_widgets["region"] = region_edit
            row += 1

            # Test-Button für obere linke Ecke der Region
            if len(region) >= 2:
                test_region_btn = QPushButton("Region-Position testen")
                test_region_btn.clicked.connect(
                    lambda: self._test_mouse_position(region[0], region[1], screen_combo.currentIndex())
                )
                self.form_layout.addWidget(test_region_btn, row, 0, 1, 2)
                row += 1

            # Text
            self.form_layout.addWidget(QLabel("Text:"), row, 0)
            text_edit = QLineEdit(action.params.get("text", "Beispieltext"))
            self.form_layout.addWidget(text_edit, row, 1)
            self.parameter_widgets["text"] = text_edit
            row += 1

            # Timeout
            self.form_layout.addWidget(QLabel("Timeout (s):"), row, 0)
            timeout_spinbox = QSpinBox()
            timeout_spinbox.setRange(1, 300)
            timeout_spinbox.setValue(action.params.get("timeout", 10))
            self.form_layout.addWidget(timeout_spinbox, row, 1)
            self.parameter_widgets["timeout"] = timeout_spinbox
            row += 1

    def _on_type_changed(self, new_type_str: str):
        """
        Wird aufgerufen, wenn der Benutzer den Aktionstyp ändert

        Args:
            new_type_str: Der neue Aktionstyp als String
        """
        if not self.edit_mode or not self.action:
            return

        # Nur fortfahren, wenn sich der Typ tatsächlich geändert hat
        new_type = next((t for t in ActionType if t.value == new_type_str), None)
        if new_type and new_type != self.action.action_type:
            # Bestätigungsdialog anzeigen
            dialog = QDialog(self)
            dialog.setWindowTitle("Aktionstyp ändern")
            dialog_layout = QVBoxLayout(dialog)

            message = QLabel(f"Möchtest du den Aktionstyp wirklich ändern? "
                           f"Von '{self.action.action_type.value}' zu '{new_type.value}'?\n\n"
                           f"Hinweis: Einige Parameter könnten verloren gehen.")
            message.setWordWrap(True)
            dialog_layout.addWidget(message)

            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            dialog_layout.addWidget(button_box)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.type_changed.emit(new_type)

    def _apply_changes(self):
        """Sammelt die Änderungen aus den Widgets und gibt sie weiter"""
        if not self.edit_mode or not self.action:
            return

        for param_name, widget in self.parameter_widgets.items():
            if param_name in self.action.params:
                old_value = self.action.params[param_name]

                if isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
                    new_value = widget.value()
                elif isinstance(widget, QComboBox):
                    if param_name == "screen_id":
                        new_value = widget.currentIndex()  # Speichere den Index, nicht den Text
                    else:
                        new_value = widget.currentText()
                elif isinstance(widget, QLineEdit):
                    # Spezielle Behandlung für bestimmte Parameter
                    if param_name == "keys":
                        new_value = [k.strip() for k in widget.text().split(",")]
                    elif param_name == "color":
                        valid, color = validate_color(widget.text())
                        if valid:
                            new_value = color
                        else:
                            continue  # Ungültige Farbe, überspringen
                    elif param_name == "region":
                        valid, region = validate_region(widget.text())
                        if valid:
                            new_value = region
                        else:
                            continue  # Ungültige Region, überspringen
                    else:
                        new_value = widget.text()
                else:
                    continue  # Unbekannter Widget-Typ

                if new_value != old_value:
                    # Parameteränderung senden
                    self.parameter_changed.emit(
                        ActionParameterChangeEvent(param_name, old_value, new_value)
                    )

    def toggle_position_tracking(self, x_widget, y_widget, screen_combo=None):
        """
        Startet oder stoppt die Verfolgung der Mausposition

        Args:
            x_widget: Widget für die X-Koordinate
            y_widget: Widget für die Y-Koordinate
            screen_combo: ComboBox mit der Bildschirmauswahl
        """
        if self.tracking_active:
            self.stop_position_tracking()
        else:
            self.start_position_tracking(x_widget, y_widget, screen_combo)

    def start_position_tracking(self, x_widget, y_widget, screen_combo=None):
        """
        Startet die Verfolgung der Mausposition

        Args:
            x_widget: Widget für die X-Koordinate
            y_widget: Widget für die Y-Koordinate
            screen_combo: ComboBox mit der Bildschirmauswahl
        """
        # Tracking beenden, falls bereits aktiv
        if self.tracking_active:
            self.stop_position_tracking()

        # Tracking-Status setzen
        self.tracking_active = True
        self.tracking_target_widget = (x_widget, y_widget)
        self.tracking_screen_combo = screen_combo

        # Shortcut aktivieren
        if hasattr(self, 'enter_shortcut'):
            self.enter_shortcut.setEnabled(True)

        # Timer für Mausverfolgung starten
        self.tracking_timer = QTimer()
        self.tracking_timer.timeout.connect(self.update_mouse_position)
        self.tracking_timer.start(50)  # Alle 50 ms aktualisieren

        # Status-Label aktualisieren
        if self.position_display_label:
            self.position_display_label.setStyleSheet("color: #4CAF50; font-weight: bold;")  # Grün

    def stop_position_tracking(self):
        """Beendet die Verfolgung der Mausposition"""
        if not self.tracking_active:
            return

        # Timer stoppen
        if self.tracking_timer:
            self.tracking_timer.stop()
            self.tracking_timer = None

        # Tracking-Status zurücksetzen
        self.tracking_active = False
        self.tracking_target_widget = None

        # Shortcut deaktivieren
        if hasattr(self, 'enter_shortcut'):
            self.enter_shortcut.setEnabled(False)

        # Status-Label zurücksetzen
        if self.position_display_label:
            self.position_display_label.setStyleSheet("")

    def update_mouse_position(self):
        """Aktualisiert das Label mit der aktuellen Mausposition"""
        if not self.tracking_active or not self.position_display_label:
            return

        # Aktuelle globale Mausposition abrufen
        global_pos = pyautogui.position()

        # Wenn wir einen Bildschirm-Selektor haben, die relativen Koordinaten berechnen
        screen_id = 0
        if self.tracking_screen_combo:
            screen_id = self.tracking_screen_combo.currentIndex()

        # Bildschirminformationen holen
        screens = self.get_available_screens()
        if 0 <= screen_id < len(screens):
            screen = screens[screen_id]
            # Relative Position zum ausgewählten Bildschirm berechnen
            rel_x = global_pos[0] - screen["x"]
            rel_y = global_pos[1] - screen["y"]

            # Display aktualisieren mit relativen Koordinaten
            self.position_display_label.setText(
                f"Position auf Bildschirm {screen_id}: {rel_x}, {rel_y}"
            )
        else:
            # Fallback auf absolute Koordinaten
            self.position_display_label.setText(f"Globale Position: {global_pos[0]}, {global_pos[1]}")

    def apply_tracked_position(self):
        """Übernimmt die aktuelle Mausposition in die Zielfelder"""
        if not self.tracking_active or not self.tracking_target_widget:
            return

        # Aktuelle globale Mausposition abrufen
        global_pos = pyautogui.position()

        # Bildschirm-ID für die Konvertierung holen
        screen_id = 0
        if self.tracking_screen_combo:
            screen_id = self.tracking_screen_combo.currentIndex()

        # Bildschirminformationen holen
        screens = self.get_available_screens()
        if 0 <= screen_id < len(screens):
            screen = screens[screen_id]
            # Relative Position zum ausgewählten Bildschirm berechnen
            rel_x = global_pos[0] - screen["x"]
            rel_y = global_pos[1] - screen["y"]

            # Werte in die Felder eintragen (relative Koordinaten)
            x_widget, y_widget = self.tracking_target_widget
            x_widget.setValue(rel_x)
            y_widget.setValue(rel_y)

            # Tracking beenden
            self.stop_position_tracking()

            # Bestätigungsnachricht anzeigen
            if self.position_display_label:
                self.position_display_label.setText(
                    f"Position übernommen: {rel_x}, {rel_y} (Bildschirm {screen_id})"
                )
        else:
            # Fallback auf absolute Koordinaten
            x_widget, y_widget = self.tracking_target_widget
            x_widget.setValue(global_pos[0])
            y_widget.setValue(global_pos[1])

            # Tracking beenden
            self.stop_position_tracking()

            # Bestätigungsnachricht anzeigen
            if self.position_display_label:
                self.position_display_label.setText(
                    f"Position übernommen: {global_pos[0]}, {global_pos[1]}"
                )

    def keyPressEvent(self, event):
        """Behandelt Tastatureingaben"""
        # Enter-Taste abfangen, wenn Tracking aktiv
        if self.tracking_active and event.key() == Qt.Key.Key_Return:
            self.apply_tracked_position()
        else:
            super().keyPressEvent(event)

    def _test_mouse_position(self, x: int, y: int, screen_id: int = 0):
        """
        Bewegt die Maus zur angegebenen Position, um sie zu testen

        Args:
            x: X-Koordinate (relativ zum Bildschirm)
            y: Y-Koordinate (relativ zum Bildschirm)
            screen_id: ID des Bildschirms
        """
        # Aktuelle Mausposition speichern
        original_pos = pyautogui.position()

        try:
            # Bildschirmoffset für absolute Koordinaten hinzufügen
            screens = self.get_available_screens()
            abs_x, abs_y = x, y

            if 0 <= screen_id < len(screens):
                screen = screens[screen_id]
                abs_x = screen["x"] + x
                abs_y = screen["y"] + y

            # Maus zur gewünschten Position bewegen
            pyautogui.moveTo(abs_x, abs_y, duration=0.2)

            # Funktion, um die Maus nach einer Verzögerung zurückzubewegen
            def move_back():
                time.sleep(1.5)  # 1,5 Sekunden warten
                pyautogui.moveTo(original_pos[0], original_pos[1], duration=0.2)

            # Thread starten, um die Maus zurückzubewegen
            thread = threading.Thread(target=move_back)
            thread.daemon = True  # Thread als Daemon markieren, damit er das Programm nicht blockiert
            thread.start()

        except Exception as e:
            QMessageBox.warning(self, "Positionstest fehlgeschlagen", f"Fehler beim Testen der Position: {str(e)}")

    def _pick_color(self, color_edit: QLineEdit):
        """
        Öffnet den Farbwähler und setzt die ausgewählte Farbe in das Eingabefeld

        Args:
            color_edit: Das Eingabefeld für die Farbe
        """
        # Placeholder, tatsächliche Implementierung würde den ColorPicker verwenden
        pass

    def _pick_region(self, region_edit: QLineEdit, screen_id: int = 0):
        """
        Öffnet den Regionswähler und setzt die ausgewählte Region in das Eingabefeld

        Args:
            region_edit: Das Eingabefeld für die Region
            screen_id: ID des Bildschirms
        """
        # Placeholder, tatsächliche Implementierung würde den RegionSelector verwenden
        pass