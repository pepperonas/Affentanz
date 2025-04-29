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
            for i, action in enumerate(self.workflow):
                if not self.is_playing:
                    break

                self._execute_action(action)

                if callback:
                    callback(i)
        except Exception as e:
            print(f"Fehler bei Workflow-Ausführung: {e}")
        finally:
            self.is_playing = False

    def stop_playback(self):
        """Stoppt die Ausführung des Workflows"""
        self.is_playing = False

    def _execute_action(self, action: Action):
        """Führt eine einzelne Aktion aus"""
        try:
            if action.action_type == ActionType.MOUSE_MOVE:
                pyautogui.moveTo(action.params["x"], action.params["y"],
                              duration=action.params.get("duration", 0.1))

            elif action.action_type == ActionType.MOUSE_CLICK:
                pyautogui.click(action.params["x"], action.params["y"],
                             button=action.params.get("button", "left"),
                             duration=action.params.get("duration", 0.1))

            elif action.action_type == ActionType.MOUSE_DOUBLE_CLICK:
                pyautogui.doubleClick(action.params["x"], action.params["y"],
                                   button=action.params.get("button", "left"),
                                   duration=action.params.get("duration", 0.1))

            elif action.action_type == ActionType.MOUSE_RIGHT_CLICK:
                pyautogui.rightClick(action.params["x"], action.params["y"],
                                  duration=action.params.get("duration", 0.1))

            elif action.action_type == ActionType.MOUSE_DRAG:
                # Erst zur Startposition bewegen, dann ziehen
                start_x = action.params.get("start_x", pyautogui.position()[0])
                start_y = action.params.get("start_y", pyautogui.position()[1])
                pyautogui.moveTo(start_x, start_y, duration=action.params.get("duration", 0.1) / 2)

                # Jetzt zur Endposition ziehen
                pyautogui.dragTo(action.params["end_x"], action.params["end_y"],
                              button=action.params.get("button", "left"),
                              duration=action.params.get("duration", 0.5),
                              mouseDownUp=True)

            elif action.action_type == ActionType.KEY_PRESS:
                pyautogui.press(action.params["key"])

            elif action.action_type == ActionType.KEY_COMBO:
                pyautogui.hotkey(*action.params["keys"])

            elif action.action_type == ActionType.WAIT:
                time.sleep(action.params["seconds"])

            elif action.action_type == ActionType.WAIT_FOR_COLOR:
                self._wait_for_color(
                    action.params["x"],
                    action.params["y"],
                    action.params["color"],
                    action.params.get("tolerance", 10),
                    action.params.get("timeout", 10)
                )

            elif action.action_type == ActionType.WAIT_FOR_TEXT:
                self._wait_for_text(
                    action.params["region"],
                    action.params["text"],
                    action.params.get("timeout", 10)
                )

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
            region: Liste mit [x, y, width, height]
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

    def get_pixel_color(self, x: int, y: int) -> Tuple[int, int, int]:
        """
        Gibt die Farbe des Pixels an Position (x,y) zurück

        Returns:
            Tuple[int, int, int]: RGB-Werte des Pixels
        """
        img = ImageGrab.grab(bbox=(x, y, x+1, y+1))
        color = img.getpixel((0, 0))

        # Stelle sicher, dass wir RGB zurückgeben
        if len(color) > 3:  # RGBA Format
            return color[0:3]  # Ignoriere Alpha-Kanal
        return color

    def find_color_on_screen(self, target_color: List[int],
                           tolerance: int = 10) -> Optional[Tuple[int, int]]:
        """
        Sucht nach dem ersten Vorkommen einer Farbe auf dem Bildschirm

        Args:
            target_color: RGB-Werte der zu suchenden Farbe [r, g, b]
            tolerance: Erlaubte Abweichung pro Farbkanal

        Returns:
            Optional[Tuple[int, int]]: (x, y) Position der Farbe oder None, wenn nicht gefunden
        """
        try:
            screen = ImageGrab.grab()
            width, height = screen.size

            for x in range(0, width, 5):  # Für bessere Performance in 5er-Schritten
                for y in range(0, height, 5):
                    pixel_color = screen.getpixel((x, y))

                    # Stelle sicher, dass wir mit RGB-Werten vergleichen
                    if len(pixel_color) > 3:  # RGBA Format
                        pixel_color = pixel_color[0:3]  # Ignoriere Alpha-Kanal

                    if all(abs(a-b) <= tolerance for a, b in zip(pixel_color, target_color)):
                        # Fine-tuning: Jetzt genau den Pixel finden
                        for dx in range(-5, 6):
                            for dy in range(-5, 6):
                                nx, ny = x + dx, y + dy
                                if 0 <= nx < width and 0 <= ny < height:
                                    pixel_color = screen.getpixel((nx, ny))
                                    if len(pixel_color) > 3:
                                        pixel_color = pixel_color[0:3]
                                    if all(abs(a-b) <= tolerance for a, b in zip(pixel_color, target_color)):
                                        return (nx, ny)
        except Exception as e:
            print(f"Fehler bei Farbsuche: {e}")

        return None

    def ocr_region(self, region: List[int]) -> str:
        """
        Führt OCR auf einer bestimmten Bildschirmregion aus

        Args:
            region: Liste mit [x, y, width, height]

        Returns:
            str: Erkannter Text
        """
        if len(region) != 4:
            raise ValueError("Region muss 4 Werte enthalten: [x, y, width, height]")

        # Region: [x, y, width, height]
        img = ImageGrab.grab(bbox=(region[0], region[1],
                                 region[0]+region[2],
                                 region[1]+region[3]))
        return pytesseract.image_to_string(img)

    def find_text_on_screen(self, text: str, min_confidence: float = 0.7) -> Optional[List[int]]:
        """
        Sucht nach Text auf dem Bildschirm und gibt die Region zurück

        Args:
            text: Der zu suchende Text
            min_confidence: Minimale Konfidenz für die Texterkennung (0-1)

        Returns:
            Optional[List[int]]: [x, y, width, height] der gefundenen Region oder None
        """
        try:
            screen = ImageGrab.grab()
            width, height = screen.size

            # Bildschirm in Regionen mit adaptiver Größe unterteilen
            # (weniger Bereiche für bessere Performance)
            max_regions = 9  # 3x3 Grid
            region_width = width // int(max_regions ** 0.5)
            region_height = height // int(max_regions ** 0.5)

            for x in range(0, width, region_width):
                for y in range(0, height, region_height):
                    actual_width = min(region_width, width - x)
                    actual_height = min(region_height, height - y)

                    region_img = screen.crop((x, y, x + actual_width, y + actual_height))
                    recognized_text = pytesseract.image_to_string(region_img)

                    if text.lower() in recognized_text.lower():
                        # Verbesserte Erkennung mit OCR-spezifischen Optionen
                        data = pytesseract.image_to_data(region_img, output_type=pytesseract.Output.DICT)
                        confidence_threshold = min_confidence * 100  # Umrechnung in Prozent

                        # Suche nach dem erkannten Text
                        for i, word in enumerate(data['text']):
                            if word and text.lower() in word.lower() and float(data['conf'][i]) >= confidence_threshold:
                                # Gefundene Position zurückgeben, absolut zum Bildschirm
                                word_x = x + data['left'][i]
                                word_y = y + data['top'][i]
                                word_w = data['width'][i]
                                word_h = data['height'][i]
                                return [word_x, word_y, word_w, word_h]

                        # Wenn keine genauere Position gefunden wurde, gib die Region zurück
                        return [x, y, actual_width, actual_height]
        except Exception as e:
            print(f"Fehler bei Textsuche: {e}")

        return None