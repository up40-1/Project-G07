from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QFrame, QCheckBox,
                              QComboBox, QSpinBox)
from PyQt6.QtCore import Qt
from gui.styles import Styles
from utils.config_manager import ConfigManager

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        title = QLabel("Settings")
        title.setStyleSheet(Styles.LABEL_TITLE)
        layout.addWidget(title)
        
        discord_frame = QFrame()
        discord_frame.setStyleSheet(Styles.CARD)
        discord_layout = QVBoxLayout(discord_frame)
        discord_layout.setSpacing(20)
        
        section_title = QLabel("Discord Configuration")
        section_title.setStyleSheet("""
            color: #00d4ff;
            font-size: 18px;
            font-weight: bold;
        """)
        discord_layout.addWidget(section_title)
        
        token_label = QLabel("Bot Token:")
        token_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        discord_layout.addWidget(token_label)
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Enter your Discord bot token")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setStyleSheet(Styles.INPUT)
        self.token_input.setFixedHeight(45)
        discord_layout.addWidget(self.token_input)
        
        guild_label = QLabel("Guild ID:")
        guild_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        discord_layout.addWidget(guild_label)
        
        self.guild_input = QLineEdit()
        self.guild_input.setPlaceholderText("Enter your Discord server ID")
        self.guild_input.setStyleSheet(Styles.INPUT)
        self.guild_input.setFixedHeight(45)
        discord_layout.addWidget(self.guild_input)
        
        channel_label = QLabel("Control Channel:")
        channel_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        discord_layout.addWidget(channel_label)
        
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("Channel name (default: g07-control)")
        self.channel_input.setStyleSheet(Styles.INPUT)
        self.channel_input.setFixedHeight(45)
        discord_layout.addWidget(self.channel_input)
        
        layout.addWidget(discord_frame)
        
        app_frame = QFrame()
        app_frame.setStyleSheet(Styles.CARD)
        app_layout = QVBoxLayout(app_frame)
        app_layout.setSpacing(20)
        
        app_section_title = QLabel("Application Settings")
        app_section_title.setStyleSheet("""
            color: #00d4ff;
            font-size: 18px;
            font-weight: bold;
        """)
        app_layout.addWidget(app_section_title)
        
        refresh_layout = QHBoxLayout()
        
        refresh_label = QLabel("Auto Refresh Interval (seconds):")
        refresh_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        refresh_layout.addWidget(refresh_label)
        
        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(1, 60)
        self.refresh_spin.setValue(5)
        self.refresh_spin.setStyleSheet(Styles.INPUT)
        self.refresh_spin.setFixedHeight(40)
        self.refresh_spin.setFixedWidth(100)
        refresh_layout.addWidget(self.refresh_spin)
        
        refresh_layout.addStretch()
        app_layout.addLayout(refresh_layout)
        
        self.notifications_check = QCheckBox("Enable Desktop Notifications")
        self.notifications_check.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 5px;
                border: 2px solid #00d4ff;
            }
            QCheckBox::indicator:checked {
                background-color: #00d4ff;
            }
        """)
        self.notifications_check.setChecked(True)
        app_layout.addWidget(self.notifications_check)
        
        self.autostart_check = QCheckBox("Start Bot on Application Launch")
        self.autostart_check.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 5px;
                border: 2px solid #00d4ff;
            }
            QCheckBox::indicator:checked {
                background-color: #00d4ff;
            }
        """)
        self.autostart_check.setChecked(False)
        app_layout.addWidget(self.autostart_check)
        
        self.sound_check = QCheckBox("Play Sound on New Client Connection")
        self.sound_check.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 5px;
                border: 2px solid #00d4ff;
            }
            QCheckBox::indicator:checked {
                background-color: #00d4ff;
            }
        """)
        self.sound_check.setChecked(True)
        app_layout.addWidget(self.sound_check)
        
        layout.addWidget(app_frame)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("Save Settings")
        save_btn.setStyleSheet(Styles.BUTTON)
        save_btn.setFixedSize(200, 50)
        save_btn.clicked.connect(self.save_settings)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_layout.addWidget(save_btn)
        
        reset_btn = QPushButton("Reset to Default")
        reset_btn.setStyleSheet(Styles.BUTTON_SECONDARY)
        reset_btn.setFixedSize(200, 50)
        reset_btn.clicked.connect(self.reset_settings)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_layout.addWidget(reset_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
    
    def load_settings(self):
        self.token_input.setText(self.config.get('bot_token', ''))
        self.guild_input.setText(str(self.config.get('guild_id', '')))
        self.channel_input.setText(self.config.get('control_channel', 'g07-control'))
        self.refresh_spin.setValue(self.config.get('refresh_interval', 5))
        self.notifications_check.setChecked(self.config.get('notifications', True))
        self.autostart_check.setChecked(self.config.get('autostart_bot', False))
        self.sound_check.setChecked(self.config.get('sound_alerts', True))
    
    def save_settings(self):
        try:
            guild_id = self.guild_input.text().strip()
            if guild_id:
                guild_id = int(guild_id)
            
            self.config.set('bot_token', self.token_input.text().strip())
            self.config.set('guild_id', guild_id)
            self.config.set('control_channel', self.channel_input.text().strip() or 'g07-control')
            self.config.set('refresh_interval', self.refresh_spin.value())
            self.config.set('notifications', self.notifications_check.isChecked())
            self.config.set('autostart_bot', self.autostart_check.isChecked())
            self.config.set('sound_alerts', self.sound_check.isChecked())
            
            self.config.save()
            
            try:
                self.window().show_notification("Settings saved", level='success')
            except Exception:
                pass
            
        except ValueError:
            try:
                self.window().show_notification("Guild ID must be a number", level='warn')
            except Exception:
                pass
        except Exception as e:
            try:
                self.window().show_notification(f"Failed to save settings: {e}", level='error', duration_ms=7000)
            except Exception:
                pass
    
    def reset_settings(self):
        decided = {'go': False}
        def _confirm():
            decided['go'] = True
        try:
            self.window().show_notification(
                "Reset all settings to default?",
                level='warn',
                duration_ms=9000,
                actions=[("Yes", _confirm), ("Cancel", lambda: None)]
            )
        except Exception:
            pass
        from PyQt6.QtCore import QTimer
        def _apply():
            if decided['go']:
                self.token_input.setText('')
                self.guild_input.setText('')
                self.channel_input.setText('g07-control')
                self.refresh_spin.setValue(5)
                self.notifications_check.setChecked(True)
                self.autostart_check.setChecked(False)
                self.sound_check.setChecked(True)
                try:
                    self.window().show_notification("Settings reset", level='info')
                except Exception:
                    pass
        QTimer.singleShot(9100, _apply)
