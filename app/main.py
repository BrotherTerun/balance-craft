import sys
import os
import json
import mysql.connector

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QObject, Slot, QUrl, Signal
from PySide6.QtWidgets import QFileDialog

from backend.progression_model import analyze_player
from backend.pipeline import run_pipeline

# Конфигурация подключения к MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '2256',
    'database': 'monitor_rpg_model'
}


class LogStream:

    def __init__(self, callback):
        self.callback = callback

    def write(self, message):

        if message.strip():
            self.callback(message)

    def flush(self):
        pass

class Backend(QObject):
    
    @Slot(result=str)
    def getPlayers(self):
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT DISTINCT player_id
            FROM sessions
        """)

        result = cursor.fetchall()

        return json.dumps(result)


    @Slot(str, result=str)
    def analyzePlayer(self, player_id):
        print("Запуск симуляции из Python")

        result = analyze_player(player_id=player_id)

        # Возвращаем JSON-строку
        return json.dumps(result)

    @Slot(result=str)
    def selectFolder(self):

        folder = QFileDialog.getExistingDirectory(
            None,
            "Выберите источник данных"
        )

        return folder

    @Slot(str, result=bool)
    def processPipeline(self, folder_path):

        try:
            run_pipeline(folder_path)
            return True

        except Exception as e:
            print("PIPELINE ERROR:", e)
            return False

    logSignal = Signal(str)

    def emitLog(self, message):

        self.logSignal.emit(message)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("BalanceCraft")
        self.resize(1400, 850)
        self.setMinimumSize(980, 620)

        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        self.channel = QWebChannel()
        self.backend = Backend()
        sys.stdout = LogStream(self.backend.emitLog)
        self.channel.registerObject("backend", self.backend)
        self.browser.page().setWebChannel(self.channel)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(base_dir, "ui", "index.html")
        self.browser.load(QUrl.fromLocalFile(html_path))


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())
