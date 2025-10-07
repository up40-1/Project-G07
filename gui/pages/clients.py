from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QTableWidget, QTableWidgetItem, QPushButton,
                              QFrame, QHeaderView, QMenu, QStyledItemDelegate)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QPainter, QBrush, QFont
from PyQt6.QtCore import QSize
from gui.styles import Styles
from utils.config_manager import ConfigManager
from utils.discord_bot import DiscordBot
from utils.sound_manager import SoundManager


def svg_to_icon(svg_text: str, size: int = 18):
    try:
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPixmap, QPainter, QIcon
        from PyQt6.QtCore import QByteArray
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        r = QSvgRenderer(QByteArray(svg_text.encode('utf-8')))
        p = QPainter(pix)
        r.render(p)
        p.end()
        return QIcon(pix)
    except Exception:
        return None

class ClientsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.discord_bot = None
        self.sound_manager = SoundManager()
        self.previous_clients = []
        self.init_ui()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_clients)
        self.timer.start(3000)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        
        title_layout = QHBoxLayout()
        
        title = QLabel("Connected Clients")
        title.setStyleSheet(Styles.LABEL_TITLE)
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        refresh_btn = QPushButton("  Refresh")
        refresh_btn.setStyleSheet(Styles.BUTTON_SECONDARY)
        refresh_btn.setFixedSize(140, 40)
        refresh_btn.clicked.connect(self.refresh_clients)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6">  <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" /></svg>'''
        try:
            from PyQt6.QtSvg import QSvgRenderer
            from PyQt6.QtGui import QPixmap, QPainter, QIcon
            from PyQt6.QtCore import QByteArray
            pix = QPixmap(18, 18)
            pix.fill(Qt.GlobalColor.transparent)
            r = QSvgRenderer(QByteArray(refresh_svg.encode('utf-8')))
            p = QPainter(pix)
            r.render(p)
            p.end()
            refresh_btn.setIcon(QIcon(pix))
            refresh_btn.setIconSize(pix.size())
            refresh_btn.setText(" Refresh")
        except Exception:
            refresh_btn.setText("Refresh")
        title_layout.addWidget(refresh_btn)
        
        layout.addLayout(title_layout)
        
        legend = QLabel("Right-click a row for actions • Double-click also opens the menu • Columns are sortable")
        legend.setStyleSheet(f"color:{Styles.TEXT_SECONDARY}; font-size:12px; padding-left:4px;")
        layout.addWidget(legend)

        table_frame = QFrame()
        table_frame.setStyleSheet(Styles.CARD)
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(8, 8, 8, 8)
        table_layout.setSpacing(6)

        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(5)
        self.clients_table.setHorizontalHeaderLabels([
            "Status", "PC Name", "IP Address", "Region", "Last Ping"
        ])
        self.clients_table.setStyleSheet(Styles.TABLE + f"""
            QTableWidget {{
                gridline-color: #333333;
                /* neutral hover/selection color to avoid yellow */
                selection-background-color: {Styles.HOVER};
                selection-color: {Styles.TEXT};
                border-radius: 14px;
                outline: none;
            }}
            QHeaderView::section {{
                background-color: #1f1f1f;
                color: {Styles.TEXT_SECONDARY};
                padding: 9px 6px;
                border: none;
                border-right: 1px solid #2b2b2b;
                font-size: 12px;
                letter-spacing: .5px;
            }}
            QHeaderView::section:first {{ border-top-left-radius: 10px; }}
            QHeaderView::section:last {{ border-top-right-radius: 10px; border-right:none; }}
            QTableWidget::item {{ padding: 6px; }}
            QTableWidget::item:selected {{ background-color: {Styles.HOVER}; }}
            QTableWidget::item:focus {{ background-color: transparent; }}
        """)
        self.clients_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.clients_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.clients_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.clients_table.customContextMenuRequested.connect(self.show_context_menu)
        self.clients_table.setSortingEnabled(True)
        self.clients_table.doubleClicked.connect(lambda: self._open_context_for_current())

        header = self.clients_table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setHighlightSections(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.clients_table.setColumnWidth(0, 100)
        self.clients_table.setColumnWidth(3, 100)
        self.clients_table.setShowGrid(False)
        header.setVisible(True)

        table_layout.addWidget(self.clients_table)
        layout.addWidget(table_frame, 1)

        tips = {
            0: "Connection status (Online / Offline)",
            1: "Reported hostname of the client machine",
            2: "Internal or external IP address used for Discord communication",
            3: "Resolved geographic region (may be approximate)",
            4: "Time since the last heartbeat / ping"
        }
        for col, text in tips.items():
            item = self.clients_table.horizontalHeaderItem(col)
            if item:
                item.setToolTip(text)

        self.clients_table.setItemDelegateForColumn(0, StatusBadgeDelegate(self))

        self._empty_label = QLabel("No clients yet. When clients connect they'll appear here.")
        self._empty_label.setStyleSheet(f"color:{Styles.TEXT_SECONDARY}; font-size:13px; padding:14px;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        table_layout.addWidget(self._empty_label)
        self._empty_label.hide()

        self.refresh_clients()

    def _open_context_for_current(self):
        row = self.clients_table.currentRow()
        if row < 0:
            return
        rect = self.clients_table.visualItemRect(self.clients_table.item(row, 0))
        local_point = rect.center()
        self.show_context_menu(local_point)

class StatusBadgeDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        value = index.data()
        online = bool(index.data(Qt.ItemDataRole.UserRole))
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = option.rect
        dot_radius = 6
        dot_x = r.left() + 12
        dot_y = r.center().y()
        dot_color = QColor("#19c870") if online else QColor("#888888")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(dot_x - dot_radius, dot_y - dot_radius, dot_radius*2, dot_radius*2)
        text_rect = r.adjusted(28, 0, -6, 0)
        font = painter.font()
        font.setBold(False)
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(QColor(Styles.TEXT))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, str(value))
        painter.restore()

    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        return base + QSize(0, 8)

def _clients_page_methods_patch():
    pass

ClientsPage.refresh_clients = lambda self: _refresh_clients_impl(self)
ClientsPage.show_context_menu = lambda self, position: _show_context_menu_impl(self, position)
ClientsPage.add_actions_to_menu = lambda self, menu, row: _add_actions_impl(self, menu, row)
ClientsPage.execute_command = lambda self, row, command: _execute_command_impl(self, row, command)
ClientsPage.open_terminal = lambda self, row: _open_terminal_impl(self, row)
ClientsPage.open_file_explorer = lambda self, row: _open_file_explorer_impl(self, row)
ClientsPage.send_discord_command = lambda self, ip, command: _send_discord_impl(self, ip, command)
ClientsPage.remove_client = lambda self, row: _remove_client_impl(self, row)

def _refresh_clients_impl(self):
    try:
        self.config.load()
    except Exception:
        pass
    all_clients = self.config.get('clients', [])
    display_clients = [c for c in all_clients if not c.get('hidden', False)]
    try:
        bot_ready = bool(self.discord_bot and self.discord_bot.is_ready())
    except Exception:
        bot_ready = False
    if self.config.get('sound_alerts', True):
        current_online = [c['ip'] for c in display_clients if c.get('ip')]
        previous_online = [c for c in self.previous_clients if c]
        new_online = set(current_online) - set(previous_online)
        if new_online:
            self.sound_manager.play('online')
        went_offline = set(previous_online) - set(current_online)
        if went_offline:
            self.sound_manager.play('offline')
    self.previous_clients = [c.get('ip') for c in display_clients if c.get('ip')]
    try:
        self.clients_table.clearContents()
    except Exception:
        pass
    self.clients_table.setRowCount(len(display_clients))
    for row, client in enumerate(display_clients):
        status = client.get('status', 'offline')
        is_online = str(status).lower() == 'online'
        status_item = QTableWidgetItem("Online" if is_online else "Offline")
        status_item.setData(Qt.ItemDataRole.UserRole, is_online)
        self.clients_table.setItem(row, 0, status_item)
        name_item = QTableWidgetItem(client.get('hostname', 'Unknown'))
        f = name_item.font()
        f.setBold(True)
        name_item.setFont(f)
        self.clients_table.setItem(row, 1, name_item)
        self.clients_table.setItem(row, 2, QTableWidgetItem(client.get('ip', 'Unknown')))
        self.clients_table.setItem(row, 3, QTableWidgetItem(client.get('region', 'Unknown')))
        last_ping = client.get('last_ping', 'Never')
        if last_ping != 'Never':
            try:
                ping_time = datetime.fromisoformat(last_ping)
                secs = int((datetime.now() - ping_time).total_seconds())
                if secs < 60:
                    last_ping = "Just now"
                elif secs < 3600:
                    last_ping = f"{secs // 60}m ago"
                elif secs < 86400:
                    last_ping = f"{secs // 3600}h ago"
                else:
                    last_ping = f"{secs // 86400}d ago"
            except Exception:
                pass
        self.clients_table.setItem(row, 4, QTableWidgetItem(last_ping))
    try:
        self.clients_table.resizeRowsToContents()
        self.clients_table.viewport().update()
    except Exception:
        pass
    if len(display_clients) == 0:
        self._empty_label.show(); self.clients_table.hide()
    else:
        self._empty_label.hide(); self.clients_table.show()

def _show_context_menu_impl(self, position):
    row = self.clients_table.rowAt(position.y())
    if row < 0:
        return
    menu = QMenu(self)
    menu.setStyleSheet(f"""
        QMenu {{ background-color: {Styles.CARD_BG}; color: {Styles.TEXT}; border: 2px solid {Styles.PRIMARY}; border-radius: 10px; padding: 5px; }}
        QMenu::item {{ padding: 8px 25px; border-radius: 5px; }}
        QMenu::item:selected {{ background-color: {Styles.HOVER}; }}
    """)
    self.add_actions_to_menu(menu, row)
    menu.exec(self.clients_table.viewport().mapToGlobal(position))

def _add_actions_impl(self, menu, row):
    screenshot_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6"> <path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" /> <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z" /></svg>'''
    terminal_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6"> <path stroke-linecap="round" stroke-linejoin="round" d="m6.75 7.5 3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0 0 21 18V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v12a2.25 2.25 0 0 0 2.25 2.25Z" /></svg>'''
    info_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6"> <path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 12V5.25" /></svg>'''
    file_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6"> <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" /></svg>'''
    restart_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6"> <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" /></svg>'''
    shutdown_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6"> <path stroke-linecap="round" stroke-linejoin="round" d="M5.636 5.636a9 9 0 1 0 12.728 0M12 3v9" /></svg>'''
    logoff_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6"> <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 9V5.25A2.25 2.25 0 0 1 10.5 3h6a2.25 2.25 0 0 1 2.25 2.25v13.5A2.25 2.25 0 0 1 16.5 21h-6a2.25 2.25 0 0 1-2.25-2.25V15m-3 0-3-3m0 0 3-3m-3 3H15" /></svg>'''
    def _add(label, svg, handler):
        a = QAction(label, self)
        icon = svg_to_icon(svg, 18)
        if icon:
            a.setIcon(icon)
        a.triggered.connect(handler)
        menu.addAction(a)
    _add("Screenshot", screenshot_svg, lambda: self.execute_command(row, "screenshot"))
    _add("Open Terminal", terminal_svg, lambda: self.open_terminal(row))
    _add("System Info", info_svg, lambda: self.execute_command(row, "info"))
    _add("File Explorer", file_svg, lambda: self.open_file_explorer(row))
    menu.addSeparator()
    _add("Shutdown", shutdown_svg, lambda: self.execute_command(row, "shutdown"))
    _add("Restart", restart_svg, lambda: self.execute_command(row, "restart"))
    _add("Logoff", logoff_svg, lambda: self.execute_command(row, "logoff"))

def _execute_command_impl(self, row, command):
    ip = self.clients_table.item(row, 2).text()
    hostname = self.clients_table.item(row, 1).text()
    if command in ['shutdown', 'restart']:
        decided = {'go': False}
        def do_it(): decided['go'] = True
        try:
            self.window().show_notification(
                f"Confirm {command} for {hostname}?", level='warn', duration_ms=8000,
                actions=[("Yes", do_it), ("Cancel", lambda: None)]
            )
        except Exception:
            pass
        from PyQt6.QtCore import QTimer
        def _check():
            if decided['go']:
                self.send_discord_command(ip, command)
                try:
                    self.window().show_notification(f"Command '{command}' sent to {hostname}", level='info')
                except Exception:
                    pass
        QTimer.singleShot(8200, _check)
        return
    self.send_discord_command(ip, command)
    try:
        self.window().show_notification(f"Command '{command}' sent to {hostname}", level='info')
    except Exception:
        pass

def _open_terminal_impl(self, row):
    from gui.dialogs.terminal_dialog import TerminalDialog
    ip = self.clients_table.item(row, 2).text()
    hostname = self.clients_table.item(row, 1).text()
    TerminalDialog(self, hostname, ip).exec()

def _open_file_explorer_impl(self, row):
    from gui.dialogs.file_explorer_dialog import FileExplorerDialog
    ip = self.clients_table.item(row, 2).text()
    hostname = self.clients_table.item(row, 1).text()
    FileExplorerDialog(self, hostname, ip, self.discord_bot).exec()

def _send_discord_impl(self, ip, command):
    if not self.discord_bot:
        try: self.window().show_notification("Start the Discord bot first (title bar)", level='warn')
        except Exception: pass
        return
    if not self.discord_bot.is_ready():
        try: self.window().show_notification("Bot is starting up. Try again soon.", level='warn')
        except Exception: pass
        return
    success = self.discord_bot.send_command(ip, command)
    if not success:
        try: self.window().show_notification("Failed to send command. Check bot status.", level='error')
        except Exception: pass

def _remove_client_impl(self, row):
    try:
        ip_item = self.clients_table.item(row, 2)
        if not ip_item:
            return
        ip = ip_item.text()
        clients = self.config.get('clients', [])
        changed = False
        for c in clients:
            if c.get('ip') == ip:
                c['hidden'] = True
                changed = True
                break
        if changed:
            self.config.set('clients', clients)
        self.config.save()
        self.refresh_clients()
        try: self.window().show_notification(f"Removed client {ip}", level='info')
        except Exception: pass
    except Exception as e:
        try: self.window().show_notification(f"Failed to remove client: {e}", level='error')
        except Exception: pass

