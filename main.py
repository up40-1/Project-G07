import sys
import os
import subprocess
import shutil
import importlib.util
import traceback
from types import SimpleNamespace

_setup_logs = []

class _SilentStream:
    def write(self, text):
        if text and not text.isspace():
            _setup_logs.append(text.rstrip('\n'))
    def flush(self):
        pass

_REAL_STDOUT = sys.stdout
_REAL_STDERR = sys.stderr

sys.stdout = _SilentStream()
sys.stderr = _SilentStream()

def _exception_hook(exc_type, exc_value, exc_tb):
    details = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _setup_logs.append('[fatal] Unhandled exception:')
    _setup_logs.extend(line for line in details.splitlines())
    try:
        _REAL_STDERR.write(details)
    except Exception:
        pass
    sys.exit(1)

sys.excepthook = _exception_hook


def in_virtualenv() -> bool:
    if hasattr(sys, 'real_prefix'):
        return True
    if sys.prefix != getattr(sys, 'base_prefix', sys.prefix):
        return True
    if os.environ.get('VIRTUAL_ENV'):
        return True
    return False


def find_system_python():
    candidates = [shutil.which('python'), shutil.which('python3'), shutil.which('py')]
    for c in candidates:
        if not c:
            continue
        try:
            c_real = os.path.realpath(c)
            if not c_real.startswith(os.path.realpath(sys.prefix)):
                return c
        except Exception:
            return c
    for p in [r"C:\Windows\py.exe", r"C:\Python39\python.exe", r"C:\Program Files\Python39\python.exe"]:
        if os.path.exists(p):
            return p
    return None


def relaunch_with_system_python():
    try:
        if not in_virtualenv():
            return False
        system_py = find_system_python()
        if not system_py:
            return False
        cmd = [system_py] + sys.argv
        os.execv(system_py, cmd)
        return True
    except Exception:
        return False


def ensure_dependencies(packages: dict):
    missing = []
    for pip_name, import_name in packages.items():
        if importlib.util.find_spec(import_name) is None:
            missing.append(pip_name)

    if not missing:
        return True

    _setup_logs.append(f"[setup] Installing missing packages: {missing}")
    for pkg in missing:
        try:
            _setup_logs.append(f"[setup] pip install {pkg} ...")
            res = subprocess.run([sys.executable, '-m', 'pip', 'install', pkg], check=False)
            if res.returncode != 0:
                _setup_logs.append(f"[setup] Failed to install {pkg} (exit {res.returncode})")
                return False
        except Exception as e:
            _setup_logs.append(f"[setup] Exception installing {pkg}: {e}")
            return False
    return True


try:
    if relaunch_with_system_python():
        pass
except Exception:
    pass

REQUIRED = {
    'PyQt6': 'PyQt6',
    'discord.py': 'discord',
    'Pillow': 'PIL',
    'aiohttp': 'aiohttp',
    'pyinstaller': 'PyInstaller'
}

if not ensure_dependencies(REQUIRED):
    sys.stdout = _REAL_STDOUT
    sys.stderr = _REAL_STDERR
    print('Failed to ensure required dependencies. See setup logs below:')
    for line in _setup_logs:
        print(line)
    sys.exit(1)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from gui.main_window import MainWindow

def main():
    if hasattr(QApplication, 'setHighDpiScaleFactorRoundingPolicy'):
        try:
            QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        except Exception:
            pass
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    try:
        window = MainWindow()
    except Exception:
        raise
    for line in _setup_logs:
        try:
            window.append_log(line)
        except Exception:
            pass
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
