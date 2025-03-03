# kocrd/system/ui/messagebox_ui.py
from PyQt5.QtWidgets import QMessageBox, QApplication
import logging
from kocrd.system.config.config_module import Config
from kocrd.system.ui import MainWindow

class MessageBoxUI:
    def __init__(self, config):
        self.config = Config("config/development.json")

    def show_error_message(self, message):
        self.config.main_window.show_error_message(message)

    def show_question_message(self, message):
        return self.config.main_window.show_question_message(message)

    def show_warning_message(self, message):
        self.config.main_window.show_warning_message(message)

    def show_information_message(self, message):
        self.config.main_window.show_information_message(message)

    def show_confirmation_message(self, message):
        return self.config.main_window.show_confirmation_message(message)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, 
            self.config.coll_text("UI", "016"), 
            self.config.coll_text("UI", "016"),
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
