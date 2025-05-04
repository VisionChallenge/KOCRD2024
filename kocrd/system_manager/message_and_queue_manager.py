# kocrd/system_manager/message_and_queue_manager.py
import logging
import os
import configparser
from enum import Enum
from typing import Dict, Any, Optional
from kocrd.system_manager.system_loder.file_utils import show_message_box_safe


class MessageType(Enum):
    UI = "UI"
    MSG = "MSG"
    LOG = "LOG"
    WARN = "WARN"
    ERR = "ERR"
    ID = "ID"
    OCR = "OCR"


class RabbitMQConfig:
    def __init__(self, config):
        self.host = config.get("rabbitmq.host")
        self.port = config.get("rabbitmq.port")
        self.user = config.get("rabbitmq.user")
        self.password = config.get("rabbitmq.password")
        self.virtual_host = config.get("rabbitmq.virtual_host")
        self.exchange_name = config.get("rabbitmq.exchange_name", "")
        self.routing_key = config.get("rabbitmq.routing_key", "")
        self.events_queue = config.get("rabbitmq.events_queue")
        self.prediction_requests_queue = config.get("rabbitmq.prediction_requests_queue")
        self.prediction_results_queue = config.get("rabbitmq.prediction_results_queue")
        self.feedback_queue = config.get("rabbitmq.feedback_queue")


class LanguageController:
    def __init__(self, language_dir="kocrd/system_manager/config/language"):
        self.language_packs = {}
        self.language_dir = language_dir
        self.load_language_packs()
        self.current_language = self.determine_language()

    def load_language_packs(self):
        for filename in os.listdir(self.language_dir):
            if filename.endswith(".ini"):
                config = configparser.ConfigParser()
                file_path = os.path.join(self.language_dir, filename)
                try:
                    config.read(file_path, encoding='utf-8')
                    if "GENERAL" in config and "TEXT" in config:
                        lang_abbr = config["GENERAL"].get("LANGABBR")
                        if lang_abbr:
                            self.language_packs[lang_abbr] = config["TEXT"]
                        else:
                            logging.warning(f"언어팩 '{filename}'에 'LANGABBR'이 정의되지 않았습니다.")
                    else:
                        logging.warning(f"언어팩 '{filename}'의 구조가 올바르지 않습니다.")
                except configparser.Error as e:
                    logging.error(f"언어팩 '{filename}' 로딩 오류: {e}")
                except UnicodeDecodeError as e:
                    logging.error(f"언어팩 '{filename}' 인코딩 오류: {e}")

    def set_language(self, language_code):
        if language_code in self.language_packs:
            self.current_language = language_code
        else:
            logging.warning(f"언어 코드 '{language_code}'를 찾을 수 없습니다.")

    def determine_language(self, preferred_language=None):
        if preferred_language and preferred_language in self.language_packs:
            return preferred_language
        return list(self.language_packs.keys())[0] if self.language_packs else "kor"

    def get_message(self, message_id: str, message_type: MessageType, default_message=""):
        lang_pack = self.language_packs.get(self.current_language)
        if lang_pack and message_id in lang_pack:
            return lang_pack[message_id]
        else:
            logging.warning(f"메시지 ID '{message_id}'를 언어팩 '{self.current_language}'에서 찾을 수 없습니다.")
            return default_message


class MessageHandler:
    def __init__(self, config_instance, language_controller_instance):
        self.config = config_instance
        self.language_controller = language_controller_instance
        self.message_handlers = {
            MessageType.ERR: self._handle_error_message,
            MessageType.WARN: self._handle_warning_message,
            MessageType.LOG: self._handle_log_message,
            MessageType.MSG: self._handle_message,
            MessageType.ID: self._handle_message,
            MessageType.UI: self._handle_ui_message,
            MessageType.OCR: self._handle_ocr_message,
        }

    def handle_message(self, message_type: MessageType, message_id: str, data: Optional[Dict[str, Any]] = None, additional_message=None):
        handler = self.message_handlers.get(message_type)
        if handler:
            handler(message_id, data, additional_message)
        else:
            logging.warning(f"알 수 없는 메시지 타입: {message_type}")

    def _handle_error_message(self, message_id: str, data: Optional[Dict[str, Any]] = None, additional_message=None):
        message = self.language_controller.get_message(message_id, MessageType.ERR)
        if additional_message:
            message += f" - {additional_message}"
        logging.error(self._format_message(message, data))
        show_message_box_safe(self._format_message(message, data), "오류")

    def _handle_warning_message(self, message_id: str, data: Optional[Dict[str, Any]] = None):
        message = self.language_controller.get_message(message_id, MessageType.WARN)
        logging.warning(self._format_message(message, data))

    def _handle_log_message(self, message_id: str, data: Optional[Dict[str, Any]] = None):
        message = self.language_controller.get_message(message_id, MessageType.LOG)
        logging.info(self._format_message(message, data))

    def _handle_message(self, message_id: str, data: Optional[Dict[str, Any]] = None):
        message = self.language_controller.get_message(message_id, MessageType.MSG)
        logging.info(self._format_message(message, data))

    def _handle_ui_message(self, message_id: str, data: Optional[Dict[str, Any]] = None):
        message = self.language_controller.get_message(message_id, MessageType.UI)
        return self._format_message(message, data)

    def _handle_ocr_message(self, message_id: str, data: Optional[Dict[str, Any]] = None):
        message = self.language_controller.get_message(message_id, MessageType.OCR)
        logging.info(self._format_message(message, data))

    def _format_message(self, message: str, data: Optional[Dict[str, Any]] = None):
        if data:
            try:
                message = message.format(**data)
            except KeyError as e:
                logging.warning(f"메시지 포맷 오류: {e}")
        return message


class RabbitMQManager:
    def __init__(self, config):
        self.config = config
        self.rabbitmq_config = RabbitMQConfig(config)

    def send_message(self, queue_name: str, message: str):
        """지정된 큐에 메시지를 전송합니다."""
        try:
            # RabbitMQ 연결 및 메시지 전송 로직
            logging.info(f"Message sent to queue '{queue_name}': {message}")
        except Exception as e:
            logging.error(f"메시지 전송 실패: {e}")