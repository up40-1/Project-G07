"""
Sound Manager for notification sounds
"""
import os
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl

class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.load_sounds()
    
    def load_sounds(self):
        """Load sound files"""
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Load on.mp3
        on_path = os.path.join(base_path, "on.mp3")
        if os.path.exists(on_path):
            try:
                # QSoundEffect has spotty MP3 support; only use for wav/ogg
                if on_path.lower().endswith(('.wav', '.ogg')):
                    self.sounds['online'] = QSoundEffect()
                    self.sounds['online'].setSource(QUrl.fromLocalFile(on_path))
                    self.sounds['online'].setVolume(0.5)
            except Exception as e:
                pass  # Silently fail if sound can't be loaded
        
        # Load off.mp3
        off_path = os.path.join(base_path, "off.mp3")
        if os.path.exists(off_path):
            try:
                if off_path.lower().endswith(('.wav', '.ogg')):
                    self.sounds['offline'] = QSoundEffect()
                    self.sounds['offline'].setSource(QUrl.fromLocalFile(off_path))
                    self.sounds['offline'].setVolume(0.5)
            except Exception as e:
                pass  # Silently fail if sound can't be loaded
    
    def play(self, sound_name: str):
        """Play a sound"""
        if sound_name in self.sounds:
            try:
                self.sounds[sound_name].play()
            except Exception as e:
                print(f"Error playing sound: {e}")
