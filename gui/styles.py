class Styles:
    PRIMARY = "#ffffff"
    SECONDARY = "#c0c0c0"
    BACKGROUND = "#0d0d0d"
    CARD_BG = "#161616"
    HOVER = "#222222"
    TEXT = "#f5f5f5"
    TEXT_SECONDARY = "#9d9d9d"
    ACCENT = "#5c5c5c"
    SUCCESS = "#4caf50"
    ERROR = "#ef5350"
    WARNING = "#ffa726"
    
    MAIN_WINDOW = f"""
        QWidget {{
            background-color: {BACKGROUND};
            color: {TEXT};
            /* larger rounded corners for the whole app */
            border-radius: 20px;
        }}
    """
    
    TITLE_BAR = f"""
        QFrame {{
            background-color: {CARD_BG};
            /* rounded top corners to match main window */
            border-top-left-radius: 20px;
            border-top-right-radius: 20px;
        }}
    """
    
    TITLE_BAR_BUTTON = f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            color: {TEXT};
            font-size: 16px;
            border-radius: 5px;
        }}
        QPushButton:hover {{
            background-color: {HOVER};
        }}
    """
    
    TITLE_BAR_BUTTON_CLOSE = f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            color: {TEXT};
            font-size: 16px;
            border-radius: 5px;
        }}
        QPushButton:hover {{
            background-color: {ERROR};
        }}
    """
    
    SIDEBAR = f"""
        QFrame {{
            background-color: {CARD_BG};
            /* round both top-left and bottom-left corners for a pill-like tab bar */
            border-top-left-radius: 20px;
            border-bottom-left-radius: 20px;
        }}
    """
    
    NAV_BUTTON = f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            color: {TEXT_SECONDARY};
            text-align: left;
            padding-left: 20px;
            font-size: 14px;
            border-radius: 10px;
        }}
        QPushButton:hover {{
            background-color: {HOVER};
            color: {TEXT};
        }}
    """
    
    NAV_BUTTON_ACTIVE = f"""
        QPushButton {{
            background-color: {HOVER};
            border: 1px solid {ACCENT};
            color: {TEXT};
            text-align: left;
            padding-left: 20px;
            font-size: 14px;
            font-weight: bold;
            border-radius: 10px;
        }}
    """
    
    CARD = f"""
        QFrame {{
            background-color: {CARD_BG};
            /* slightly larger card corners for a softer look */
            border-radius: 18px;
            padding: 20px;
        }}
    """
    
    BUTTON = f"""
        QPushButton {{
            background-color: {HOVER};
            border: 1px solid {ACCENT};
            color: {TEXT};
            padding: 12px 30px;
            font-size: 14px;
            font-weight: 500;
            border-radius: 10px;
        }}
        QPushButton:hover {{
            background-color: {ACCENT};
        }}
        QPushButton:pressed {{
            background-color: {HOVER};
            padding: 13px 29px 11px 31px;
        }}
        QPushButton:disabled {{
            background-color: {HOVER};
            color: {TEXT_SECONDARY};
        }}
    """
    
    BUTTON_SECONDARY = f"""
        QPushButton {{
            background-color: transparent;
            border: 1px solid {ACCENT};
            color: {TEXT_SECONDARY};
            padding: 10px 28px;
            font-size: 14px;
            font-weight: 500;
            border-radius: 10px;
        }}
        QPushButton:hover {{
            background-color: {HOVER};
            color: {TEXT};
        }}
    """
    
    INPUT = f"""
        QLineEdit, QTextEdit, QSpinBox, QComboBox {{
            background-color: {HOVER};
            border: 1px solid {ACCENT};
            color: {TEXT};
            padding: 10px 15px;
            border-radius: 10px;
            font-size: 13px;
        }}
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border: 1px solid {TEXT_SECONDARY};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border: none;
        }}
    """
    
    TABLE = f"""
        QTableWidget {{
            background-color: {CARD_BG};
            border: 1px solid {ACCENT};
            border-radius: 15px;
            color: {TEXT};
            gridline-color: {ACCENT};
        }}
        QTableWidget::item {{
            padding: 10px;
            border: none;
        }}
        QTableWidget::item:selected {{
            background-color: {HOVER};
        }}
        QHeaderView::section {{
            background-color: {HOVER};
            color: {TEXT_SECONDARY};
            padding: 12px;
            border: none;
            font-weight: 600;
        }}
        QScrollBar:vertical {{
            background-color: {CARD_BG};
            width: 12px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {ACCENT};
            border-radius: 6px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {HOVER};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    """
    
    LABEL_TITLE = f"""
        QLabel {{
            color: {TEXT};
            font-size: 28px;
            font-weight: bold;
        }}
    """
    
    LABEL_SUBTITLE = f"""
        QLabel {{
            color: {TEXT_SECONDARY};
            font-size: 16px;
        }}
    """
    
    PROGRESS_BAR = f"""
        QProgressBar {{
            background-color: {HOVER};
            border: 1px solid {ACCENT};
            border-radius: 10px;
            text-align: center;
            color: {TEXT};
        }}
        QProgressBar::chunk {{
            background-color: {ACCENT};
            border-radius: 10px;
        }}
    """
