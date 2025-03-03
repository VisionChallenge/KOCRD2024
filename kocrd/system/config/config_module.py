# kocrd/system/config/config_module.py
import logging
import re
from typing import Dict, Any, List, Optional, Callable
import os
import json
import pika
import tensorflow as tf
from transformers import GPT2Tokenizer, GPT2LMHeadModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text
from kocrd.system.system_loder.file_utils import FileManager, show_message_box_safe
from kocrd.system.temp_file_manager import TempFileManager
from kocrd.system.ui.messagebox_ui import MessageBoxUI
from enum import Enum

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

class FilePathConfig:
    def __init__(self, config):
        self.models = config.get("file_paths.models")
        self.document_embedding = config.get("file_paths.document_embedding")
        self.document_types = config.get("file_paths.document_types")
        self.temp_files = config.get("file_paths.temp_files")

class UIConfig:
    def __init__(self, config):
        self.config = config.config_data.get("window_settings", {})
        self.config_instance = config  # Config 인스턴스 저장

    def get_window_setting(self, setting_type, area=None, key=None):
        if area and key:
            return self.config.get(setting_type, {}).get(area, {}).get(key)
        elif area:
            return self.config.get(setting_type, {}).get(area)
        else:
            return self.config.get(setting_type)

    def set_window_setting(self, setting_type, area, key, value):
        self.config[setting_type][area][key] = value
        self.config_instance.save_config()  # Config 클래스의 save_config 메소드 사용

    def set_splitter_ratio(self, ratio):
        self.set_window_setting("current", "document_area", "width_ratio", ratio)
        self.set_window_setting("current", "monitoring_area", "width_ratio", 1 - ratio)

    def get_splitter_ratio(self):
        return self.get_window_setting("current", "document_area", "width_ratio")

    def get_min_size(self):
        min_width = self.get_window_setting("minimum", "width")
        min_height = self.get_window_setting("minimum", "height")
        return min_width if min_width else 500, min_height if min_height else 200

