"""
Workflow-Tab für das Desktop-Automatisierungstool.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QLabel, QListWidget, QPushButton, QMessageBox,
                            QSplitter, QRadioButton, QDialog, QFileDialog, QComboBox,
                            QCheckBox, QDoubleSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QKeySequence, QShortcut

from automation_engine import AutomationEngine
from models import Action, ActionType
from action_editor import ActionEditor, ActionParameterChangeEvent
from constants import *


class ActionAddDialog(QDialog):
    """Dialog zum Hinzufügen einer neuen Aktion"""

    def __init__(self, parent=None, current_index=-1):
        super().__init__(parent)
        self.setWindowTitle("Neue Aktion hinzufügen")
        self.setMinimumWidth(350)

        # Layout
        layout = QVBoxLayout(self)

        # Aktionstyp-Auswahl
        layout.addWidget(QLabel("Aktionstyp:"))
        self.action_type_combo = QComboBox()
        for action_type in ActionType:
            self.action_type_combo.addItem(action_type.value)
        layout.addWidget(self.action_type_combo)

        # Position
        layout.addWidget(QLabel("Position:"))
        position_layout = QHBoxLayout()

        # Standardmäßig am Ende einfügen
        self.at_end_radio = QRadioButton("Am Ende")
        self.at_end_radio.setChecked(True)

        # Option zum Einfügen nach der aktuellen Aktion
        self.after_current_radio = QRadioButton("Nach aktueller Aktion")
        self.after_current_radio.setEnabled(current_index >= 0)

        position_layout.addWidget(self.at_end_radio)
        position_layout.addWidget(self.after_current_radio)
        layout.addLayout(position_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Hinzufügen")
        self.add_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton("Abbrechen")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def get_action_type(self) -> ActionType:
        """Gibt den ausgewählten Aktionstyp zurück"""
        action_type_str = self.action_type_combo.currentText()
        return next(t for t in ActionType if t.value == action_type_str)

    def get_insert_at_end(self) -> bool:
        """Gibt zurück, ob die Aktion am Ende eingefügt werden soll"""
        return self.at_end_radio.isChecked()


class WorkflowTab(QWidget):
    """Tab für die Bearbeitung und Verwaltung von Workflows"""

    # Signale
    workflow_changed = pyqtSignal()
    status_message = pyqtSignal(str, int)  # Nachricht, Timeout in ms

    def __init__(self, engine: AutomationEngine, parent=None):
        super().__init__(parent)
        self.engine = engine

        # Aktuelle Auswahl und Aktionseditor-Zustand
        self.current_index = -1
        self.is_modified = False
        self.updating_ui = False  # Verhindert rekursive Updates

        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        """Erstellt die Benutzeroberfläche"""
        # Hauptlayout
        layout = QVBoxLayout(self)

        # Dauerhafte Ausführungs-Optionen
        repeat_options_layout = QHBoxLayout()

        # Checkbox für Dauerhaft ausführen
        self.loop_checkbox = QCheckBox("Dauerhaft ausführen")
        self.loop_checkbox.setChecked(self.engine.loop_enabled)
        self.loop_checkbox.toggled.connect(self.on_loop_toggled)
        repeat_options_layout.addWidget(self.loop_checkbox)

        # Pause zwischen Durchläufen
        repeat_options_layout.addWidget(QLabel("Pause (s):"))
        self.loop_pause_spin = QDoubleSpinBox()
        self.loop_pause_spin.setRange(0, 60)
        self.loop_pause_spin.setSingleStep(0.5)
        self.loop_pause_spin.setValue(self.engine.loop_pause)
        self.loop_pause_spin.valueChanged.connect(self.on_loop_pause_changed)
        repeat_options_layout.addWidget(self.loop_pause_spin)

        # Abbruchtaste
        repeat_options_layout.addWidget(QLabel("Abbruchtaste:"))
        self.abort_key_combo = QComboBox()
        # Füge gängige Tasten hinzu
        for key in ["esc", "f12", "tab", "space", "pause"]:
            self.abort_key_combo.addItem(key)
        self.abort_key_combo.setCurrentText(self.engine.abort_key)
        self.abort_key_combo.currentTextChanged.connect(self.on_abort_key_changed)
        repeat_options_layout.addWidget(self.abort_key_combo)

        repeat_options_layout.addStretch()

        # Layout hinzufügen
        layout.addLayout(repeat_options_layout)

        # Splitter für linke und rechte Seite
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Linke Seite: Workflow-Liste
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.workflow_list = QListWidget()
        self.workflow_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.workflow_list.itemSelectionChanged.connect(self.on_action_selected)

        left_layout.addWidget(QLabel("Workflow-Aktionen:"))
        left_layout.addWidget(self.workflow_list)

        # Buttons für die Workflow-Verwaltung (im Raster-Layout)
        button_layout = QGridLayout()

        self.add_action_btn = QPushButton("Aktion hinzufügen")
        self.add_action_btn.clicked.connect(self.add_action)

        self.remove_action_btn = QPushButton("Entfernen")
        self.remove_action_btn.clicked.connect(self.remove_selected_action)

        self.duplicate_action_btn = QPushButton("Duplizieren")
        self.duplicate_action_btn.clicked.connect(self.duplicate_selected_action)

        self.move_up_btn = QPushButton("↑")
        self.move_up_btn.clicked.connect(self.move_action_up)

        self.move_down_btn = QPushButton("↓")
        self.move_down_btn.clicked.connect(self.move_action_down)

        button_layout.addWidget(self.add_action_btn, 0, 0, 1, 2)
        button_layout.addWidget(self.remove_action_btn, 0, 2, 1, 1)
        button_layout.addWidget(self.duplicate_action_btn, 1, 0, 1, 2)
        button_layout.addWidget(self.move_up_btn, 1, 2, 1, 1)
        button_layout.addWidget(self.move_down_btn, 1, 3, 1, 1)

        left_layout.addLayout(button_layout)

        # Rechte Seite: Aktionsdetails
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        right_layout.addWidget(QLabel("Aktionsdetails:"))

        # Aktionseditor
        self.action_editor = ActionEditor()
        self.action_editor.parameter_changed.connect(self.on_parameter_changed)
        self.action_editor.type_changed.connect(self.on_type_changed)

        right_layout.addWidget(self.action_editor)

        # Widgets zum Splitter hinzufügen
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        # Splitter-Proportionen setzen
        splitter.setSizes([300, 500])

        # Splitter zum Layout hinzufügen
        layout.addWidget(splitter)

        # UI aktualisieren
        self.refresh_workflow_list()
        self.update_button_states()

    def setup_shortcuts(self):
        """Richtet Tastaturkürzel für den Tab ein"""
        # Aktion hinzufügen
        add_shortcut = QShortcut(QKeySequence(SHORTCUT_ADD_ACTION), self)
        add_shortcut.activated.connect(self.add_action)

        # Aktion löschen
        delete_shortcut = QShortcut(QKeySequence(SHORTCUT_DELETE_ACTION), self)
        delete_shortcut.activated.connect(self.remove_selected_action)

        # Aktion duplizieren
        duplicate_shortcut = QShortcut(QKeySequence(SHORTCUT_DUPLICATE_ACTION), self)
        duplicate_shortcut.activated.connect(self.duplicate_selected_action)

        # Aktion nach oben verschieben
        move_up_shortcut = QShortcut(QKeySequence(SHORTCUT_MOVE_UP), self)
        move_up_shortcut.activated.connect(self.move_action_up)

        # Aktion nach unten verschieben
        move_down_shortcut = QShortcut(QKeySequence(SHORTCUT_MOVE_DOWN), self)
        move_down_shortcut.activated.connect(self.move_action_down)

    # Callback-Methoden für die Dauerhaft-Optionen
    def on_loop_toggled(self, checked):
        """Wird aufgerufen, wenn die Dauerhaft-Checkbox umgeschaltet wird"""
        self.engine.loop_enabled = checked

    def on_loop_pause_changed(self, value):
        """Wird aufgerufen, wenn die Pausenzeit geändert wird"""
        self.engine.loop_pause = value

    def on_abort_key_changed(self, key):
        """Wird aufgerufen, wenn die Abbruchtaste geändert wird"""
        self.engine.abort_key = key

    def refresh_workflow_list(self):
        """Aktualisiert die Workflow-Liste"""
        if self.updating_ui:
            return

        self.updating_ui = True

        # Aktuelle Auswahl speichern
        current_row = self.workflow_list.currentRow()

        self.workflow_list.clear()

        # Aktionen hinzufügen
        for i, action in enumerate(self.engine.workflow):
            item_text = f"{i+1}. {action.get_description()}"
            self.workflow_list.addItem(item_text)

        # Auswahl wiederherstellen, falls möglich
        if current_row >= 0 and current_row < self.workflow_list.count():
            self.workflow_list.setCurrentRow(current_row)
        elif self.workflow_list.count() > 0:
            self.workflow_list.setCurrentRow(0)
            # Wenn nur eine Aktion vorhanden ist, wird der itemSelectionChanged-Signal manchmal nicht ausgelöst
            # Daher manuell die Aktionsdetails aktualisieren, wenn es nur eine Aktion gibt
            if len(self.engine.workflow) == 1:
                self.current_index = 0
                self.action_editor.edit_action(self.engine.workflow[0])

        # Dauerhaft-Ausführen-Einstellungen aktualisieren
        self.update_loop_settings()

        self.updating_ui = False

        # Button-Status aktualisieren
        self.update_button_states()

    def update_button_states(self):
        """Aktualisiert den Status der Buttons basierend auf der aktuellen Auswahl"""
        has_workflow = len(self.engine.workflow) > 0
        has_selection = self.current_index >= 0
        is_first = self.current_index == 0
        is_last = self.current_index == len(self.engine.workflow) - 1

        # Buttons aktivieren/deaktivieren
        self.remove_action_btn.setEnabled(has_selection)
        self.duplicate_action_btn.setEnabled(has_selection)
        self.move_up_btn.setEnabled(has_selection and not is_first)
        self.move_down_btn.setEnabled(has_selection and not is_last)

    def on_action_selected(self):
        """Wird aufgerufen, wenn eine Aktion in der Liste ausgewählt wird"""
        if self.updating_ui:
            return

        # Index der ausgewählten Aktion
        self.current_index = self.workflow_list.currentRow()

        # Button-Status aktualisieren
        self.update_button_states()

        # Aktionseditor aktualisieren
        if self.current_index >= 0 and self.current_index < len(self.engine.workflow):
            self.action_editor.edit_action(self.engine.workflow[self.current_index])
        else:
            self.action_editor.clear_editor()

    def on_parameter_changed(self, event: ActionParameterChangeEvent):
        """
        Wird aufgerufen, wenn ein Parameter einer Aktion geändert wurde

        Args:
            event: Das Ereignisobjekt mit dem geänderten Parameter
        """
        if self.current_index < 0 or self.current_index >= len(self.engine.workflow):
            return

        # Parameter aktualisieren
        self.engine.workflow[self.current_index].params[event.param_name] = event.new_value

        # Statusmeldung anzeigen
        self.status_message.emit(
            f"Parameter '{event.param_name}' geändert: {event.old_value} -> {event.new_value}",
            STATUSBAR_TIMEOUT
        )

        # Liste aktualisieren
        self.refresh_workflow_list()

        # Workflow als geändert markieren
        self.is_modified = True
        self.workflow_changed.emit()

    def on_type_changed(self, new_type: ActionType):
        """
        Wird aufgerufen, wenn der Typ einer Aktion geändert wurde

        Args:
            new_type: Der neue Aktionstyp
        """
        if self.current_index < 0 or self.current_index >= len(self.engine.workflow):
            return

        old_action = self.engine.workflow[self.current_index]
        old_type = old_action.action_type

        # Standardparameter für den neuen Typ
        new_params = Action.get_default_params(new_type)

        # Bestehende Parameter übernehmen, wenn möglich
        for key, value in old_action.params.items():
            if key in new_params:
                new_params[key] = value

        # Neue Aktion erstellen
        new_action = Action(new_type, new_params)

        # Alte Aktion ersetzen
        self.engine.workflow[self.current_index] = new_action

        # Statusmeldung anzeigen
        self.status_message.emit(
            f"Aktionstyp geändert: {old_type.value} -> {new_type.value}",
            STATUSBAR_TIMEOUT
        )

        # Editor aktualisieren
        self.action_editor.edit_action(new_action)

        # Liste aktualisieren
        self.refresh_workflow_list()

        # Workflow als geändert markieren
        self.is_modified = True
        self.workflow_changed.emit()

    def add_action(self):
        """Öffnet den Dialog zum Hinzufügen einer neuen Aktion"""
        dialog = ActionAddDialog(self, self.current_index)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            action_type = dialog.get_action_type()

            # Standardparameter für den Aktionstyp
            params = Action.get_default_params(action_type)

            # Neue Aktion erstellen
            action = Action(action_type, params)

            # Position zum Einfügen bestimmen
            if not dialog.get_insert_at_end() and self.current_index >= 0:
                # Nach der aktuellen Aktion einfügen
                insert_index = self.current_index + 1
                self.engine.insert_action(insert_index, action)
            else:
                # Am Ende einfügen
                self.engine.add_action(action)
                insert_index = len(self.engine.workflow) - 1

            # Liste aktualisieren und neue Aktion auswählen
            self.refresh_workflow_list()
            self.workflow_list.setCurrentRow(insert_index)

            # Statusmeldung anzeigen
            self.status_message.emit(f"Aktion '{action_type.value}' hinzugefügt", STATUSBAR_TIMEOUT)

            # Workflow als geändert markieren
            self.is_modified = True
            self.workflow_changed.emit()

    def remove_selected_action(self):
        """Entfernt die ausgewählte Aktion"""
        if self.current_index < 0 or self.current_index >= len(self.engine.workflow):
            return

        # Aktionsbeschreibung für die Bestätigungsmeldung
        action_description = self.workflow_list.currentItem().text()

        # Bestätigung vom Benutzer einholen
        confirm = QMessageBox.question(
            self,
            "Aktion löschen",
            f"Möchtest du die Aktion wirklich löschen?\n\n{action_description}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            # Aktion entfernen
            self.engine.remove_action(self.current_index)

            # Liste aktualisieren
            self.refresh_workflow_list()

            # Neue Auswahl festlegen
            new_index = min(self.current_index, len(self.engine.workflow) - 1)
            if new_index >= 0:
                self.workflow_list.setCurrentRow(new_index)
            else:
                self.current_index = -1
                self.action_editor.clear_editor()

            # Statusmeldung anzeigen
            self.status_message.emit("Aktion gelöscht", STATUSBAR_TIMEOUT)

            # Workflow als geändert markieren
            self.is_modified = True
            self.workflow_changed.emit()

    def duplicate_selected_action(self):
        """Dupliziert die ausgewählte Aktion"""
        if self.current_index < 0 or self.current_index >= len(self.engine.workflow):
            return

        # Originalaktion holen
        original_action = self.engine.workflow[self.current_index]

        # Tiefe Kopie der Parameter erstellen
        new_params = dict(original_action.params)

        # Neue Aktion erstellen
        new_action = Action(original_action.action_type, new_params)

        # Nach der ausgewählten Aktion einfügen
        insert_index = self.current_index + 1
        self.engine.insert_action(insert_index, new_action)

        # Liste aktualisieren und neue Aktion auswählen
        self.refresh_workflow_list()
        self.workflow_list.setCurrentRow(insert_index)

        # Statusmeldung anzeigen
        self.status_message.emit("Aktion dupliziert", STATUSBAR_TIMEOUT)

        # Workflow als geändert markieren
        self.is_modified = True
        self.workflow_changed.emit()

    def move_action_up(self):
        """Verschiebt die ausgewählte Aktion nach oben"""
        if self.current_index <= 0 or self.current_index >= len(self.engine.workflow):
            return

        # Aktionen tauschen
        self.engine.swap_actions(self.current_index, self.current_index - 1)

        # Liste aktualisieren und Auswahl anpassen
        new_index = self.current_index - 1
        self.refresh_workflow_list()
        self.workflow_list.setCurrentRow(new_index)

        # Statusmeldung anzeigen
        self.status_message.emit("Aktion nach oben verschoben", STATUSBAR_TIMEOUT)

        # Workflow als geändert markieren
        self.is_modified = True
        self.workflow_changed.emit()

    def move_action_down(self):
        """Verschiebt die ausgewählte Aktion nach unten"""
        if (self.current_index < 0 or
            self.current_index >= len(self.engine.workflow) - 1):
            return

        # Aktionen tauschen
        self.engine.swap_actions(self.current_index, self.current_index + 1)

        # Liste aktualisieren und Auswahl anpassen
        new_index = self.current_index + 1
        self.refresh_workflow_list()
        self.workflow_list.setCurrentRow(new_index)

        # Statusmeldung anzeigen
        self.status_message.emit("Aktion nach unten verschoben", STATUSBAR_TIMEOUT)

        # Workflow als geändert markieren
        self.is_modified = True
        self.workflow_changed.emit()

    def set_modified(self, modified: bool = True):
        """Setzt den Änderungsstatus des Workflows"""
        self.is_modified = modified

    def update_loop_settings(self):
        """Aktualisiert die UI-Elemente für die Dauerhaft-Ausführen-Einstellungen"""
        # UI-Updates blockieren, um Signale zu vermeiden
        self.updating_ui = True

        # Checkbox-Status aktualisieren
        self.loop_checkbox.setChecked(self.engine.loop_enabled)

        # Pausenzeit aktualisieren
        self.loop_pause_spin.setValue(self.engine.loop_pause)

        # Abbruchtaste aktualisieren
        index = self.abort_key_combo.findText(self.engine.abort_key)
        if index >= 0:
            self.abort_key_combo.setCurrentIndex(index)

        self.updating_ui = False