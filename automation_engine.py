"""
Hauptlogik für die Automatisierung von Benutzerinteraktionen.
Enthält die AutomationEngine Klasse, die die Ausführung von Workflows handhabt.
"""

import time
import json
import pyautogui
import pytesseract
from PIL import Image, ImageGrab
from PyQt6.QtWidgets import QApplication
from typing import List, Dict, Any, Optional, Tuple, Callable

from models import Action, ActionType


class AutomationEngine:
    """Hauptklasse für die Ausführung von Automatisierungsworkflows"""

    def __init__(self):
        """Initialisiert die AutomationEngine"""
        self.workflow: List[Action] = []
        self.is_recording = False
        self.is_playing = False
        self.loop_enabled = False       # Neues Attribut für Dauerhafte Ausführung
        self.loop_pause = 1.0          # Pause zwischen Wiederholungen in Sekunden
        self.abort_key = "esc"         # Taste zum Abbrechen der Dauerausführung
        self.screen_info = self._get_screen_info()

    def _get_screen_info(self) -> Dict[str, Any]:
        """Erfasst Informationen über alle angeschlossenen Bildschirme"""
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
        return {"screens": screens}

    def start_recording(self):
        """Startet die Aufzeichnung von Benutzeraktionen"""
        self.is_recording = True
        # Wir löschen nicht den bestehenden Workflow hier, um Erweiterungen zu ermöglichen

    def stop_recording(self):
        """Stoppt die Aufzeichnung von Benutzeraktionen"""
        self.is_recording = False

    def add_action(self, action: Action):
        """Fügt eine Aktion zum aktuellen Workflow hinzu"""
        self.workflow.append(action)

    def insert_action(self, index: int, action: Action):
        """Fügt eine Aktion an einer bestimmten Position in den Workflow ein"""
        if 0 <= index <= len(self.workflow):
            self.workflow.insert(index, action)
        else:
            # Bei ungültigem Index am Ende einfügen
            self.workflow.append(action)

    def remove_action(self, index: int):
        """Entfernt eine Aktion aus dem Workflow"""
        if 0 <= index < len(self.workflow):
            self.workflow.pop(index)

    def swap_actions(self, index1: int, index2: int) -> bool:
        """Tauscht zwei Aktionen im Workflow aus"""
        if 0 <= index1 < len(self.workflow) and 0 <= index2 < len(self.workflow):
            self.workflow[index1], self.workflow[index2] = self.workflow[index2], self.workflow[index1]
            return True
        return False

    def clear_workflow(self):
        """Löscht den gesamten Workflow"""
        self.workflow = []

    def save_workflow(self, filename: str):
        """Speichert den Workflow als JSON-Datei"""
        data = {
            "version": "1.0",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "settings": {
                "loop_enabled": self.loop_enabled,
                "loop_pause": self.loop_pause,
                "abort_key": self.abort_key
            },
            "actions": [action.to_dict() for action in self.workflow]
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

    def load_workflow(self, filename: str) -> int:
        """
        Lädt einen Workflow aus einer JSON-Datei

        Returns:
            int: Anzahl der geladenen Aktionen
        """
        with open(filename, 'r') as f:
            data = json.load(f)

        # Lade Workflow-Einstellungen, falls vorhanden
        if "settings" in data:
            settings = data["settings"]
            self.loop_enabled = settings.get("loop_enabled", False)
            self.loop_pause = settings.get("loop_pause", 1.0)
            self.abort_key = settings.get("abort_key", "esc")

        # Lade Aktionen
        self.workflow = [Action.from_dict(action_data) for action_data in data["actions"]]
        return len(self.workflow)

    def play_workflow(self, callback: Optional[Callable[[int], None]] = None):
        """
        Führt den aktuellen Workflow aus

        Args:
            callback: Optional. Funktion, die nach jeder Aktion mit dem Index aufgerufen wird
        """
        if self.is_playing or not self.workflow:
            return

        self.is_playing = True

        try:
            # Ausführungsschleife
            while self.is_playing:
                for i, action in enumerate(self.workflow):
                    if not self.is_playing:
                        break

                    self._execute_action(action)

                    if callback:
                        callback(i)

                    # Prüfen ob Abbruchtaste gedrückt wurde
                    if self._check_abort_key():
                        self.is_playing = False
                        break

                # Wenn Loop nicht aktiviert ist oder abgebrochen wurde, beenden
                if not self.loop_enabled or not self.is_playing:
                    break

                # Pause zwischen den Durchläufen
                if self.loop_pause > 0:
                    time.sleep(self.loop_pause)

                    # Während der Pause noch einmal prüfen, ob abgebrochen wurde
                    if self._check_abort_key():
                        self.is_playing = False
                        break
        except Exception as e:
            print(f"Fehler bei Workflow-Ausführung: {e}")
        finally:
            self.is_playing = False

    def _check_abort_key(self) -> bool:
        """Prüft, ob die Abbruchtaste gedrückt wurde"""
        try:
            return pyautogui.isKeyDown(self.abort_key)
        except:
            return False

    def stop_playback(self):
        """Stoppt die Ausführung des Workflows"""
        self.is_playing = False

    def _get_absolute_coordinates(self, x: int, y: int, screen_id: int = 0) -> Tuple[int, int]:
        """
        Berechnet absolute Bildschirmkoordinaten aus relativen Koordinaten eines Bildschirms

        Args:
            x: Relative X-Koordinate auf dem Bildschirm
            y: Relative Y-Koordinate auf dem Bildschirm
            screen_id: ID des Bildschirms

        Returns:
            Tuple[int, int]: Absolute Bildschirmkoordinaten (x, y)
        """
        screen_offset_x, screen_offset_y = 0, 0

        if 0 <= screen_id < len(self.screen_info["screens"]):
            screen = self.screen_info["screens"][screen_id]
            screen_offset_x = screen["x"]
            screen_offset_y = screen["y"]

        return (screen_offset_x + x, screen_offset_y + y)

    def _execute_action(self, action: Action):
        """Führt eine einzelne Aktion aus"""
        try:
            # Screen ID abrufen, falls vorhanden
            screen_id = action.params.get("screen_id", 0)

            if action.action_type == ActionType.MOUSE_MOVE:
                # Absolute Position berechnen
                abs_x, abs_y = self._get_absolute_coordinates(
                    action.params["x"], action.params["y"], screen_id
                )

                pyautogui.moveTo(abs_x, abs_y, duration=action.params.get("duration", 0.1))

            elif action.action_type == ActionType.MOUSE_CLICK:
                # Absolute Position berechnen
                abs_x, abs_y = self._get_absolute_coordinates(
                    action.params["x"], action.params["y"], screen_id
                )

                pyautogui.click(abs_x, abs_y,
                             button=action.params.get("button", "left"),
                             duration=action.params.get("duration", 0.1))

            elif action.action_type == ActionType.MOUSE_DOUBLE_CLICK:
                # Absolute Position berechnen
                abs_x, abs_y = self._get_absolute_coordinates(
                    action.params["x"], action.params["y"], screen_id
                )

                pyautogui.doubleClick(abs_x, abs_y,
                                   button=action.params.get("button", "left"),
                                   duration=action.params.get("duration", 0.1))

            elif action.action_type == ActionType.MOUSE_RIGHT_CLICK:
                # Absolute Position berechnen
                abs_x, abs_y = self._get_absolute_coordinates(
                    action.params["x"], action.params["y"], screen_id
                )

                pyautogui.rightClick(abs_x, abs_y,
                                  duration=action.params.get("duration", 0.1))

            elif action.action_type == ActionType.MOUSE_DRAG:
                # Absolute Positionen berechnen
                abs_start_x, abs_start_y = self._get_absolute_coordinates(
                    action.params.get("start_x", 0),
                    action.params.get("start_y", 0),
                    screen_id
                )

                abs_end_x, abs_end_y = self._get_absolute_coordinates(
                    action.params["end_x"],
                    action.params["end_y"],
                    screen_id
                )

                # Erst zur Startposition bewegen, dann ziehen
                pyautogui.moveTo(abs_start_x, abs_start_y,
                              duration=action.params.get("duration", 0.1) / 2)

                # Jetzt zur Endposition ziehen
                pyautogui.dragTo(abs_end_x, abs_end_y,
                              button=action.params.get("button", "left"),
                              duration=action.params.get("duration", 0.5),
                              mouseDownUp=True)

            elif action.action_type == ActionType.KEY_PRESS:
                pyautogui.press(action.params["key"])

            elif action.action_type == ActionType.KEY_COMBO:
                pyautogui.hotkey(*action.params["keys"])

            elif action.action_type == ActionType.TEXT_WRITE:
                pyautogui.write(action.params["text"], interval=action.params.get("interval", 0))

            elif action.action_type == ActionType.WAIT:
                time.sleep(action.params["seconds"])

            elif action.action_type == ActionType.WAIT_FOR_COLOR:
                # Absolute Position für den Farbvergleich berechnen
                abs_x, abs_y = self._get_absolute_coordinates(
                    action.params["x"], action.params["y"], screen_id
                )

                self._wait_for_color(
                    abs_x,
                    abs_y,
                    action.params["color"],
                    action.params.get("tolerance", 10),
                    action.params.get("timeout", 10)
                )

            elif action.action_type == ActionType.WAIT_FOR_TEXT:
                # Absolute Regionkoordinaten berechnen
                region = action.params["region"]
                if len(region) >= 4:
                    abs_x, abs_y = self._get_absolute_coordinates(
                        region[0], region[1], screen_id
                    )
                    abs_region = [abs_x, abs_y, region[2], region[3]]

                    self._wait_for_text(
                        abs_region,
                        action.params["text"],
                        action.params.get("timeout", 10)
                    )
                else:
                    raise ValueError("Region muss 4 Werte enthalten: [x, y, width, height]")

        except pyautogui.FailSafeException:
            # Spezieller Umgang mit dem PyAutoGUI-Failsafe
            print(f"Fehler bei Ausführung von Aktion {action.action_type}: PyAutoGUI-Failsafe wurde ausgelöst.")
            raise  # Fehler weiterleiten, damit er im Thread behandelt werden kann
        except Exception as e:
            print(f"Fehler bei Ausführung von Aktion {action.action_type}: {e}")
            raise

    def _wait_for_color(self, x: int, y: int, target_color: List[int],
                      tolerance: int = 10, timeout: int = 10) -> bool:
        """
        Wartet, bis der Pixel an Position (x,y) eine bestimmte Farbe hat

        Args:
            x: Absolute X-Koordinate
            y: Absolute Y-Koordinate
            target_color: Die zu suchende Farbe [r, g, b]
            tolerance: Toleranz für Farbvergleich
            timeout: Maximale Wartezeit in Sekunden

        Returns:
            bool: True wenn die Farbe gefunden wurde, False bei Timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                img = ImageGrab.grab(bbox=(x, y, x+1, y+1))
                pixel_color = img.getpixel((0, 0))

                # Stelle sicher, dass wir mit RGB-Werten vergleichen
                if len(pixel_color) > 3:  # RGBA Format
                    pixel_color = pixel_color[0:3]  # Ignoriere Alpha-Kanal

                if all(abs(a-b) <= tolerance for a, b in zip(pixel_color, target_color)):
                    return True
            except Exception as e:
                print(f"Fehler bei Farbprüfung: {e}")

            time.sleep(0.1)

        return False

    def _wait_for_text(self, region: List[int], text: str, timeout: int = 10) -> bool:
        """
        Wartet, bis der angegebene Text in der Region erscheint

        Args:
            region: Liste mit absoluten Koordinaten [x, y, width, height]
            text: Der zu suchende Text
            timeout: Maximale Wartezeit in Sekunden

        Returns:
            bool: True wenn der Text gefunden wurde, False bei Timeout
        """
        if len(region) != 4:
            raise ValueError("Region muss 4 Werte enthalten: [x, y, width, height]")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Region: [x, y, width, height]
                img = ImageGrab.grab(bbox=(region[0], region[1],
                                         region[0]+region[2],
                                         region[1]+region[3]))

                recognized_text = pytesseract.image_to_string(img)

                if text in recognized_text:
                    return True
            except Exception as e:
                print(f"Fehler bei OCR: {e}")

            time.sleep(0.5)

        return False

    def get_pixel_color(self, x: int, y: int, screen_id: int = 0) -> Tuple[int, int, int]:
        """
        Gibt die Farbe des Pixels an Position (x,y) zurück

        Args:
            x: Relative X-Koordinate auf dem Bildschirm
            y: Relative Y-Koordinate auf dem Bildschirm
            screen_id: ID des Bildschirms

        Returns:
            Tuple[int, int, int]: RGB-Werte des Pixels
        """
        # Absolute Koordinaten berechnen
        abs_x, abs_y = self._get_absolute_coordinates(x, y, screen_id)

        # Screenshot des Pixels machen
        img = ImageGrab.grab(bbox=(abs_x, abs_y, abs_x+1, abs_y+1))
        color = img.getpixel((0, 0))

        # Stelle sicher, dass wir RGB zurückgeben
        if len(color) > 3:  # RGBA Format
            return color[0:3]  # Ignoriere Alpha-Kanal
        return color

    def find_color_on_screen(self, target_color: List[int], screen_id: int = None,
                           tolerance: int = 10) -> Optional[Tuple[int, int]]:
        """
        Sucht nach dem ersten Vorkommen einer Farbe auf dem Bildschirm

        Args:
            target_color: RGB-Werte der zu suchenden Farbe [r, g, b]
            screen_id: Optional. ID des Bildschirms. Wenn None, werden alle Bildschirme durchsucht.
            tolerance: Erlaubte Abweichung pro Farbkanal

        Returns:
            Optional[Tuple[int, int]]: (rel_x, rel_y) Position der Farbe relativ
                                      zum ausgewählten Bildschirm, oder None, wenn nicht gefunden
        """
        try:
            # Bestimme die zu durchsuchenden Bildschirme
            screens_to_search = []
            if screen_id is not None and 0 <= screen_id < len(self.screen_info["screens"]):
                # Nur einen bestimmten Bildschirm durchsuchen
                screens_to_search = [self.screen_info["screens"][screen_id]]
            else:
                # Alle Bildschirme durchsuchen
                screens_to_search = self.screen_info["screens"]

            for screen in screens_to_search:
                # Screenshot des Bildschirms machen
                screen_x, screen_y = screen["x"], screen["y"]
                screen_width, screen_height = screen["width"], screen["height"]

                # Region des Bildschirms erfassen
                screen_shot = ImageGrab.grab(bbox=(
                    screen_x, screen_y,
                    screen_x + screen_width,
                    screen_y + screen_height
                ))

                # Bildschirm nach der Farbe durchsuchen
                for x in range(0, screen_width, 5):  # Für bessere Performance in 5er-Schritten
                    for y in range(0, screen_height, 5):
                        pixel_color = screen_shot.getpixel((x, y))

                        # Stelle sicher, dass wir mit RGB-Werten vergleichen
                        if len(pixel_color) > 3:  # RGBA Format
                            pixel_color = pixel_color[0:3]  # Ignoriere Alpha-Kanal

                        if all(abs(a-b) <= tolerance for a, b in zip(pixel_color, target_color)):
                            # Fine-tuning: Jetzt genau den Pixel finden
                            for dx in range(-5, 6):
                                for dy in range(-5, 6):
                                    nx, ny = x + dx, y + dy
                                    if 0 <= nx < screen_width and 0 <= ny < screen_height:
                                        pixel_color = screen_shot.getpixel((nx, ny))
                                        if len(pixel_color) > 3:
                                            pixel_color = pixel_color[0:3]
                                        if all(abs(a-b) <= tolerance for a, b in zip(pixel_color, target_color)):
                                            # Relative Koordinaten auf dem Bildschirm zurückgeben
                                            return (nx, ny)

        except Exception as e:
            print(f"Fehler bei Farbsuche: {e}")

        return None

    def ocr_region(self, region: List[int], screen_id: int = 0) -> str:
        """
        Führt OCR auf einer bestimmten Bildschirmregion aus

        Args:
            region: Liste mit relativen Koordinaten [x, y, width, height]
            screen_id: ID des Bildschirms

        Returns:
            str: Erkannter Text
        """
        if len(region) != 4:
            raise ValueError("Region muss 4 Werte enthalten: [x, y, width, height]")

        # Absolute Koordinaten für die Region berechnen
        abs_x, abs_y = self._get_absolute_coordinates(region[0], region[1], screen_id)
        width, height = region[2], region[3]

        # Region: [x, y, width, height]
        img = ImageGrab.grab(bbox=(abs_x, abs_y, abs_x + width, abs_y + height))
        return pytesseract.image_to_string(img)

    def find_text_on_screen(self, text: str, screen_id: int = None,
                          min_confidence: float = 0.7) -> Optional[List[int]]:
        """
        Sucht nach Text auf dem Bildschirm und gibt die Region zurück

        Args:
            text: Der zu suchende Text
            screen_id: Optional. ID des Bildschirms. Wenn None, werden alle Bildschirme durchsucht.
            min_confidence: Minimale Konfidenz für die Texterkennung (0-1)

        Returns:
            Optional[List[int]]: [rel_x, rel_y, width, height] der gefundenen Region
                                relativ zum Bildschirm, oder None
        """
        try:
            # Bestimme die zu durchsuchenden Bildschirme
            screens_to_search = []
            if screen_id is not None and 0 <= screen_id < len(self.screen_info["screens"]):
                # Nur einen bestimmten Bildschirm durchsuchen
                screens_to_search = [self.screen_info["screens"][screen_id]]
            else:
                # Alle Bildschirme durchsuchen
                screens_to_search = self.screen_info["screens"]

            for screen in screens_to_search:
                current_screen_id = screen["id"]
                screen_x, screen_y = screen["x"], screen["y"]
                screen_width, screen_height = screen["width"], screen["height"]

                # Bildschirm in Regionen mit adaptiver Größe unterteilen
                max_regions = 9  # 3x3 Grid
                region_width = screen_width // int(max_regions ** 0.5)
                region_height = screen_height // int(max_regions ** 0.5)

                for x in range(0, screen_width, region_width):
                    for y in range(0, screen_height, region_height):
                        actual_width = min(region_width, screen_width - x)
                        actual_height = min(region_height, screen_height - y)

                        # Absoluten Bildschirmbereich erfassen
                        abs_x = screen_x + x
                        abs_y = screen_y + y

                        region_img = ImageGrab.grab(bbox=(
                            abs_x, abs_y,
                            abs_x + actual_width,
                            abs_y + actual_height
                        ))

                        recognized_text = pytesseract.image_to_string(region_img)

                        if text.lower() in recognized_text.lower():
                            # Verbesserte Erkennung mit OCR-spezifischen Optionen
                            data = pytesseract.image_to_data(region_img, output_type=pytesseract.Output.DICT)
                            confidence_threshold = min_confidence * 100  # Umrechnung in Prozent

                            # Suche nach dem erkannten Text
                            for i, word in enumerate(data['text']):
                                if word and text.lower() in word.lower() and float(data['conf'][i]) >= confidence_threshold:
                                    # Gefundene Position zurückgeben, relativ zum Bildschirm
                                    word_x = x + data['left'][i]
                                    word_y = y + data['top'][i]
                                    word_w = data['width'][i]
                                    word_h = data['height'][i]
                                    return [word_x, word_y, word_w, word_h, current_screen_id]

                            # Wenn keine genauere Position gefunden wurde, gib die Region zurück
                            return [x, y, actual_width, actual_height, current_screen_id]

        except Exception as e:
            print(f"Fehler bei Textsuche: {e}")

        return None