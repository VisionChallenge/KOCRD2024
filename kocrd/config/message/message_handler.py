# kocrd/config/message/message_handler.py
import json
import logging
from typing import Callable, Dict, Optional, Any
import os

from kocrd.config.config import config
from kocrd.handlers.training_event_handler import TrainingEventHandler

class MessageHandler:
    def __init__(self, lang_dir="kocrd/config/language"):
        self.language_packs = self._load_language_packs(lang_dir)
        self.current_language = self._determine_language()
        self.training_event_handler = TrainingEventHandler()
        self.message_handlers: Dict[str, Callable[[str, Dict[str, Any]], None]] = {
            "MSG": self._handle_message,
            "LOG": self._handle_message,
            "WARN": self._handle_message,
            "ERR": self._handle_message,
            "ID": self._handle_message,
            "OCR": self._handle_message,
        }
        self.messages = self._load_messages("kocrd/config/message/messages.json") # 기본 메시지 로드

    def _load_json(self, file_path):  # 중복 코드 제거
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading JSON file {file_path}: {e}")
            return {}  # 빈 딕셔너리 반환하여 오류 처리
    def _load_language_packs(self, lang_dir):
        language_packs = {}
        for filename in os.listdir(lang_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(lang_dir, filename)
                try:
                    lang_pack = self._load_json(file_path)
                    language_code = lang_pack.get("language_code") # language_code 사용
                    if language_code:
                        language_packs[language_code] = lang_pack
                    else:
                        logging.warning(f"Language pack '{filename}' does not have 'language_code' attribute.")
                except json.JSONDecodeError:
                    logging.error(f"Error decoding JSON in '{filename}'.")
                except Exception as e:
                    logging.exception(f"An unexpected error occurred: {e}")
        return language_packs
    def get_message(self, message_id: str, *args, **kwargs) -> Optional[str]:
        lang_pack = self.language_packs.get(self.current_language)
        if not lang_pack:
            logging.error(f"Language pack for '{self.current_language}' not found.")
            return None # None 반환
        try:
            message = lang_pack.get(message_id)
            if message:
                return message.format(*args, **kwargs)
            else:
                message = self.messages.get(message_id)
                if message:
                    return message.format(*args, **kwargs)
                else:
                    logging.error(f"Message ID '{message_id}' not found in any language pack or default messages.")
                    return None # None 반환

        except Exception as e:
            logging.error(f"Error formatting message {message_id}: {e}")
            return None # None 반환
    def _handle_message(self, message_id, data, message_type):
        try:
            message = self.get_message(message_id, **data)
            if message_type == "LOG":
                logging.log(logging.INFO, message)
            elif message_type == "WARN":
                logging.warning(message)
            elif message_type == "ERR":
                logging.error(message)
            elif message_type == "ID":
                logging.info(message)
            elif message_type == "MSG":
                logging.info(message)
            elif message_type == "OCR":
                self.training_event_handler.handle_ocr_request(data.get("file_path"))
                logging.info(message)
        except Exception as e:
            logging.error(f"Error handling {message_type} message: {message_id} - {e}")
    def _load_messages(self, message_file_path): # 기본 메시지 로드 함수
        return self._load_json(message_file_path)
    def _determine_language(self):
        if config and config.get("ui.language"):
            preferred_language = config.get("ui.language")
            if preferred_language and preferred_language in self.language_packs:
                return preferred_language

        if not self.language_packs:
            logging.warning("No language packs found. Using default language 'en'.")
            return "en"
        return list(self.language_packs.keys())[0]
    def process_message(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            message_type = message.get("type")
            message_id = message.get("id")
            data = message.get("data", {})
            handler = self.message_handlers.get(message_type)

            if handler:
                handler(message_id, data, message_type)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                logging.warning(f"Unknown message type: {message_type}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True) # requeue=True 고려 (DLQ와 함께)

        except json.JSONDecodeError as e:
            logging.error(f"JSON 파싱 오류: {body} - {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logging.error(f"메시지 처리 중 오류: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    def _handle_log_message(self, message_type, message):
        log_function = getattr(logging, message_type.lower())
        log_function(message)
    def _handle_id_message(self, message):
        logging.info(message)
    def _handle_general_message(self, message):
        logging.info(message)
    def _handle_ocr_message(self, message, data):
        self.training_event_handler.handle_ocr_request(data.get("file_path"))
        logging.info(message)