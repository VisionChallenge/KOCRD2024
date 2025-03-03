import logging
import os
import json
from PyQt5.QtWidgets import QMainWindow, QWidget, QSplitter, QVBoxLayout, QMessageBox, QProgressBar
from PyQt5.QtCore import pyqtSignal
from window.document_ui_system import DocumentUISystem
from window.monitoring_ui_system import MonitoringUISystem
from kocrd.window.menubar_manager import MenubarManager
from kocrd.config.messages import messages

class MainWindow(QMainWindow):
    command_processed = pyqtSignal(str, str)  # (Command Text, AI Response) 신호

    def trigger_process(self, process_type, data=None):
        self.system_manager.trigger_process(process_type, data) # SystemManager에 위임

    def handle_command(self, command_text):
        """GPT 명령 처리."""
        if not command_text.strip():
            logging.warning("Command input field is empty.")
            return

        try:
            response = self.monitoring_ui_system.generate_ai_response(command_text)
            self.monitoring_ui_system.display_chat_response(response)
            self.command_processed.emit(command_text, response)
        except Exception as e:
            logging.error(self.get_error_message("02").format(error=e))
            QMessageBox.critical(self, "Command Error", self.get_error_message("02").format(error=e))

    def process_ocr_event(self, file_path):
        """OCR 이벤트 처리."""
        try:
            text = self.ocr_manager.extract_text(file_path)
            log_message = f"Extracted Text: {text}"
            self.monitoring_ui_system.display_log(log_message)
        except Exception as e:
            logging.error(self.get_error_message("03").format(error=e))
            QMessageBox.critical(self, "OCR Error", self.get_error_message("03").format(error=e))

    def handle_monitoring_event(self, event_type):
        """AI_Monitoring_event와 연동."""
        try:
            self.event_manager.handle_monitoring_event(event_type)
            logging.info(f"Monitoring event '{event_type}' handled successfully.")
        except Exception as e:
            logging.error(self.get_error_message("04").format(error=e))
            QMessageBox.critical(self, "Monitoring Event Error", self.get_error_message("04").format(error=e))

    def handle_chat(self, message):
        """사용자 메시지 처리."""
        try:
            if not message.strip():
                logging.warning("Empty message received.")
                return

            response = self.monitoring_ui_system.generate_ai_response(message)
            self.monitoring_ui_system.display_chat_message(message, response)

        except Exception as e:
            logging.error(self.get_error_message("05"))
            self.monitoring_ui_system.display_chat_message(message, self.get_error_message("05"))

    def display_document_content(self, text, source="AI"):
        """문서 내용 표시."""
        try:
            self.monitoring_ui_system.display_log(f"[{source}]:\n{text}\n")
            logging.info(f"Displayed content from {source}.")
        except Exception as e:
            logging.error(self.get_error_message("06").format(error=e))

    def load_config(self):
        """설정 파일을 로드하거나 기본 설정을 생성합니다."""
        print(messages["601"])  # Window configuration loaded successfully.
        return messages

    def get_message(self, key):
        """메시지 키를 통해 메시지를 가져옵니다."""
        return self.config.get(key, "메시지를 찾을 수 없습니다.")

    def get_error_message(self, key):
        """에러 메시지 키를 통해 에러 메시지를 가져옵니다."""
        return self.error_messages.get(key, "에러 메시지를 찾을 수 없습니다.")

# system_manager 모듈을 나중에 임포트
from system import SystemManager
