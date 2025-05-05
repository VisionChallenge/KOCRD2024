# kocrd/system/ui/monitoring_ui.py
import json
import logging
from PyQt5.QtWidgets import QProgressBar, QTextEdit, QLineEdit, QListWidget, QVBoxLayout, QWidget, QPushButton
from sympy import Q
from kocrd.system_manager.config.config_module import Config
from kocrd.system_manager.ai_model_manager import AIModelManager
from kocrd.system_manager.document_manager import DocumentManager
class MonitoringUI(QWidget):
    def __init__(self, parent=None, config_path="config/ui.json"):
        super().__init__(parent)
        self.config = Config(config_path)
        self.ai_model_manager = AIModelManager()
        self.document_manager = DocumentManager(QProgressBar(), QTextEdit(), QLineEdit(), QListWidget())
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Log Display
        self.log_display = QTextEdit(self)
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)

        # Chat Output
        self.chat_output = QTextEdit(self)
        self.chat_output.setReadOnly(True)
        layout.addWidget(self.chat_output)

        # Chat Input
        self.chat_input = QLineEdit(self)
        layout.addWidget(self.chat_input)

        # Send Button
        self.send_button = QPushButton(self.config.link_text_processor("UI", "014"), self)
        self.send_button.clicked.connect(self.button_click_1)
        layout.addWidget(self.send_button)

        # Clear Button
        self.clear_button = QPushButton(self.config.link_text_processor("UI", "013"), self)
        self.clear_button.clicked.connect(self.button_click_2)
        layout.addWidget(self.clear_button)

        # File Import Button
        self.import_button = QPushButton(self.config.link_text_processor("UI", "015"), self)
        layout.addWidget(self.import_button)

        # OCR Execute Button
        self.ocr_button = QPushButton(self.config.link_text_processor("UI", "016"), self)
        layout.addWidget(self.ocr_button)

        self.setLayout(layout)
        self.load_ui_config()

    def button_click_1(self):
        message = self.chat_input.text()
        if message:
            self.chat_output.append(f"User: {message}")
            self.chat_input.clear()
            # AI 응답 생성 및 추가
            ai_response = self.ai_model_manager.generate_ai_response(message)
            self.chat_output.append(f"AI: {ai_response}")

    def button_click_2(self): # 파일 테이블을 초기화합니다
        self.document_manager.clear_table()

    def load_ui_config(self):
        """UI 설정을 로드하고 적용합니다."""
        try:
            components = self.config.get("components", {}).get("monitoring", {}).get("widgets", [])
            for component in components:
                if component.get("name") == "log_display":
                    self.log_display.setPlainText("")
                elif component.get("name") == "chat_output":
                    self.chat_output.setPlainText("")
                elif component.get("name") == "chat_input":
                    self.chat_input.setText("")
            logging.info(self.config.link_text_processor("LOG", "328"))
        except KeyError as e:
            logging.error(f"Error loading UI configuration: {e}")

    def append_log(self, message):
        """로그 메시지를 추가합니다."""
        self.log_display.append(message)

    def append_chat_output(self, message):
        """채팅 출력을 추가합니다."""
        self.chat_output.append(message)


def setup_monitoring_ui():
    # ...existing code...
    print(get_message(self.messages_config, "351"))  # Documents filtered successfully.
    # ...existing code...
    print(get_message(self.messages_config, "352"))  # Document search completed for keyword: {keyword}
    # ...existing code...
