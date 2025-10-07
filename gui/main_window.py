import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QStackedWidget, QLabel, QFrame, QTextEdit, QFileDialog, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QSize, QByteArray, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QPainter, QColor, QPixmap
try:
    from PyQt6.QtSvg import QSvgRenderer
except Exception:
    QSvgRenderer = None
import sys
from gui.pages.dashboard import DashboardPage
from gui.pages.builder import BuilderPage
from gui.pages.clients import ClientsPage
from gui.pages.help_page import HelpPage
from gui.pages.settings import SettingsPage
from gui.styles import Styles
from utils.config_manager import ConfigManager
from utils.discord_bot import DiscordBot

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project G07")
        self.setMinimumSize(1600, 1000)
        self.resize(1600, 1000)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.discord_bot = None
        self.config = ConfigManager()
        
        self.central_widget = QWidget()
        self.central_widget.setStyleSheet(Styles.MAIN_WINDOW)
        self.setCentralWidget(self.central_widget)
        
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.title_bar = self.create_title_bar()
        main_layout.addWidget(self.title_bar)
        
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        self.sidebar = self.create_sidebar()
        content_layout.addWidget(self.sidebar)
        
        self.pages = QStackedWidget()
        self.pages.setStyleSheet("background: transparent;")

        self.dashboard_page = DashboardPage()
        self.builder_page = BuilderPage()
        self.clients_page = ClientsPage()
        self.console_page = self.create_console_page()
        self.help_page = HelpPage()
        self.settings_page = SettingsPage()

        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(self.builder_page)
        self.pages.addWidget(self.clients_page)
        self.pages.addWidget(self.console_page)
        self.pages.addWidget(self.help_page)
        self.pages.addWidget(self.settings_page)
        
        content_layout.addWidget(self.pages, 1)
        main_layout.addWidget(content_widget)

        from PyQt6.QtCore import QTimer

        class EmittingStream:
            def __init__(self, append_func):
                self.append = append_func
            def write(self, text):
                if text and not text.isspace():
                    QTimer.singleShot(0, lambda t=text: self.append(t.rstrip('\n')))
            def flush(self):
                pass

        sys.stdout = EmittingStream(self.append_log)
        sys.stderr = EmittingStream(self.append_log)
        
        self.dragging = False
        self.drag_position = None
        
        self.auto_start_bot()
        self._notifications = []
        self._notification_container = QFrame(self.central_widget)
        self._notification_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._notification_container.setStyleSheet("background: transparent;")
        from PyQt6.QtWidgets import QVBoxLayout as _VBox
        self._notification_layout = _VBox(self._notification_container)
        self._notification_layout.setContentsMargins(0, 0, 0, 0)
        self._notification_layout.setSpacing(12)
        try:
            self._notification_layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        except Exception:
            pass
        self._notification_container.raise_()
        self._notification_sound = None
        self._load_notification_sound()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            cw = self.central_widget
            if cw and self._notification_container:
                margin_x = 28
                margin_y = 28
                w = 420
                max_h = max(200, cw.height() - margin_y * 2)
                h = min(420, max_h)
                self._notification_container.resize(w, h)
                x = max(8, cw.width() - w - margin_x)
                y = max(8, cw.height() - h - margin_y)
                self._notification_container.move(x, y)
                self._notification_container.raise_()
        except Exception:
            pass
    
    def _load_notification_sound(self):
        try:
            from PyQt6.QtCore import QUrl
            try:
                from PyQt6.QtMultimedia import QSoundEffect
            except Exception:
                QSoundEffect = None
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            candidate_paths = [
                os.path.join(base, 'sounds', 'notify.mp3'),
                os.path.join(base, 'notify.mp3')
            ]
            sound_file = None
            for p in candidate_paths:
                if os.path.exists(p):
                    sound_file = p
                    break
            self._notification_sound = None
            self._notification_player = None
            if sound_file:
                if QSoundEffect is not None:
                    try:
                        eff = QSoundEffect(self)
                        eff.setSource(QUrl.fromLocalFile(sound_file))
                        try:
                            eff.setVolume(0.85)
                        except Exception:
                            pass
                        self._notification_sound = eff
                    except Exception:
                        self._notification_sound = None
                if self._notification_sound is None:
                    try:
                        from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
                        audio_output = QAudioOutput(self)
                        player = QMediaPlayer(self)
                        player.setAudioOutput(audio_output)
                        player.setSource(QUrl.fromLocalFile(sound_file))
                        audio_output.setVolume(0.85)
                        self._notification_player = player
                    except Exception:
                        self._notification_player = None
        except Exception:
            self._notification_sound = None

    def show_notification(self, message: str, level: str = 'info', duration_ms: int = 5000, actions=None):
        try:
            notif = _NotificationWidget(message, level, duration_ms, parent=self._notification_container, actions=actions)
            self._notification_layout.insertWidget(self._notification_layout.count() - 1, notif)
            self._notifications.append(notif)
            notif.closed.connect(lambda: self._on_notification_closed(notif))
            notif.start()
            try:
                if getattr(self, '_notification_sound', None) is not None:
                    self._notification_sound.stop()
                    self._notification_sound.play()
                elif getattr(self, '_notification_player', None) is not None:
                    self._notification_player.stop()
                    self._notification_player.play()
            except Exception:
                pass
        except Exception:
            print(f"[NOTIF] {message}")

    def _on_notification_closed(self, notif):
        try:
            if notif in self._notifications:
                self._notifications.remove(notif)
            notif.deleteLater()
        except Exception:
            pass
        
    def create_title_bar(self):
        title_bar = QFrame()
        title_bar.setFixedHeight(50)
        title_bar.setStyleSheet(Styles.TITLE_BAR)

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(20, 0, 18, 0)

        title = QLabel("Project G07")
        title.setStyleSheet(f"""
            color: {Styles.TEXT};
            font-size: 18px;
            font-weight: bold;
        """)
        layout.addWidget(title)

        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
        status_widget.setFixedHeight(28)

        outer_bg = QFrame()
        outer_bg.setFixedSize(14, 14)
        outer_bg.setStyleSheet("background-color: transparent; border-radius: 7px;")
        from PyQt6.QtWidgets import QVBoxLayout as _QVBox
        _v = _QVBox(outer_bg)
        _v.setContentsMargins(3, 3, 3, 3)
        self.bot_status_inner = QFrame(outer_bg)
        self.bot_status_inner.setFixedSize(8, 8)
        self.bot_status_inner.setStyleSheet("background-color: #ff1744; border: none; border-radius: 4px;")
        _v.addWidget(self.bot_status_inner)
        status_layout.addWidget(outer_bg)

        self.bot_status_text = QLabel("Bot Offline")
        self.bot_status_text.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 12px;")
        status_layout.addWidget(self.bot_status_text)

        layout.addWidget(status_widget)

        self.bot_toggle_btn = QPushButton("  Start Bot")
        self.bot_toggle_btn.setFixedSize(140, 40)
        self.bot_toggle_btn.setStyleSheet(Styles.BUTTON_SECONDARY)
        self.bot_toggle_btn.clicked.connect(self.toggle_bot)
        self.bot_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6">  <path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />  <path stroke-linecap="round" stroke-linejoin="round" d="M15.91 11.672a.375.375 0 0 1 0 .656l-5.603 3.113a.375.375 0 0 1-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112Z" /></svg>'''
        stop_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6">  <path stroke-linecap="round" stroke-linejoin="round" d="M14.25 9v6m-4.5 0V9M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>'''

        def _make_icon(svg, px=18):
            if QSvgRenderer is None:
                return None
            try:
                pm = QPixmap(px, px)
                pm.fill(Qt.GlobalColor.transparent)
                r = QSvgRenderer(QByteArray(svg.encode('utf-8')))
                p = QPainter(pm)
                r.render(p)
                p.end()
                return QIcon(pm)
            except Exception:
                return None

        self._start_icon = _make_icon(start_svg, 20)
        self._stop_icon = _make_icon(stop_svg, 20)
        if self._start_icon:
            self.bot_toggle_btn.setIcon(self._start_icon)
            self.bot_toggle_btn.setIconSize(QSize(18, 18))
        layout.addWidget(self.bot_toggle_btn)

        layout.addStretch()

        btn_minimize = QPushButton("−")
        btn_close = QPushButton("✕")

        for btn in [btn_minimize, btn_close]:
            btn.setFixedSize(45, 35)
            btn.setStyleSheet(Styles.TITLE_BAR_BUTTON)

        btn_close.setStyleSheet(Styles.TITLE_BAR_BUTTON_CLOSE)

        svg_min = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6">  <path stroke-linecap="round" stroke-linejoin="round" d="M15 12H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>'''
        svg_close = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6">  <path stroke-linecap="round" stroke-linejoin="round" d="m9.75 9.75 4.5 4.5m0-4.5-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>'''

        def _svg_to_icon(svg_src, size_px=14):
            if QSvgRenderer is None:
                return None
            try:
                pix = QPixmap(size_px, size_px)
                pix.fill(Qt.GlobalColor.transparent)
                renderer = QSvgRenderer(QByteArray(svg_src.encode('utf-8')))
                p = QPainter(pix)
                renderer.render(p)
                p.end()
                return QIcon(pix)
            except Exception:
                return None

        icon_min = _svg_to_icon(svg_min, 21)
        icon_close = _svg_to_icon(svg_close, 21)
        if icon_min:
            btn_minimize.setIcon(icon_min)
            btn_minimize.setIconSize(QSize(21, 21))
            btn_minimize.setText("")
        if icon_close:
            btn_close.setIcon(icon_close)
            btn_close.setIconSize(QSize(21, 21))
            btn_close.setText("")

        btn_minimize.clicked.connect(self.showMinimized)
        btn_close.clicked.connect(self.close)

        layout.addWidget(btn_minimize)
        layout.addWidget(btn_close)

        return title_bar
    
    def create_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(Styles.SIDEBAR)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(15, 30, 15, 30)
        layout.setSpacing(10)
        self.nav_buttons = []

        svg_icons = {
            'Dashboard': f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6">  <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75" /></svg>''',
            'Builder': f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6">  <path stroke-linecap="round" stroke-linejoin="round" d="m21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" /></svg>''',
            'Clients': f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6">  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" /></svg>''',
            'Console': f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6">  <path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" /></svg>''',
            'Help': f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6">  <path stroke-linecap="round" stroke-linejoin="round" d="M10.05 4.575a1.575 1.575 0 1 0-3.15 0v3m3.15-3v-1.5a1.575 1.575 0 0 1 3.15 0v1.5m-3.15 0 .075 5.925m3.075.75V4.575m0 0a1.575 1.575 0 0 1 3.15 0V15M6.9 7.575a1.575 1.575 0 1 0-3.15 0v8.175a6.75 6.75 0 0 0 6.75 6.75h2.018a5.25 5.25 0 0 0 3.712-1.538l1.732-1.732a5.25 5.25 0 0 0 1.538-3.712l.003-2.024a.668.668 0 0 1 .198-.471 1.575 1.575 0 1 0-2.228-2.228 3.818 3.818 0 0 0-1.12 2.687M6.9 7.575V12m6.27 4.318A4.49 4.49 0 0 1 16.35 15m.002 0h-.002" /></svg>''',
            'Settings': f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{Styles.TEXT}" class="size-6">  <path stroke-linecap="round" stroke-linejoin="round" d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 0 1 1.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.559.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.894.149c-.424.07-.764.383-.929.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 0 1-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.398.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 0 1-.12-1.45l.527-.737c.25-.35.272-.806.108-1.204-.165-.397-.506-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.108-1.204l-.526-.738a1.125 1.125 0 0 1 .12-1.45l.773-.773a1.125 1.125 0 0 1 1.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894Z" />  <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /></svg>'''
        }

        def make_icon(svg_src, size=18):
            if QSvgRenderer is None:
                return QIcon()
            try:
                pix = QPixmap(size, size)
                pix.fill(Qt.GlobalColor.transparent)
                renderer = QSvgRenderer(QByteArray(svg_src.encode('utf-8')))
                p = QPainter(pix)
                renderer.render(p)
                p.end()
                return QIcon(pix)
            except Exception:
                return QIcon()

        nav_items = [
            ("Dashboard", 0),
            ("Builder", 1),
            ("Clients", 2),
            ("Console", 3),
            ("Help", 4),
            ("Settings", 5)
        ]

        for text, index in nav_items:
            btn = QPushButton(f"  {text}")
            btn.setFixedHeight(50)
            btn.setStyleSheet(Styles.NAV_BUTTON)
            icon = make_icon(svg_icons.get(text, ""), size=27)
            if not icon.isNull():
                btn.setIcon(icon)
                btn.setIconSize(QSize(27, 27))
            btn.clicked.connect(lambda checked, i=index: self.switch_page(i))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        self.indicator = QFrame(sidebar)
        self.indicator.setStyleSheet(f"background-color: {Styles.TEXT}; border-radius: 2px;")
        self.indicator.setGeometry(10, 30, 4, 50)
        self.indicator.raise_()

        if self.nav_buttons:
            self.nav_buttons[0].setStyleSheet(Styles.NAV_BUTTON_ACTIVE)
            self.current_btn = self.nav_buttons[0]
        else:
            self.current_btn = None
        
        layout.addStretch()
        
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet("""
            color: #6c757d;
            font-size: 12px;
        """)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
        return sidebar
    
    def switch_page(self, index):
        if index < 0 or index >= self.pages.count():
            return
        if self.current_btn:
            self.current_btn.setStyleSheet(Styles.NAV_BUTTON)
        self.nav_buttons[index].setStyleSheet(Styles.NAV_BUTTON_ACTIVE)
        new_btn = self.nav_buttons[index]
        self.current_btn = new_btn

        target_y = new_btn.pos().y()
        anim = QPropertyAnimation(self.indicator, b"geometry")
        anim.setDuration(350)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(self.indicator.geometry())
        anim.setEndValue(QRect(self.indicator.geometry().x(), target_y, self.indicator.width(), new_btn.height()))
        anim.start()
        self._indicator_anim = anim

        old_index = self.pages.currentIndex()
        if old_index != index:
            self.pages.setCurrentIndex(index)
            widget = self.pages.currentWidget()
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
            fade = QPropertyAnimation(effect, b"opacity")
            fade.setDuration(300)
            fade.setEasingCurve(QEasingCurve.Type.OutCubic)
            fade.setStartValue(0.0)
            fade.setEndValue(1.0)
            fade.start()
            self._fade_anim = fade

    def create_console_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(15)

        header = QLabel("Console Log")
        header.setStyleSheet(Styles.LABEL_TITLE)
        layout.addWidget(header)

        btn_row = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(Styles.BUTTON_SECONDARY)
        clear_btn.clicked.connect(self.clear_console)
        btn_row.addWidget(clear_btn)

        save_btn = QPushButton("Save Logs")
        save_btn.setStyleSheet(Styles.BUTTON_SECONDARY)
        save_btn.clicked.connect(self.save_console)
        btn_row.addWidget(save_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.console_edit = QTextEdit()
        self.console_edit.setReadOnly(True)
        self.console_edit.setStyleSheet("background-color: #161616; border:1px solid #222222; border-radius:10px; font-family: Consolas, monospace; font-size:12px; color:#f5f5f5;")
        layout.addWidget(self.console_edit, 1)

        return page

    def append_log(self, text: str):
        if not hasattr(self, 'console_edit'):
            return
        self.console_edit.append(text)

    def clear_console(self):
        if hasattr(self, 'console_edit'):
            self.console_edit.clear()

    def save_console(self):
        if not hasattr(self, 'console_edit'):
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Logs", "logs.txt", "Text Files (*.txt)")
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.console_edit.toPlainText())
            except Exception as e:
                print(f"Failed to save logs: {e}")
    
    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() < 50:
                self.dragging = True
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
    
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.dragging = False
    
    def auto_start_bot(self):
        if self.config.get('autostart_bot', False):
            token = self.config.get('bot_token')
            guild_id = self.config.get('guild_id')
            
            if token and guild_id:
                self.start_bot()
    
    def toggle_bot(self):
        if self.discord_bot and self.discord_bot.is_ready():
            self.stop_bot()
        else:
            self.start_bot()
    
    def start_bot(self):
        if self.discord_bot and self.discord_bot.is_ready():
            return
        
        token = self.config.get('bot_token')
        guild_id = self.config.get('guild_id')
        channel_name = self.config.get('control_channel', 'g07-control')
        
        if not token or not guild_id:
            try:
                self.show_notification("Configure Bot Token and Guild ID in Settings first", level='warn')
            except Exception:
                pass
            return
        
        try:
            if self.discord_bot:
                self.discord_bot.stop()
            
            self.discord_bot = DiscordBot(token, int(guild_id), channel_name)
            
            self.discord_bot.on_client_connect = self.on_client_connected
            self.discord_bot.on_screenshot = self.on_screenshot_received
            
            self.discord_bot.start()
            
            try:
                self.bot_status_inner.setStyleSheet("background-color: #00e676; border: none; border-radius: 4px;")
                self.bot_status_text.setText("Bot Online")
                self.bot_status_text.setStyleSheet(f"color: {Styles.TEXT}; font-size: 12px;")
            except Exception:
                pass

            if getattr(self, '_stop_icon', None):
                self.bot_toggle_btn.setIcon(self._stop_icon)
                self.bot_toggle_btn.setIconSize(QSize(18, 18))
            self.bot_toggle_btn.setText("Stop Bot")
            
            self.clients_page.discord_bot = self.discord_bot
            
            print("Bot started from GUI")
            self.append_log("[INFO] Bot started and online")
            try:
                self.show_notification("Bot started and online", level='success')
            except Exception:
                pass
            
        except Exception as e:
            try:
                self.show_notification(f"Failed to start bot: {str(e)}", level='error')
            except Exception:
                pass
    
    def stop_bot(self):
        if self.discord_bot:
            self.discord_bot.stop()
            self.discord_bot = None
        
        try:
            self.bot_status_inner.setStyleSheet("background-color: #ff1744; border: none; border-radius: 4px;")
            self.bot_status_text.setText("Bot Offline")
            self.bot_status_text.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 12px;")
        except Exception:
            pass

        if getattr(self, '_start_icon', None):
            self.bot_toggle_btn.setIcon(self._start_icon)
            self.bot_toggle_btn.setIconSize(QSize(18, 18))
            self.bot_toggle_btn.setText("Start Bot")
        print("⏸ Bot stopped")
        self.append_log("[INFO] Bot stopped")
        try:
            self.show_notification("Bot stopped", level='info')
        except Exception:
            pass
    
    def closeEvent(self, event):
        if self.discord_bot:
            self.stop_bot()
        event.accept()
    
    def on_client_connected(self, hostname: str, ip: str):
        from PyQt6.QtCore import QTimer

        def _handle():
            from datetime import datetime

            region = "Unknown"
            try:
                first_octet = int(ip.split('.')[0])
                if 192 <= first_octet <= 223:
                    region = "EU"
                elif 1 <= first_octet <= 100:
                    region = "US"
                elif 100 <= first_octet <= 150:
                    region = "AS"
            except:
                pass

            clients = self.config.get('clients', [])
            existing = None
            for client in clients:
                if client.get('ip') == ip:
                    existing = client
                    break

            if existing:
                existing['status'] = 'online'
                existing['last_ping'] = datetime.now().isoformat()
                existing['hostname'] = hostname
                if existing.get('hidden'):
                    try:
                        del existing['hidden']
                    except Exception:
                        existing['hidden'] = False
            else:
                new_client = {
                    'hostname': hostname,
                    'ip': ip,
                    'status': 'online',
                    'region': region,
                    'last_ping': datetime.now().isoformat(),
                    'first_seen': datetime.now().isoformat()
                }
                clients.append(new_client)

                today = datetime.now().strftime('%Y-%m-%d')
                history = self.config.get('client_history', {})
                history[today] = history.get(today, 0) + 1
                self.config.set('client_history', history)

            self.config.set('clients', clients)
            self.config.save()

            try:
                self.clients_page.refresh_clients()
                self.dashboard_page.update_stats()
            except Exception as e:
                print(f"Error refreshing UI: {e}")

            msg = f"Client online: {hostname} ({ip})"
            print(f"{msg}")
            self.append_log(f"[CLIENT] {msg}")

        QTimer.singleShot(0, _handle)
    
    def on_screenshot_received(self, hostname: str, image_url: str):
        import webbrowser, pathlib
        from PyQt6.QtCore import QTimer
        print(f"Screenshot received from {hostname}: {image_url}")
        self.append_log(f"[SCREENSHOT] from {hostname}: {image_url}")

        def _open():
            try:
                if image_url and pathlib.Path(image_url).exists():
                    webbrowser.open_new_tab(pathlib.Path(image_url).as_uri())
                else:
                    webbrowser.open_new_tab(image_url)
            except Exception as e:
                print(f"Failed to open screenshot in browser: {e}")

        QTimer.singleShot(0, _open)

class _NotificationWidget(QFrame):
    closed = pyqtSignal()
    def __init__(self, message: str, level: str, duration_ms: int, parent=None, actions=None):
        super().__init__(parent)
        self._duration = max(1500, duration_ms)
        self._remaining = self._duration
        self._progress = 1.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._progress_anim = None
        self._actions = actions or []
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet("background: transparent;")
        from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QProgressBar
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        card = QFrame()
        card.setObjectName("card")
        palette = {
            'info': ("#2196f3", Styles.TEXT),
            'warn': ("#ffb300", Styles.TEXT),
            'error': ("#e53935", Styles.TEXT),
            'success': ("#43a047", Styles.TEXT)
        }
        accent, text_col = palette.get(level, ("#2196f3", Styles.TEXT))
        card.setStyleSheet(f"""
            QFrame#card {{
                background-color: #181818;
                border: 1px solid #ffffff;
                border-radius: 18px;
            }}
            QLabel#msg {{ color: {text_col}; font-size:15px; line-height: 1.3em; }}
            QPushButton#close {{
                background: transparent;
                border: none;
                padding: 6px;
                border-radius: 8px;
            }}
            QProgressBar {{
                background: #2a2a2a;
                border: none;
                height: 3px;
                border-bottom-left-radius: 18px;
                border-bottom-right-radius: 18px;
            }}
            QProgressBar::chunk {{
                background: #ffffff;
                border-bottom-left-radius: 18px;
                border-bottom-right-radius: 18px;
            }}
        """)
        v = QVBoxLayout(card)
        v.setContentsMargins(20, 18, 20, 10)
        v.setSpacing(14)
        row = QHBoxLayout()
        row.setSpacing(16)
        bell_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="#ffffff" class="size-6"><path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0M3.124 7.5A8.969 8.969 0 0 1 5.292 3m13.416 0a8.969 8.969 0 0 1 2.168 4.5" /></svg>'''
        close_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="{text_col}" class="size-6"><path stroke-linecap="round" stroke-linejoin="round" d="m9.75 9.75 4.5 4.5m0-4.5-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>'''
        from PyQt6.QtWidgets import QLabel as _L
        icon_lbl = _L()
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setStyleSheet("background: transparent;")
        if QSvgRenderer is not None:
            try:
                pm = QPixmap(28, 28)
                pm.fill(Qt.GlobalColor.transparent)
                r = QSvgRenderer(QByteArray(bell_svg.encode('utf-8') if isinstance(bell_svg, str) else bell_svg))
                p = QPainter(pm)
                r.render(p)
                p.end()
                icon_lbl.setPixmap(pm)
            except Exception:
                pass
        row.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignTop)
        msg_lbl = QLabel(message)
        msg_lbl.setObjectName("msg")
        msg_lbl.setWordWrap(True)
        row.addWidget(msg_lbl, 1)
        close_btn = QPushButton()
        close_btn.setObjectName("close")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(36, 36)
        if QSvgRenderer is not None:
            try:
                pm2 = QPixmap(22, 22)
                pm2.fill(Qt.GlobalColor.transparent)
                r2 = QSvgRenderer(QByteArray(close_svg.encode('utf-8')))
                p2 = QPainter(pm2)
                r2.render(p2)
                p2.end()
                close_btn.setIcon(QIcon(pm2))
                close_btn.setIconSize(QSize(22, 22))
            except Exception:
                pass
        close_btn.clicked.connect(self._close_now)
        row.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
        v.addLayout(row)
        if self._actions:
            act_row = QHBoxLayout()
            act_row.setSpacing(10)
            from PyQt6.QtWidgets import QPushButton as _PB
            for label, cb in self._actions:
                b = _PB(label)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setStyleSheet("background-color: #ffffff12; color: #ffffff; border:1px solid #ffffff88; border-radius:8px; padding:6px 14px; font-size:13px;")
                def wrap(func=cb):
                    try:
                        func()
                    finally:
                        self._close_now()
                b.clicked.connect(wrap)
                act_row.addWidget(b)
            act_row.addStretch()
            v.addLayout(act_row)
        self._bar = QProgressBar()
        self._bar.setTextVisible(False)
        self._bar.setRange(0, 1000)
        self._bar.setValue(1000)
        v.addWidget(self._bar)
        outer.addWidget(card)
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._fade_anim = QPropertyAnimation(self._opacity, b"opacity")
        self._fade_anim.setDuration(220)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

    def start(self):
        try:
            from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
            anim = QPropertyAnimation(self._bar, b"value", self)
            anim.setStartValue(1000)
            anim.setEndValue(0)
            anim.setDuration(self._duration)
            anim.setEasingCurve(QEasingCurve.Type.Linear)
            anim.finished.connect(self._close_now)
            self._progress_anim = anim
            anim.start()
        except Exception:
            self._timer.start(50)

    def _tick(self):
        self._remaining -= 50
        if self._remaining <= 0:
            self._close_now()
            return
        self._progress = self._remaining / float(self._duration)
        self._bar.setValue(int(self._progress * 1000))

    def _close_now(self):
        self._timer.stop()
        fade = QPropertyAnimation(self._opacity, b"opacity")
        fade.setDuration(220)
        fade.setStartValue(self._opacity.opacity())
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.InOutCubic)
        fade.finished.connect(lambda: self._finalize())
        fade.start()
        self._fade_anim = fade

    def _finalize(self):
        self.hide()
        self.closed.emit()
