import requests
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                              QHBoxLayout, QScrollArea)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from gui.styles import Styles
import os
from datetime import datetime

class ImageLoader(QThread):
    finished = pyqtSignal(QPixmap)
    error = pyqtSignal(str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
    
    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            
            if not pixmap.isNull():
                self.finished.emit(pixmap)
            else:
                self.error.emit("Failed to load image")
        except Exception as e:
            self.error.emit(str(e))

class ScreenshotDialog(QDialog):
    def __init__(self, parent, hostname: str, image_url: str):
        super().__init__(parent)
        self.hostname = hostname
        self.image_url = image_url
        self.current_pixmap = None
        
        self.setWindowTitle(f"Screenshot - {hostname}")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(f"background-color: {Styles.BACKGROUND};")
        
        self.init_ui()
        self.load_image()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_label = QLabel(f"Screenshot from {self.hostname}")
        title_label.setStyleSheet("""
            color: #00d4ff;
            font-size: 18px;
            font-weight: bold;
        """)
        layout.addWidget(title_label)
        
        time_label = QLabel(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        time_label.setStyleSheet("""
            color: #8b92a7;
            font-size: 13px;
        """)
        layout.addWidget(time_label)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 2px solid {Styles.PRIMARY};
                border-radius: 10px;
                background-color: {Styles.CARD_BG};
            }}
        """)
        
        self.image_label = QLabel("Loading screenshot...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            color: #ffffff;
            padding: 20px;
            font-size: 14px;
        """)
        
        scroll.setWidget(self.image_label)
        layout.addWidget(scroll, 1)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(Styles.BUTTON_SECONDARY)
        save_btn.setFixedSize(120, 40)
        save_btn.clicked.connect(self.save_image)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_layout.addWidget(save_btn)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(Styles.BUTTON_SECONDARY)
        close_btn.setFixedSize(120, 40)
        close_btn.clicked.connect(self.close)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def load_image(self):
        if os.path.exists(self.image_url):
            pix = QPixmap(self.image_url)
            if not pix.isNull():
                self.on_image_loaded(pix)
                return
        self.loader = ImageLoader(self.image_url)
        self.loader.finished.connect(self.on_image_loaded)
        self.loader.error.connect(self.on_image_error)
        self.loader.start()
    
    def on_image_loaded(self, pixmap):
        scaled_pixmap = pixmap.scaled(
            1200, 900,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled_pixmap)
        self.current_pixmap = pixmap
    
    def on_image_error(self, error):
        self.image_label.setText(f"Failed to load screenshot:\n{error}")
        self.image_label.setStyleSheet("""
            color: #ff1744;
            padding: 20px;
            font-size: 14px;
        """)
    
    def save_image(self):
        from PyQt6.QtWidgets import QFileDialog
        
        if not hasattr(self, 'current_pixmap'):
            return
        
        screenshots_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = f"{self.hostname}_{timestamp}.png"
        default_path = os.path.join(screenshots_dir, default_filename)
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Screenshot",
            default_path,
            "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*.*)"
        )
        
        if filename:
            try:
                self.current_pixmap.save(filename)
                self.image_label.setWindowTitle(f"Screenshot - {self.hostname} (Saved)")
                
                try:
                    self.window().show_notification(f"Screenshot saved: {filename}", level='success', duration_ms=6000)
                except Exception:
                    pass
            except Exception as e:
                try:
                    self.window().show_notification(f"Failed to save screenshot: {e}", level='error', duration_ms=7000)
                except Exception:
                    pass
