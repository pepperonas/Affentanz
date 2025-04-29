"""
Thread-Klassen für die Ausführung von Workflows und die Aufzeichnung von Aktionen.
"""

import time
import pyautogui
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
from automation_engine import AutomationEngine
from models import Action, ActionType


class WorkflowThread(QThread):
    """Thread für die Ausführung eines Workflows"""
    progress_updated = pyqtSignal(int)
    action_completed = pyqtSignal(int, bool)  # Index, Success
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, engine: AutomationEngine):
        """
        Initialisiert den WorkflowThread
        
        Args:
            engine: AutomationEngine-Instanz, die den Workflow ausführt
        """
        super().__init__()
        self.engine = engine
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self.paused = False
        
    def run(self):
        """Führt den Workflow aus"""
        try:
            def update_progress(index):
                """Callback für Fortschrittsanzeige"""
                self.progress_updated.emit(index)
                
                # Unterstütze Pausieren
                self.mutex.lock()
                if self.paused:
                    self.condition.wait(self.mutex)
                self.mutex.unlock()
                
            self.engine.play_workflow(callback=update_progress)
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            # Sicherstellen, dass is_playing auf False gesetzt wird
            self.engine.is_playing = False
            self.finished.emit()

    def stop(self):
        """Stoppt die Ausführung des Workflows"""
        # Setze is_playing im Engine auf False, um die Ausführungsschleife zu unterbrechen
        self.engine.is_playing = False
        self.engine.stop_playback()

        # Stelle sicher, dass der Thread nicht im pausierten Zustand hängt
        self.mutex.lock()
        self.paused = False
        self.condition.wakeAll()
        self.mutex.unlock()

        # Warte maximal 1 Sekunde auf Beendigung
        if not self.wait(1000):
            # Nur als letzten Ausweg
            self.terminate()
            self.wait()

    def pause(self):
        """Pausiert die Ausführung des Workflows"""
        self.mutex.lock()
        self.paused = True
        self.mutex.unlock()

    def resume(self):
        """Setzt die Ausführung des Workflows fort"""
        self.mutex.lock()
        self.paused = False
        self.condition.wakeAll()
        self.mutex.unlock()


class RecordingThread(QThread):
    """Thread für die Aufzeichnung von Benutzeraktionen"""
    action_recorded = pyqtSignal(Action)
    error_occurred = pyqtSignal(str)

    def __init__(self, engine: AutomationEngine):
        """
        Initialisiert den RecordingThread

        Args:
            engine: AutomationEngine-Instanz, die die Aufzeichnung handhabt
        """
        super().__init__()
        self.engine = engine
        self.mutex = QMutex()
        self.running = True
        self.last_mouse_position = None
        self.last_mouse_time = 0
        self.min_move_distance = 10  # Mindestabstand für Mausbewegungen in Pixeln
        self.min_move_interval = 0.2  # Minimales Zeitintervall zwischen Aufzeichnungen

    def run(self):
        """Hauptmethode für die Aufzeichnung"""
        try:
            # Mock-Implementation mit tatsächlichem Tracking
            # In einer realen Implementation würden wir System-spezifische Event-Hooks verwenden
            initial_mouse_pos = pyautogui.position()
            self.last_mouse_position = initial_mouse_pos
            self.last_mouse_time = time.time()

            # Aufzeichnen der Startposition
            start_action = Action(
                ActionType.MOUSE_MOVE,
                {"x": initial_mouse_pos[0], "y": initial_mouse_pos[1], "duration": 0.1}
            )
            self.action_recorded.emit(start_action)

            while self.running:
                self.mutex.lock()
                still_running = self.running
                self.mutex.unlock()

                if not still_running:
                    break

                # Mausposition prüfen
                current_mouse_pos = pyautogui.position()
                current_time = time.time()

                # Wenn sich die Maus genug bewegt hat und genug Zeit vergangen ist
                if (self._distance(current_mouse_pos, self.last_mouse_position) > self.min_move_distance and
                    current_time - self.last_mouse_time > self.min_move_interval):

                    # Mausbewegung aufzeichnen
                    move_action = Action(
                        ActionType.MOUSE_MOVE,
                        {"x": current_mouse_pos[0], "y": current_mouse_pos[1], "duration": 0.1}
                    )
                    self.action_recorded.emit(move_action)

                    self.last_mouse_position = current_mouse_pos
                    self.last_mouse_time = current_time

                # Kurze Pause, um CPU-Last zu reduzieren
                time.sleep(0.05)
        except Exception as e:
            self.error_occurred.emit(f"Fehler bei der Aufzeichnung: {str(e)}")

    def _distance(self, pos1, pos2):
        """Berechnet die Entfernung zwischen zwei Punkten"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

    def stop(self):
        """Stoppt die Aufzeichnung"""
        self.mutex.lock()
        self.running = False
        self.mutex.unlock()

        # Warte maximal 1 Sekunde auf Beendigung
        if not self.wait(1000):
            self.terminate()  # Nur als letzte Möglichkeit