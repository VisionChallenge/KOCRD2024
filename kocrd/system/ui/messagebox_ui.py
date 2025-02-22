# kocrd/system/ui/messagebox_ui.py
from PyQt5.QtWidgets import QMessageBox

class MessageBoxUI:
    def __init__(self, messages, error_messages):
        self.messages = messages
        self.error_messages = error_messages

        self.setWindowTitle(self.messages["main_window"]["title"])
        self.setGeometry(100, 100, self.messages["main_window"]["size"]["width"], self.messages["main_window"]["size"]["height"])

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, 
            self.get_message("16"), 
            self.get_message("16"),
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.system_manager.database_packaging() # SystemManager에 위임
                logging.info("Database successfully packaged on close.")
            except Exception as e:
                logging.error(f"Error packaging database on close: {e}")
            event.accept()
        else:
            event.ignore()
