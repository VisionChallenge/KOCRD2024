# kocrd/config/loader.py
import json
import logging
import os
import re
import shutil
from typing import Callable, Dict, Optional, Any
from kocrd.utils.file_utils import FileManager, show_message_box_safe
import importlib
from kocrd.config.config import load_config, load_json, merge_configs, get_temp_dir
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text
import pika
import tensorflow as tf
from transformers import GPT2Tokenizer, GPT2LMHeadModel

class ConfigLoader:
    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        self.config_data = {}
        self.language_packs = {}
        self.current_language = "en"
        self.managers = {}
        self.load_language_packs("kocrd/config/language")
        self.load_messages("kocrd/config/message/messages.json")
        self.file_manager = FileManager(get_temp_dir(), config.get("backup_dir"), []) 

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
    def _message(self, key: str, *args, **kwargs) -> str:
        message = self.get_message(key) or "Unknown message"  # get_message 사용
        return message.format(*args, **kwargs) if message else "Unknown message"
    def _get_language_message(self, key: str) -> Optional[str]:
        lang_pack = self.language_packs.get(self.current_language)
        return lang_pack.get(key) if lang_pack else None
    def _get_default_message(self, key: str) -> Optional[str]:
        return self.messages.get(key)
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
    def create_ocr_engine(self, ocr_engine_type):
        # OCR 엔진 생성 로직 구현
        pass
    def create_ai_model(self, model_type):
        # 모델 생성 로직 구현
        pass
    def send_message_to_queue(self, handler_instance, queue_name, message):
        try:
            # 큐에 메시지 전송 로직 구현
            logging.info(f"Message sent to queue '{queue_name}': {message}")
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"RabbitMQ 연결 오류: {e}")
            raise
    def _process_ocr_request(self, message, data):
        file_path = data.get("file_path")
        logging.info(message)
    def load_and_merge(self, config_files: list):
        for file_path in config_files:
            config_data = self.file_manager.read_json(file_path)
            if config_data is None:
                continue
            self.config_data = self._merge_configs(self.config_data, config_data)
    def load_config_from_directory(self, directory: str) -> Dict:
        config_data = {}
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            loaded_data = self.file_manager.read_file(file_path)  # FileManager 사용
            if loaded_data is None:
                continue
            config_data = self._merge_configs(config_data, loaded_data)
        return config_data

    def get(self, key_path: str, default=None):
        def _get(data, keys):
            if not keys:
                return data
            key = keys[0]
            if isinstance(data, dict) and key in data:
                return _get(data[key], keys[1:])
            return default

        return _get(self.config, key_path.split("."))
    def validate(self, key_path: str, validator: callable, message: str):
        value = self.get(key_path)
        if not validator(value):
            raise ValueError(message)
    def get_rabbitmq_settings(self):
        return self.get("rabbitmq")
    def get_file_paths(self):
        return self.get("file_paths")
    def get_constants(self):
        return self.get("constants")
    def get_ui_settings(self):
        return self.get("ui.settings")
    def get_ui_id_mapping(self):
        return self.get("ui.id_mapping")
    def get_manager(self, manager_name):
        return self.managers.get(manager_name)
    def get_managers(self):
        return self.get("managers")
    def get_messages(self):
        return self.get("messages")
    def get_queues(self):
        return self.get("queues")
    def get_database_url(self):
        return self.get("database_url")
    def get_file_settings(self):
        return self.get("file_settings")
    def get_queue_name(self, queue_type: str) -> Optional[str]:
        queues = self.get("queues")
        if queues:
            return queues.get(queue_type)
        return None
    def get_setting(self, setting_path: str) -> Optional[Any]:
        return self.get(f"ui.settings.{setting_path}")
    def handle_error(self, category, code, exception=None, message=None):
        error_message_key = f"{category}_{code}"
        error_message = self._message(error_message_key)
        if message: error_message += f" - {message}"
        if exception:
            logging.exception(error_message)
        else:
            logging.error(error_message)

    def get_database_init_queries(self):
        return self.get("database.init_queries")
    def load_language_packs(self, lang_dir):
        for filename in os.listdir(lang_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(lang_dir, filename)
                lang_pack = self.file_manager.read_json(file_path)  # FileManager 사용
                language_code = lang_pack.get("language_code")
                if language_code:
                    self.language_packs[language_code] = lang_pack
                else:
                    logging.warning(f"Language pack '{filename}' does not have 'language_code' attribute.")
        self.current_language = self._determine_language()
    def load_messages(self, message_file_path):
        self.messages = self.file_manager.read_json(message_file_path)  # FileManager 사용
    def _merge_configs(self, config1: dict, config2: dict) -> dict:
        return merge_configs(config1, config2)
    def _determine_language(self):
        preferred_language = self.get("ui.language")
        if preferred_language and preferred_language in self.language_packs:
            return preferred_language
        return list(self.language_packs.keys())[0] if self.language_packs else "en" # 간략화
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
            logging.error(self._message("error.507", e=f"Unsupported operation: {operation}"))
            return False
    def initialize_database(self, engine):
        try:
            config = self.get("database.init_queries")
            queries = [text(query) for query in config]
            with engine.connect() as conn:
                for query in queries:
                    conn.execute(query)
            logging.info(self._message("db_init_success")) # 메시지 ID 사용
        except (SQLAlchemyError, IOError, KeyError) as e:
            logging.error(self._message("db_init_fail", error=e)) # 메시지 ID와 에러 정보 전달
            raise RuntimeError("Database initialization failed.") from e
    def handle_db_exception(self, func):
        """데이터베이스 예외 처리를 위한 데코레이터."""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except SQLAlchemyError as e:
                logging.error(f"Database error: {e}")
                raise
        return wrapper

    @handle_db_exception
    def execute_and_log(self, engine, query, params, success_message):
        """쿼리를 실행하고 성공 메시지를 로깅합니다."""
        with engine.connect() as conn:
            conn.execute(query, params)
        logging.info(success_message)

    @handle_db_exception
    def execute_and_fetch(self, engine, query, error_message, params=None):
        """쿼리를 실행하고 결과를 반환합니다."""
        with engine.connect() as conn:
            result = conn.execute(query, params or {})
            return [dict(row) for row in result]
    def load_tensorflow_model(self, model_path):
        try:
            model = tf.keras.models.load_model(model_path)
            logging.info(self._message("model_load_success", model_path=model_path))
            return model
        except Exception as e:
            self.handle_error("model_load_error", "505", exception=e, message=self._message("model_load_fail", model_path=model_path))
            return None

    def load_gpt_model(self, gpt_model_path):
        try:
            logging.info("GPT 모델 로딩 중...")
            tokenizer = GPT2Tokenizer.from_pretrained(gpt_model_path)
            gpt_model = GPT2LMHeadModel.from_pretrained(gpt_model_path)
            logging.info(f"GPT 모델 로딩 완료: {gpt_model_path}")
            return tokenizer, gpt_model
        except Exception as e:
            self.handle_error("gpt_model_load_error", "505", exception=e, message=f"GPT 모델 로드 실패: {gpt_model_path}")
            return None, None
    def initialize_managers(self):
        for manager_name, manager_config in self.get_managers().items():
            module_path = manager_config["module"]
            class_name = manager_config["class"]
            dependencies = manager_config.get("dependencies", [])
            kwargs = manager_config.get("kwargs", {})

            dependencies_instances = [
                self.managers[dep] for dep in dependencies
            ]

            try:
                module = __import__(module_path, fromlist=[class_name])
                manager_class = getattr(module, class_name)

                self.managers[manager_name] = manager_class(
                    *dependencies_instances, **kwargs
                )
            except ImportError as e:
                logging.error(self._message("error.import_error", module=module_path, error=e)) #_message 사용
            except AttributeError as e:
                logging.error(self._message("error.attribute_error", class_name=class_name, module=module_path, error=e)) #_message 사용
            except Exception as e:
                logging.error(self._message("error.manager_init_error", error=e)) #_message 사용

def get_message(message_id, error=None, **kwargs): # 전역 메시지 함수
    messages = {
        "501": "KeyError 발생: {error}",
        "505": "일반 오류 발생: {error}",
        "512": "JSON 디코딩 오류: {error}",
        "518": "OCR 엔진 오류: {error}",
        "error.import_error": "모듈 {module} 임포트 오류: {error}", # 추가
        "error.attribute_error": "모듈 {module}에서 클래스 {class_name}를 찾을 수 없음: {error}", # 추가
        "error.manager_init_error": "매니저 초기화 중 오류 발생: {error}", # 추가
        # 추가 메시지 ID와 메시지 매핑
    }
    message = messages.get(message_id, "알 수 없는 오류 발생")
    if error:
        message = message.format(error=error, **kwargs)
    return message