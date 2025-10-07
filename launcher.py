import sys
import os

def check_requirements():
    required_packages = [
        'PyQt6',
        'discord',
        'PIL',
        'PyInstaller'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("Missing required packages:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\nRun: pip install -r requirements.txt")
        return False
    
    return True

def main():
    print("Starting Project G07...")
    print("=" * 50)
    
    if not check_requirements():
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont
        from gui.main_window import MainWindow
        
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        font = QFont("Segoe UI", 10)
        app.setFont(font)
        
        print("All checks passed!")
        print("Loading GUI...")
        
        window = MainWindow()
        window.show()
        
        print("Project G07 is ready!")
        print("=" * 50)
        
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"\nError starting application:")
        print(f"   {str(e)}")
        print("\nTry reinstalling requirements:")
        print("   pip install -r requirements.txt")
        input("\nPress Enter to exit...")
        sys.exit(1)

if __name__ == '__main__':
    main()