class LanguageController:
    def __init__(self, language_config_path="kocrd/system/config/language/loader_language.json"):
        self.language_packs = {}
        self.language_configs = self._load_language_configs(language_config_path)
        self.current_language = "en"
        self._load_all_language_packs()

    # ConfigLoader.load_language_packs -> LanguageController로 이동 및 수정
    def load_language_packs(self, lang_dir):
        for filename in os.listdir(lang_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(lang_dir, filename)
                lang_pack = json.load(open(file_path, "r", encoding="utf-8"))
                language_code = lang_pack.get("language_code")
                if language_code:
                    self.language_packs[language_code] = lang_pack
                else:
                    logging.warning(f"Language pack '{filename}' does not have 'language_code' attribute.")
        self.current_language = self.determine_language()
    # ConfigLoader.load_messages -> LanguageController로 이동 및 수정
    def load_messages(self, message_file_path):
        try:
            with open(message_file_path, "r", encoding="utf-8") as f:
                self.messages = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading messages: {e}")

    def _load_language_configs(self, config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading language config: {e}")
            return {}

    def _load_all_language_packs(self):
        for lang_code, config in self.language_configs.items():
            lang_pack_path = config.get("language_pack")
            if lang_pack_path:
                self._load_language_pack(lang_code, lang_pack_path)

    def _load_language_pack(self, lang_code, lang_pack_path):
        try:
            with open(lang_pack_path, "r", encoding="utf-8") as f:
                self.language_packs[lang_code] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading language pack: {e}")

    def set_language(self, language_code):
        if language_code in self.language_packs:
            self.current_language = language_code
        else:
            logging.warning(f"Language code '{language_code}' not found.")

    def get_message(self, message_id: str, message_type: MessageType):
        lang_pack = self.language_packs.get(self.current_language)
        if lang_pack:
            messages = lang_pack.get("messages", {}).get(message_type, {})
            return messages.get(message_id, f"Message '{message_type}_{message_id}' not found.")
        return f"Language pack for '{self.current_language}' not found."

    def determine_language(self, preferred_language=None):
        if preferred_language and preferred_language in self.language_packs:
            return preferred_language
        return list(self.language_packs.keys())[0] if self.language_packs else "en"

class MessageHandler:
    def __init__(self, config):
        self.config = config
        self.language_controller = LanguageController()
        self.message_box_ui = MessageBoxUI(config)
        self.message_handlers = {
            MessageType.ERR: self._handle_error_message,
            MessageType.WARN: self._handle_warning_message,
            MessageType.LOG: self._handle_log_message,
            MessageType.MSG: self._handle_message,
            MessageType.ID: self._handle_message,
            MessageType.UI: self._handle_ui_message,
            MessageType.OCR: self._handle_ocr_message,
        }

    def handle_message(self, message_id: str, message_type: MessageType, data: dict = None):
        handler = self.message_handlers.get(message_type)
        if handler:
            handler(message_id, data)
        else:
            logging.warning(f"알 수 없는 메시지 타입: {message_type}")

    def _handle_error_message(self, message_id: str, data: dict = None):
        message = self.language_controller.get_message(message_id, MessageType.ERR)
        self.message_box_ui.show_error_message(message)
        logging.error(message)

    def _handle_warning_message(self, message_id: str, data: dict = None):
        message = self.language_controller.get_message(message_id, MessageType.WARN)
        self.message_box_ui.show_warning_message(message)
        logging.warning(message)

    def _handle_log_message(self, message_id: str, data: dict = None):
        message = self.language_controller.get_message(message_id, MessageType.LOG)
        logging.info(message)

    def _handle_message(self, message_id: str, data: dict = None):
        message = self.language_controller.get_message(message_id, MessageType.MSG)
        logging.info(message)

    def _handle_ui_message(self, message_id: str, data: dict = None):
        message = self.language_controller.get_message(message_id, MessageType.UI)
        return message

    def _handle_ocr_message(self, message_id: str, data: dict = None):
        message = self.language_controller.get_message(message_id, MessageType.OCR)
        # OCR 메시지 처리 로직 구현
        logging.info(message)

class Config:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config_data = self.load_and_merge([config_file, "config/queues.json", "kocrd/config/message/messages.json"])
        self.temp_dir = self.config_data.get("file_paths", {}).get("temp_files")
        self.backup_dir = os.path.join(self.temp_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.file_manager = FileManager(self.temp_dir, self.backup_dir, [])
        self.language_controller = LanguageController()
        self.message_handler = MessageHandler(self)
        self.rabbitmq = RabbitMQConfig(self)
        self.file_paths = FilePathConfig(self)
        self.ui = UIConfig(self)
        self.managers = {}
        self.manager_instances = {}
        self.initialize_managers()
        self.temp_file_manager = TempFileManager(self.file_manager)
        self.message_box_ui = MessageBoxUI(self)
    def load_and_merge(self, config_files):
        config_data = {}
        for file_path in config_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    config_data.update(file_data)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logging.error(f"Error loading config file {file_path}: {e}")
        return config_data
    def initialize_database(self, engine):
        try:
            config = self.get("database.init_queries")
            queries = [text(query) for query in config]
            with engine.connect() as conn:
                for query in queries:
                    conn.execute(query)
            logging.info("데이터베이스 초기화 성공")
        except (SQLAlchemyError, IOError, KeyError) as e:
            self.handle_error("db_init_fail", "508", exception=e, additional_message="데이터베이스 초기화 실패")
            raise RuntimeError("Database initialization failed.") from e
    def get(self, key_path, default=None):
        keys = key_path.split(".")
        data = self.config_data
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default
        return data
    def validate(self, key_path, validator, message):
        value = self.get(key_path)
        if not validator(value):
            raise ValueError(message)
    def set_language(self, language):
        self.language_controller.set_language(language)
    def send_text(self, message_id: str, message_type: MessageType, data: dict = None):
        self.message_handler.handle_message(message_id, message_type, data)
    def _process_ocr_request(self, message, data):
        file_path = data.get("file_path")
        logging.info(message)
    def initialize_managers(self):
        system_manager = self
        managers_config = self.config_data.get("managers", {})
        for manager_name, manager_config in managers_config.items():
            module_path = manager_config["module"]
            class_name = manager_config["class"]
            dependencies = manager_config.get("dependencies", [])
            kwargs = manager_config.get("kwargs", {})

            dependencies_instances = [self.manager_instances.get(dep) or getattr(system_manager, dep, None) for dep in dependencies]

            try:
                module = __import__(module_path, fromlist=[class_name])
                manager_class = getattr(module, class_name)

                instance = manager_class(*[dep for dep in dependencies_instances if dep is not None], **kwargs)
                self.manager_instances[manager_name] = instance
                setattr(self, manager_name, instance)
            except ImportError as e:
                logging.error(f"모듈 임포트 오류: {module_path} - {e}")
            except AttributeError as e:
                logging.error(f"클래스 속성 오류: {class_name} in {module_path} - {e}")
            except Exception as e:
                logging.error(f"매니저 초기화 오류: {e}")
    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        """AI 모델 실행 프로세스 트리거"""
        manager = self.manager_instances.get(process_type)
        if manager:
            manager.handle_process(data)
        elif process_type == "database_packaging":
            if hasattr(self, "temp_file"):
                self.temp_file.database_packaging()
            else:
                logging.error("temp_file 매니저 인스턴스 없음")
        elif process_type == "ai_training":
            if hasattr(self, "ai_training"):
                self.ai_training.request_ai_training(data)
            else:
                logging.error("ai_training 매니저 인스턴스 없음")
        elif process_type == "generate_text":
            if hasattr(self, "ai_prediction"):
                return self.ai_prediction.generate_text(data.get("command", ""))
            else:
                logging.error("ai_prediction 매니저 인스턴스 없음")
        else:
            logging.warning(f" 알 수 없는 프로세스 유형: {process_type}")
    def handle_error(self, category, code, exception, additional_message=None):
        message_id = f"{category}_{code}"
        error_message = self.config_data.get("messages", {}).get(message_id, "알 수 없는 오류")
        if additional_message:
            error_message += f" - {additional_message}"
        log_message = error_message.format(error=exception)
        logging.error(log_message)
        show_message_box_safe(error_message.format(error=exception), "오류")
    def handle_document_exception(self, parent, category, code, exception, additional_message=None):
        message_id = f"{category}_{code}"
        error_message = self.config_data.get("messages", {}).get(message_id, "알 수 없는 오류")
        if additional_message:
            error_message += f" - {additional_message}"
        log_message = error_message.format(error=exception)
        logging.error(log_message)
        show_message_box_safe(error_message.format(error=exception), "오류")
        return log_message
    def get_setting(self, setting_path):
        return self.get(setting_path)
    def create_ocr_engine(self, engine_type: str):
        pass
    def create_ai_model(self, model_type: str):
        # AI 모델 생성 로직 구현 (현재는 pass)
        pass
    def load_tensorflow_model(self, model_path):
        try:
            model = tf.keras.models.load_model(model_path)
            logging.info(f"TensorFlow 모델 로딩 완료: {model_path}")
            return model
        except Exception as e:
            self.handle_error("model_load_error", "505", exception=e, additional_message=f"TensorFlow 모델 로드 실패: {model_path}")
            return None
    def load_gpt_model(self, gpt_model_path):
        try:
            logging.info("GPT 모델 로딩 중...")
            tokenizer = GPT2Tokenizer.from_pretrained(gpt_model_path)
            gpt_model = GPT2LMHeadModel.from_pretrained(gpt_model_path)
            logging.info(f"GPT 모델 로딩 완료: {gpt_model_path}")
            return tokenizer, gpt_model
        except Exception as e:
            self.handle_error("gpt_model_load_error", "505", exception=e, additional_message=f"GPT 모델 로드 실패: {gpt_model_path}")
            return None, None
    def handle_file_operation(self, operation: str, file_path: str, content=None, destination=None, file_type: str = "auto"):
        file_handlers = {
            "read": lambda: self.file_manager.read_file(file_path, file_type),
            "write": lambda: self.file_manager.write_file(file_path, content, file_type),
            "copy": lambda: self.file_manager.copy_file(file_path, destination),
            "move": lambda: self.file_manager.move_file(file_path, destination),
            "delete": lambda: self.file_manager.delete_file(file_path),
            "exists": lambda: self.file_manager.file_exists(file_path),
        }
        handler = file_handlers.get(operation)
        if handler:
            return handler()
        else:
            self.handle_error("error", "507", exception=f"Unsupported operation: {operation}")
            return False
    def handle_db_exception(self, func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except SQLAlchemyError as e:
                logging.error(f"Database error: {e}")
                raise
        return wrapper
    def cleanup_all_temp_files(self, retention_time: int = 3600):
        return self.temp_file_manager.cleanup_all_temp_files(retention_time)
    def cleanup_specific_files(self, files: Optional[List[str]]):
        return self.temp_file_manager.cleanup_specific_files(files)
    @handle_db_exception
    def execute_and_log(self, engine, query, params, success_message):
        with engine.connect() as conn:
            conn.execute(query, params)
        logging.info(success_message)

    @handle_db_exception
    def execute_and_fetch(self, engine, query, error_message, params=None):
        """쿼리를 실행하고 결과를 반환합니다."""
        with engine.connect() as conn:
            result = conn.execute(query, params or {})
            return [dict(row) for row in result]
config = Config("config/development.json")