"""Global notification helper to decouple other modules from MainWindow implementation."""
from typing import Callable, List, Optional, Tuple

# (label, callback) list for actions
_Action = Tuple[str, Callable[[], None]]

_main_window = None

def register_main_window(win):
    global _main_window
    _main_window = win

def notify(message: str, level: str = 'info', duration_ms: int = 5000, actions: Optional[List[_Action]] = None):
    if _main_window is not None:
        try:
            _main_window.show_notification(message, level=level, duration_ms=duration_ms, actions=actions)
            return
        except Exception:
            pass
    print(f"[NOTIFY][{level.upper()}] {message}")
    if actions:
        # auto-run first action to preserve logic flow if provided
        try:
            label, cb = actions[0]
            cb()
        except Exception:
            pass

def confirm(message: str, on_yes: Callable[[], None], on_no: Optional[Callable[[], None]] = None,
            yes_label: str = 'Yes', no_label: str = 'No', level: str='warn'):
    actions: List[_Action] = [
        (yes_label, on_yes)
    ]
    if on_no:
        actions.append((no_label, on_no))
    notify(message, level=level, duration_ms=8000, actions=actions)
