"""
Datenmodelle für das Desktop-Automatisierungstool.
Enthält die Definitionen für Aktionstypen und Aktionen.
"""

from enum import Enum
from typing import Dict, Any, List


class ActionType(Enum):
    """Enumeration für die verschiedenen Arten von Aktionen"""
    MOUSE_MOVE = "Mausbewegung"
    MOUSE_CLICK = "Mausklick"
    MOUSE_DOUBLE_CLICK = "Doppelklick"
    MOUSE_RIGHT_CLICK = "Rechtsklick"
    MOUSE_DRAG = "Maus ziehen"
    KEY_PRESS = "Taste drücken"
    KEY_COMBO = "Tastenkombination"
    WAIT = "Warten"
    WAIT_FOR_COLOR = "Auf Farbe warten"
    WAIT_FOR_TEXT = "Auf Text warten"


class Action:
    """Klasse für eine einzelne Aktion im Workflow"""

    def __init__(self, action_type: ActionType, params: Dict[str, Any]):
        """
        Erstellt eine neue Aktion

        Args:
            action_type: Der Typ der Aktion
            params: Parameter für die Aktion
        """
        self.action_type = action_type
        self.params = params

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert die Aktion in ein Dictionary für die JSON-Serialisierung"""
        return {
            "type": self.action_type.value,
            "params": self.params
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        """Erstellt eine Aktion aus einem Dictionary (für die JSON-Deserialisierung)"""
        action_type = next(t for t in ActionType if t.value == data["type"])
        return cls(action_type, data["params"])

    def get_default_params(action_type: ActionType) -> Dict[str, Any]:
        """Gibt Standardparameter für einen Aktionstyp zurück"""
        if action_type in [ActionType.MOUSE_MOVE, ActionType.MOUSE_CLICK,
                           ActionType.MOUSE_DOUBLE_CLICK, ActionType.MOUSE_RIGHT_CLICK]:
            return {"x": 0, "y": 0, "duration": 0.1}
        elif action_type == ActionType.MOUSE_DRAG:
            return {"start_x": 0, "start_y": 0, "end_x": 100, "end_y": 100, "duration": 0.5}
        elif action_type == ActionType.KEY_PRESS:
            return {"key": "enter"}
        elif action_type == ActionType.KEY_COMBO:
            return {"keys": ["ctrl", "c"]}
        elif action_type == ActionType.WAIT:
            return {"seconds": 1}
        elif action_type == ActionType.WAIT_FOR_COLOR:
            return {"x": 0, "y": 0, "color": [255, 0, 0], "tolerance": 10, "timeout": 10}
        elif action_type == ActionType.WAIT_FOR_TEXT:
            return {"region": [0, 0, 200, 100], "text": "Beispieltext", "timeout": 10}
        else:
            return {}

    def get_description(self) -> str:
        """Gibt eine Beschreibung der Aktion zurück, die in der UI angezeigt werden kann"""
        description = f"{self.action_type.value}"

        if self.action_type == ActionType.MOUSE_MOVE:
            description += f" ({self.params['x']}, {self.params['y']})"
        elif self.action_type in [ActionType.MOUSE_CLICK, ActionType.MOUSE_DOUBLE_CLICK,
                                  ActionType.MOUSE_RIGHT_CLICK]:
            description += f" ({self.params['x']}, {self.params['y']})"
        elif self.action_type == ActionType.MOUSE_DRAG:
            description += f" ({self.params.get('start_x', 0)}, {self.params.get('start_y', 0)}) -> "
            description += f"({self.params['end_x']}, {self.params['end_y']})"
        elif self.action_type == ActionType.KEY_PRESS:
            description += f" {self.params['key']}"
        elif self.action_type == ActionType.KEY_COMBO:
            description += f" {'+'.join(self.params['keys'])}"
        elif self.action_type == ActionType.WAIT:
            description += f" {self.params['seconds']}s"
        elif self.action_type == ActionType.WAIT_FOR_COLOR:
            description += f" an ({self.params['x']}, {self.params['y']})"
        elif self.action_type == ActionType.WAIT_FOR_TEXT:
            description += f" '{self.params['text']}'"

        return description