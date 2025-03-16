# kocrd/system/config/config_module.py
from calendar import c
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
from kocrd.system_manager.system_loder.file_utils import FileManager, show_message_box_safe
from kocrd.system_manager.temp_file_manager import TempFileManager
from kocrd.system_manager.main_ui import MainWindow
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

class LanguageController:
    def __init__(self, language_config_path="kocrd/system/config/language/loader_language.json"):
        self.language_packs = {}
        self.load_language_configs(language_config_path)
        self.current_language = "en"
        self.load_all_language_packs()

    def load_language_configs(self, config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.language_configs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading language config: {e}")
            self.language_configs = {}

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

    def load_all_language_packs(self):
        for lang_code, config in self.language_configs.items():
            lang_pack_path = config.get("language_pack")
            if lang_pack_path:
                self.load_language_pack(lang_code, lang_pack_path)

    def load_language_pack(self, lang_code, lang_pack_path):
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

    def determine_language(self, preferred_language=None):
        if preferred_language and preferred_language in self.language_packs:
            return preferred_language
        return list(self.language_packs.keys())[0] if self.language_packs else "en"

    def get_message(self, message_id: str, message_type: MessageType):
        lang_pack = self.language_packs.get(self.current_language)
        if lang_pack:
            messages = lang_pack.get("messages", {}).get(message_type.value, {})
            return messages.get(message_id, f"Message '{message_type.value}_{message_id}' not found.")
        return f"Language pack for '{self.current_language}' not found."

class MessageHandler:
    def __init__(self):
        self.config = Config
        self.language_controller = LanguageController()
        self.main_window = MainWindow()
        self.message_handlers = {
            MessageType.ERR: self._handle_error_message,
            MessageType.WARN: self._handle_warning_message,
            MessageType.LOG: self._handle_log_message,
            MessageType.MSG: self._handle_message,
            MessageType.ID: self._handle_message,
            MessageType.UI: self._handle_ui_message,
            MessageType.OCR: self._handle_ocr_message,
        }

    def handle_message(self, group: str, message_id: str, message_type: MessageType, data: dict = None):
        handler = self.message_handlers.get(message_type)
        if handler:
            handler(group, message_id, data)
        else:
            logging.warning(f"알 수 없는 메시지 타입: {message_type}")

    def _handle_error_message(self, message_id: str, data: dict = None):
        message = self.language_controller.get_message(message_id, MessageType.ERR)
        self.main_window.show_error_message(message)
        logging.error(message)

    def _handle_warning_message(self, message_id: str, data: dict = None):
        message = self.language_controller.get_message(message_id, MessageType.WARN)
        self.main_window.show_warning_message(message)
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
        logging.info(message)

    def _format_message(self, message: str, data: dict = None):
        if data:
            try:
                message = message.format(**data)
            except KeyError as e:
                logging.warning(f"메시지 포맷 오류: {e}")
        return message

    def set_main_window(self, main_window: MainWindow):
        self.main_window = main_window


class Config:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config_data = self.load_and_merge([config_file, "config/queues.json", "kocrd/config/message/messages.json"])
        self.managers_config = self.config_data.get("managers_config", {})
        self.temp_dir = self.config_data.get("file_paths", {}).get("temp_files")
        self.backup_dir = os.path.join(self.temp_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.file_manager = FileManager(self.temp_dir, self.backup_dir, [])
        self.language_controller = LanguageController()
        self.message_handler = MessageHandler()
        self.rabbitmq = RabbitMQConfig(self)
        self.file_paths = FilePathConfig(self)
        self.managers = {}
        self.manager_instances = {}
        self.initialize_managers()
        self.temp_file_manager = TempFileManager(self.file_manager)

    def load_and_merge(self, config_files):
        """설정 파일을 로드하고 병합합니다."""
        config_data = {}
        for file_path in config_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    config_data.update(file_data)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                self.link_text_processor("501", MessageType.ERR, exception=e, additional_message=f"설정 파일 로드 실패: {file_path}")
        return config_data

    def link_text_processor(self, message_id: str, message_type: MessageType, data: dict = None, exception=None, additional_message=None):
        """메시지 처리 요청을 MessageHandler에 전달하는 중계자 역할"""
        if message_type == MessageType.ERR and exception:
            message = self.language_controller.get_message(message_id, MessageType.ERR)
            if additional_message:
                message += f" - {additional_message}"
            log_message = message.format(error=exception)
            logging.error(log_message)
            show_message_box_safe(message.format(error=exception), "오류")
        else:
            message_type == MessageType.LOG and logging.info and logging.log(message_id, message_type, data)
            message = self.language_controller.get_message(message_id, MessageType.LOG)
        if message_type == MessageType.UI:
            self.message_handler.handle_message(message_id, MessageType.UI, data)
        else:
            self.message_handler.handle_message(message_id, message_type, data)

    def initialize_database(self, engine):
        try:
            config = self.get("database.init_queries")
            queries = [text(query) for query in config]
            with engine.connect() as conn:
                for query in queries:
                    conn.execute(query)
            logging.info("데이터베이스 초기화 성공")
        except (SQLAlchemyError, IOError, KeyError) as e:
            self.link_text_processor("525", MessageType.ERR, exception=e, additional_message="데이터베이스 초기화 실패")
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

    def set_language(self, language):
        self.language_controller.set_language(language)

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
                self.link_text_processor("manager_import_error", MessageType.ERR, exception=e, additional_message=f"매니저 '{manager_name}' 모듈 임포트 오류: {module_path}")
            except AttributeError as e:
                self.link_text_processor("manager_attribute_error", MessageType.ERR, exception=e, additional_message=f"매니저 '{manager_name}' 클래스 속성 오류: {class_name} in {module_path}")
            except Exception as e:
                self.link_text_processor("manager_initialization_error", MessageType.ERR, exception=e, additional_message=f"매니저 '{manager_name}' 초기화 오류")

    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        """AI 모델 실행 프로세스 트리거"""
        manager = self.manager_instances.get(process_type)
        if manager:
            try: manager.handle_process(data)
            except Exception as e: self.link_text_processor("517", MessageType.ERR, exception=e, additional_message=f"프로세스 '{process_type}' 실행 실패")
        elif process_type == "database_packaging":
            if hasattr(self, "temp_file"):
                try: self.temp_file.database_packaging()
                except Exception as e: self.link_text_processor("519", MessageType.ERR, exception=e, additional_message="데이터베이스 패키징 실패")
            else: self.link_text_processor("509", MessageType.ERR, exception="temp_file 매니저 인스턴스 없음")
        elif process_type == "ai_training":
            if hasattr(self, "ai_training"):
                try: self.ai_training.request_ai_training(data)
                except Exception as e: self.link_text_processor("518", MessageType.ERR, exception=e, additional_message="AI 학습 요청 실패")
            else: self.link_text_processor("524", MessageType.ERR, exception="ai_training 매니저 인스턴스 없음")
        elif process_type == "generate_text":
            if hasattr(self, "ai_prediction"):
                try: return self.ai_prediction.generate_text(data.get("command", ""))
                except Exception as e: self.link_text_processor("520", MessageType.ERR, exception=e, additional_message="텍스트 생성 실패")
            else: self.link_text_processor("524", MessageType.ERR, exception="ai_prediction 매니저 인스턴스 없음")

    def get_setting(self, setting_path):
        return self.get(setting_path)
    def create_ocr_engine(self, engine_type: str): # OCR 엔진 생성 로직
        try:
            pass
        except Exception as e:
            self.link_text_processor("516", MessageType.ERR, exception=e, additional_message=f"OCR 엔진 생성 실패: {engine_type}")
            return None

    def create_ai_model(self, model_type: str):
        try:
            # AI 모델 생성 로직
            pass
        except Exception as e:
            self.link_text_processor("520", MessageType.ERR, exception=e, additional_message=f"AI 모델 생성 실패: {model_type}")
            return None

    def load_tensorflow_model(self, model_path):
        try:
            model = tf.keras.models.load_model(model_path)
            logging.info(f"TensorFlow 모델 로딩 완료: {model_path}")
            return model
        except Exception as e:
            self.link_text_processor("511", MessageType.ERR, exception=e, additional_message=f"TensorFlow 모델 로드 실패: {model_path}")
            return None
    def load_gpt_model(self, gpt_model_path):
        try:
            logging.info("GPT 모델 로딩 중...")
            tokenizer = GPT2Tokenizer.from_pretrained(gpt_model_path)
            gpt_model = GPT2LMHeadModel.from_pretrained(gpt_model_path)
            logging.info(f"GPT 모델 로딩 완료: {gpt_model_path}")
            return tokenizer, gpt_model
        except Exception as e:
            self.link_text_processor("511", MessageType.ERR, exception=e, additional_message=f"GPT 모델 로드 실패: {gpt_model_path}")
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
            try:
                return handler()
            except Exception as e:
                self.link_text_processor("529", MessageType.ERR, exception=e, additional_message=f"파일 작업 '{operation}' 실패: {file_path}")
                return False
        else:
            self.link_text_processor("524", MessageType.ERR, exception=f"지원하지 않는 파일 작업: {operation}")
            return False

    def handle_db_exception(self, func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except SQLAlchemyError as e:
                self.link_text_processor("525", MessageType.ERR, exception=e, additional_message="데이터베이스 오류 발생")
                raise
        return wrapper

    def cleanup_all_temp_files(self, retention_time: int = 3600):
        try:
            return self.temp_file_manager.cleanup_all_temp_files(retention_time)
        except OSError as e:
            self.link_text_processor("507", MessageType.ERR, exception=e, additional_message="임시 파일 정리 실패")
            return False

    def cleanup_specific_files(self, files: Optional[List[str]]):
        try:
            return self.temp_file_manager.cleanup_specific_files(files)
        except OSError as e:
            self.link_text_processor("507", MessageType.ERR, exception=e, additional_message="임시 파일 정리 실패")
            return False

    def send_message(self, message):
        """지정된 큐에 메시지를 전송합니다."""
        try:
            queue_name = QUEUES["document_queue"]
            self.message_queue_manager.send_message(queue_name, message)
            logging.info(f"Message sent to queue '{queue_name}': {message}")
        except Exception as e:
            logging.error(self.message_handler.get_message("error.520", error=e))

    @handle_db_exception
    def execute_and_log(self, engine, query, params, success_message):
        try:
            with engine.connect() as conn:
                conn.execute(query, params)
            logging.info(success_message)
        except SQLAlchemyError as e:
            self.link_text_processor("513", MessageType.ERR, exception=e, additional_message="데이터베이스 쿼리 실패")
            raise

    @handle_db_exception
    def execute_and_fetch(self, engine, query, error_message, params=None):
        try:
            with engine.connect() as conn:
                result = conn.execute(query, params or {})
            return [dict(row) for row in result]
        except SQLAlchemyError as e:
            self.link_text_processor("513", MessageType.ERR, exception=e, additional_message="데이터베이스 쿼리 실패")
            raise

config = Config("config/development.json")
