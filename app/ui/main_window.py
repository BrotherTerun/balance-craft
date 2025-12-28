# app/ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QFrame,
    QListWidget,
    QLabel
)
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Game Analytics Workbench")
        self.resize(1200, 800)

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setFrameShape(QFrame.StyledPanel)

        sidebar_layout = QHBoxLayout(sidebar)

        menu = QListWidget()
        menu.addItems([
            "Overview",
            "Metrics",
            "Models",
            "Visualization"
        ])
        menu.setCurrentRow(3)

        sidebar_layout.addWidget(menu)

        # Placeholder central area
        placeholder = QLabel("Central workspace")
        placeholder.setAlignment(Qt.AlignCenter)

        layout.addWidget(sidebar)
        layout.addWidget(placeholder, 1)
