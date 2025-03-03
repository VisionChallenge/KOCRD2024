# kocrd/system/config/config.py
import logging
import re
from typing import Dict, Any, List, Optional
import os
import json
from kocrd.system.config.loader import ConfigLoader
from kocrd.system.config.message.message_handler import MessageHandler
from kocrd.system.system_loder.file_utils import FileManager, show_message_box_safe
from kocrd.system.temp_file_manager import TempFileManager
from kocrd.system.ui.messagebox_ui import MessageBoxUI

class RabbitMQConfig:
    def __init__(self, config_loader: ConfigLoader):
        self.host = config_loader.get("rabbitmq.host")
        self.port = config_loader.get("rabbitmq.port")
        self.user = config_loader.get("rabbitmq.user")
        self.password = config_loader.get("rabbitmq.password")
        self.virtual_host = config_loader.get("rabbitmq.virtual_host")

class FilePathConfig:
    def __init__(self, config_loader: ConfigLoader):
        self.models = config_loader.get("file_paths.models")
        self.document_embedding = config_loader.get("file_paths.document_embedding")
        self.document_types = config_loader.get("file_paths.document_types")
        self.temp_files = config_loader.get("file_paths.temp_files")

class UIConfig:
    window_size_changed = pyqtSignal(str, int, int)
    splitter_moved = pyqtSignal(float)
    def __init__(self, config_file):
        self.config_file = config_file
        self.config_loader = ConfigLoader(self.config_file)
        self.config = self.load_config()

    def get(self, key_path, default=None):
        return self.config_loader.get(key_path, default)
    def get_window_setting(self, setting_type, area=None, key=None):
        """창 크기 설정을 가져옵니다."""
        if area and key:
            return self.config.get(f"window_settings.{setting_type}.{area}.{key}")
        elif area:
            return self.config.get(f"window_settings.{setting_type}.{area}")
        else:
            return self.config.get(f"window_settings.{setting_type}")
    def set_window_setting(self, setting_type, area, key, value):
        """창 크기 설정을 저장합니다."""
        self.config[f"window_settings.{setting_type}.{area}.{key}"] = value
        self.save_config()
    def set_splitter_ratio(self, ratio):
        """QSplitter 비율을 설정합니다."""
        self.set_window_setting("current", "document_area", "width_ratio", ratio)
        self.set_window_setting("current", "monitoring_area", "width_ratio", 1 - ratio)
    def get_splitter_ratio(self):
        """QSplitter 비율을 가져옵니다."""
        return self.get_window_setting("current", "document_area", "width_ratio")
    def load_config(self):
        """UI 설정을 로드합니다."""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"UI config file '{self.config_file}' not found.")
            return {}
        except json.JSONDecodeError:
            logging.error(f"UI config file '{self.config_file}' is not a valid JSON file.")
            return {}
    def get_min_size(self):
        """최소 창 크기를 가져옵니다."""
        min_width = self.get_window_setting("minimum", "width")
        min_height = self.get_window_setting("minimum", "height")
        return min_width if min_width else 500, min_height if min_height else 200
    def save_config(self):
        """UI 설정을 저장합니다."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving UI config file: {e}")

class Languageconfig:
    def __init__(self, config):
        self.config = config
        self.language_packs = {}

    def load_language_packs(self, lang_dir="kocrd/system/config/language"): #언어팩 경로 인수를 받음
        self.language_packs = {} #기존 언어팩 초기화
        for filename in os.listdir(lang_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(lang_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lang_pack = json.load(f)
                        language = lang_pack.get("language")
                        if language:
                            self.language_packs[language] = lang_pack
                        else:
                            logging.warning(f"Language pack '{filename}' does not have 'language' attribute.")
                except FileNotFoundError:
                    logging.error(f"Language pack '{filename}' not found.")
                except json.JSONDecodeError:
                    logging.error(f"Language pack '{filename}' is not a valid JSON file.")

    def get_message_text(self, message_type, collnumbur, language):
        lang_pack = self.language_packs.get(language)
        if lang_pack:
            messages = lang_pack.get("messages")  # "messages" 키로 메시지 딕셔너리 접근
            if messages:
                message_type_messages = messages.get(message_type)  # 메시지 타입별 딕셔너리 접근
                if message_type_messages:
                    message = message_type_messages.get(str(collnumbur))  # collnumbur를 문자열로 변환하여 접근
                    if message:
                        return message
                    else:
                        logging.warning(f"Message '{collnumbur}' not found in language pack '{language}' for type '{message_type}'.")
                        return None
                else:
                    logging.warning(f"Messages for type '{message_type}' not found in language pack '{language}'.")
                    return None
            else:
                logging.warning(f"Messages not found in language pack '{language}'.")
                return None
        else:
            logging.warning(f"Language pack '{language}' not found.")
            return None

    def determine_language(self):
        preferred_language = self.get("ui.language")
        if preferred_language and preferred_language in self.language_packs:
            return preferred_language
        return list(self.language_packs.keys())[0] if self.language_packs else "en"

class Config:
    def __init__(self, config_file):
        self.config_loader = ConfigLoader(config_file)  # ConfigLoader에 config_file 전달
        self.config_loader.load_and_merge([config_file, "config/queues.json", "kocrd/config/message/messages.json"])
        self.temp_dir = self.config_loader.get("file_paths.temp_files")
        self.backup_dir = os.path.join(self.temp_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.file_manager = FileManager(self.temp_dir, self.backup_dir, [])
        self.message_handler = MessageHandler(self.config_loader)  # MessageHandler 초기화
        self.rabbitmq = RabbitMQConfig(self.config_loader)
        self.file_paths = FilePathConfig(self.config_loader)
        self.ui = UIConfig(self.config_loader)
        self.managers = {}
        self.initialize_managers()
        self.temp_file_manager = TempFileManager(self.file_manager)
        self.language_config = Languageconfig(self)
        self.message_box_ui = MessageBoxUI(self)  # MessageBoxUI 인스턴스 생성, Config 인스턴스 전달

    def get(self, key_path, default=None):
        def _get(data, keys):
            if not keys:
                return data
            key = keys[0]
            if isinstance(data, dict) and key in data:
                return _get(data[key], keys[1:])
            return default

        return _get(self. get, key_path.split("."))
    
    def validate(self, key_path: str, validator: callable, message: str):
        self.config_loader.validate(key_path, validator, message)

    def set_language(self, language):
        self.current_language = language  # 현재 언어 설정

    def send_text(self, type, collnumbur):  # 메시지 ID 받도록 수정
        message = self.coll_text(type, collnumbur)  # 메시지 텍스트 가져오기
        if message:
            if type == "ERR":
                logging.error(message)
                self.message_box_ui.show_error_message(message)  # 에러 메시지 박스 표시
            elif type == "WARN":
                logging.warning(message)
                self.message_box_ui.show_warning_message(message)  # 경고 메시지 박스 표시
            elif type == "LOG":
                logging.info(message)
            elif type == "ID":
                logging.info(message)
            elif type == "MSG":
                logging.info(message)
            elif type == "OCR":
                self._process_ocr_request(message)  # OCR 처리
            elif type == "UI":
                return message  # UI 메시지 반환
            else:
                logging.info(message)  # 기본 메시지 처리
        else:
            logging.error(f"Message '{type}_{collnumbur}' not found.")  # 메시지 없을 경우 로그 출력

    def coll_text(self, type, collnumbur):
        message = self.language_config.get_message_text(type, collnumbur, self.current_language)
        if message:
            self.current_message = message  # 현재 메시지 저장
            return message
        else:
            return self.basic_language(type, collnumbur)  # 기본 언어로 메시지 조회

    def basic_language(self, type, collnumbur):
        message = self.language_config.get_message_text(type, collnumbur, self.language_config.determine_language())
        if message:
            self.current_message = message  # 현재 메시지 저장
            return message
        else:
            logging.error(f"Message '{type}_{collnumbur}' not found in any language pack.")
            return None  # 또는 기본 메시지 반환

    def _message(self, key: str, *args, **kwargs) -> str:
        message = self.get_message(key) or "Unknown message"
        return message.format(*args, **kwargs) if message else "Unknown message"
    def get_message(self, message_id: str, *args, **kwargs) -> Optional[str]:
        lang_pack = self.language_packs.get(self.current_language)
        if not lang_pack:
            logging.error(f"Language pack for '{self.current_language}' not found.")
            return None
        message = lang_pack.get(message_id) or self.messages.get(message_id)
        if message:
            return message.format(*args, **kwargs)
        logging.error(f"Message ID '{message_id}' not found.")
        return None

    def handle_document_exception(self, parent, category, code, exception, additional_message=None):
        return self.config_loader.handle_document_exception(parent, category, code, exception, additional_message)

    def handle_message(self, message_id, data, message_type):
        handlers = {
            "LOG": logging.info,
            "WARN": logging.warning,
            "ERR": logging.error,
            "ID": logging.info,
            "MSG": logging.info,
            "OCR": self._process_ocr_request,
        }
        handler = handlers.get(message_type)
        if handler:
            message = self._message(message_id, **data)
            handler(message, data) if message_type == "OCR" else handler(message)
        else:
            logging.warning(f"Unknown message type: {message_type}")

    def cleanup_all_temp_files(self, retention_time: int = 3600):
        return self.temp_file_manager.cleanup_all_temp_files(retention_time)

    def cleanup_specific_files(self, files: Optional[List[str]]):
        return self.temp_file_manager.cleanup_specific_files(files)

    def get_setting(self, setting_path):
        return self.config_loader.get_setting(setting_path)

    def create_ocr_engine(self, engine_type: str):
        return self.config_loader.create_ocr_engine(engine_type)

    def create_ai_model(self, model_type: str):
        return self.config_loader.create_ai_model(model_type)

    def load_tensorflow_model(self, model_path):
        return self.config_loader.load_tensorflow_model(model_path)
    def load_gpt_model(self, gpt_model_path):
        return self.config_loader.load_gpt_model(gpt_model_path)

    def initialize_managers(self, system_manager):
        return self.config_loader.initialize_managers(system_manager)

    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        return self.config_loader.trigger_process(process_type, data)

    def handle_error(self, category, code, exception, additional_message=None):
        return self.config_loader.handle_error(category, code, exception, additional_message)

    def send_message_to_queue(self, queue_name: str, message: dict):
        return self.config_loader.send_message_to_queue(queue_name, message)

config = Config("config/development.json")