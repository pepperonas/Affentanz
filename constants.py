"""
Konstanten für das Desktop-Automatisierungstool.
"""

# UI-Farbschema (Material Design inspiriert)
PRIMARY_COLOR = "#2C2E3B"  # Dunkles Blaugrau (Hauptfarbschema)
ACCENT_COLOR = "#5D5FEF"   # Helles Blau für Akzente
TEXT_COLOR = "#FFFFFF"     # Weiß für Text
SECONDARY_BG = "#3E4050"   # Etwas helleres Blaugrau für sekundäre Elemente
ERROR_COLOR = "#F44336"    # Rot für Fehler
SUCCESS_COLOR = "#4CAF50"  # Grün für Erfolg
WARNING_COLOR = "#FFC107"  # Gelb für Warnungen

# Tesseract-Standardpfad für verschiedene Plattformen
TESSERACT_PATH_MAC = "/usr/local/bin/tesseract"
TESSERACT_PATH_LINUX = "/usr/bin/tesseract"
TESSERACT_PATH_WINDOWS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Standardwerte für die Anwendung
DEFAULT_DURATION = 0.1      # Standarddauer für Mausbewegungen in Sekunden
DEFAULT_WAIT_TIME = 1.0     # Standardwartezeit in Sekunden
DEFAULT_TIMEOUT = 10.0      # Standard-Timeout in Sekunden
DEFAULT_COLOR_TOLERANCE = 10  # Standardtoleranz für Farbvergleiche

# UI-Einstellungen
MIN_WINDOW_WIDTH = 900
MIN_WINDOW_HEIGHT = 700
ACTION_ICON_SIZE = 16
TOOLBAR_ICON_SIZE = 24
BUTTON_MIN_WIDTH = 80
STATUSBAR_TIMEOUT = 3000  # ms
DEFAULT_BETWEEN_ACTIONS_DELAY = 100  # ms

# Dateipfade
HOME_DIR = ""  # Wird zur Laufzeit gesetzt
CONFIG_DIR = ".affentanz-configs"  # Versteckter Konfigurationsordner im Home-Verzeichnis
SETTINGS_FILE = ""  # Wird zur Laufzeit gesetzt
WORKFLOWS_DIR = ""  # Wird zur Laufzeit gesetzt

# Tastaturkürzel
SHORTCUT_NEW = "Ctrl+N"
SHORTCUT_OPEN = "Ctrl+O"
SHORTCUT_SAVE = "Ctrl+S"
SHORTCUT_PLAY = "F5"
SHORTCUT_RECORD = "F6"
SHORTCUT_STOP = "F7"
SHORTCUT_ADD_ACTION = "Ctrl+A"
SHORTCUT_DELETE_ACTION = "Delete"
SHORTCUT_DUPLICATE_ACTION = "Ctrl+D"
SHORTCUT_MOVE_UP = "Ctrl+Up"
SHORTCUT_MOVE_DOWN = "Ctrl+Down"
