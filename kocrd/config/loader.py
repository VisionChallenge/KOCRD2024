# kocrd/config/loader.py
import json
import logging
import os
import shutil  # 추가
from typing import Callable, Dict, Optional, Any
from kocrd.utils.file_utils import show_message_box_safe
import importlib  # 모듈 동적 로딩을 위한 import
from kocrd.config.config import load_config, load_json, merge_configs, get_temp_dir
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text  # 추가
import pika
import tensorflow as tf  # 추가
from transformers import GPT2Tokenizer, GPT2LMHeadModel  # 추가

class ConfigLoader:
    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        self.config_data = {}
        self.language_packs = {}
        self.current_language = "en"
        self.load_language_packs("kocrd/config/language")
        self.load_messages("kocrd/config/message/messages.json")

    def _load(self, file_path):
        return load_json(file_path)

    def _merge_configs(self, config1: dict, config2: dict) -> dict:
        return merge_configs(config1, config2)

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

    def handle_message(self, handler_instance, message_id, data, message_type):
        try:
            message = handler_instance.get_message(message_id, **data)
            if message_type in ["LOG", "WARN", "ERR", "ID", "MSG"]:
                log_function = getattr(logging, message_type.lower())
                log_function(message)
            elif message_type == "OCR":
                handler_instance.process_ocr_request(data.get("file_path"))
                logging.info(message)
        except Exception as e:
            logging.error(f"Error handling {message_type} message: {message_id} - {e}")

    def load_and_merge(self, config_files: list):
        for file_path in config_files:
            config_data = self._load(file_path)
            if "error" in config_data:
                self.handle_error(logging, "config_error", "512", config_data["message"])  # config_data["error"] -> config_data["message"]
                continue
            self.config_data = self._merge_configs(self.config_data, config_data)

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

    def get_queue_name(self, queue_type: str) -> Optional[str]:
        queues = self.get("queues")
        if queues:
            return queues.get(queue_type)
        return None

    def get_setting(self, setting_path: str) -> Optional[Any]:
        return self.get(f"ui.settings.{setting_path}")

    def handle_error(self, system_manager, category, code, exception, message=None):
        error_message_key = f"{category}_{code}"
        error_message = self.get_message(error_message_key)

        if message:
            error_message += f" - {message}"

        if exception:
            logging.exception(error_message)
        else:
            logging.error(error_message)

        if system_manager:
            system_manager.handle_error(error_message, error_message_key)

    def get_database_init_queries(self):
        return self.get("database.init_queries")

    def load_language_packs(self, lang_dir):
        for filename in os.listdir(lang_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(lang_dir, filename)
                lang_pack = self._load(file_path)
                language_code = lang_pack.get("language_code")
                if language_code:
                    self.language_packs[language_code] = lang_pack
                else:
                    logging.warning(f"Language pack '{filename}' does not have 'language_code' attribute.")
        self.current_language = self._determine_language()

    def load_messages(self, message_file_path):
        self.messages = self._load(message_file_path)

    def _determine_language(self):
        preferred_language = self.get("ui.language")
        if preferred_language and preferred_language in self.language_packs:
            return preferred_language
        if not self.language_packs:
            logging.warning("No language packs found. Using default language 'en'.")
            return "en"
        return list(self.language_packs.keys())[0]

    def handle_file_operation(self, operation, file_path, content=None, destination=None):
        """파일 작업을 공통적으로 처리하는 함수 (확장)"""
        try:
            if operation == "write":
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                return True
            elif operation == "read":
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            elif operation == "delete":
                os.remove(file_path)
                return True
            elif operation == "copy":  # 파일 복사 기능 추가
                shutil.copy2(file_path, destination)  # 메타데이터 보존을 위해 copy2 사용
                return True
            elif operation == "move": # 파일 이동 기능 추가
                shutil.move(file_path, destination)
                return True
            else:
                logging.error(self.get_message("error.507", e=f"Unsupported operation: {operation}"))
                return False
        except FileNotFoundError:
            logging.warning(self.get_message("warning.401", file_path=file_path))
            return False
        except Exception as e:
            logging.error(self.get_message("error.507", e=e))
            return False

    def initialize_database(self, engine):
        """SQLAlchemy를 사용하여 데이터베이스 테이블 생성."""
        try:
            config = self.get("database.init_queries")
            queries = [text(query) for query in config]
            with engine.connect() as conn:
                for query in queries:
                    conn.execute(query)
                logging.info("Database initialized and required tables created.")
        except (SQLAlchemyError, IOError, KeyError) as e:
            logging.error(f"Error initializing database: {e}")
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

# 외부 함수들
def load_tensorflow_model(model_path):
    """TensorFlow 모델 로딩 함수."""
    try:
        model = tf.keras.models.load_model(model_path)
        logging.info(f"TensorFlow 모델 로딩 완료: {model_path}")
        return model
    except Exception as e:
        handle_error(None, "model_load_error", "505", error=e, model_path=model_path)
        return None

def load_gpt_model(gpt_model_path):
    """GPT 모델 로딩 함수."""
    try:
        logging.info("GPT 모델 로딩 중...")
        tokenizer = GPT2Tokenizer.from_pretrained(gpt_model_path)
        gpt_model = GPT2LMHeadModel.from_pretrained(gpt_model_path)
        logging.info(f"GPT 모델 로딩 완료: {gpt_model_path}")
        return tokenizer, gpt_model
    except Exception as e:
        handle_error(None, "gpt_model_load_error", "505", error=e, model_path=gpt_model_path)
        return None, None

def load_json(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "FILE_NOT_FOUND", "message": f"File not found: {file_path}"}
    except json.JSONDecodeError:
        return {"error": "INVALID_JSON_FORMAT", "message": f"Invalid JSON format: {file_path}"}
    except Exception as e:
        return {"error": "FILE_LOAD_ERROR", "message": f"Error loading file: {file_path} - {e}"}

def handle_error(system_manager, category, code, exception, message=None):
    error_message_key = f"{category}_{code}"
    error_message = get_message(error_message_key)

    if message:
        error_message += f" - {message}"

    if exception:
        logging.exception(error_message)
    else:
        logging.error(error_message)

    if system_manager:
        system_manager.handle_error(error_message, error_message_key)

def get_message(message_id, error=None, **kwargs):
    # 메시지 ID에 따른 메시지 로딩 로직 구현
    messages = {
        "501": "KeyError 발생: {error}",
        "505": "일반 오류 발생: {error}",
        "512": "JSON 디코딩 오류: {error}",
        "518": "OCR 엔진 오류: {error}",
        # 추가 메시지 ID와 메시지 매핑
    }
    message = messages.get(message_id, "알 수 없는 오류 발생")
    if error:
        message = message.format(error=error, **kwargs)
    return message

def send_message_to_queue(system_manager, queue_name, message):
    # 큐에 메시지 전송 로직 구현
    pass

def initialize_managers(self):
    for manager_name, manager_config in config.managers.items():
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
            logging.error(f"Error importing module {module_path}: {e}")
        except AttributeError as e:
            logging.error(
                f"Error getting class {class_name} from module {module_path}: {e}")
        except Exception as e:
            logging.error(
                f"An unexpected error occurred during manager initialization: {e}")

def get_manager(self, manager_name):
    return self.managers.get(manager_name)