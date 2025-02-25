# kocrd/config/loader.py
import logging
import os
from typing import Callable, Dict, Optional, Any, List
from kocrd.system.system_loder.file_utils import FileManager, show_message_box_safe
from kocrd.system.config.config import Config
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text
import pika
import tensorflow as tf
from transformers import GPT2Tokenizer, GPT2LMHeadModel

class ConfigLoader:
    def __init__(self, config_path: str):
        self.config = Config(config_path)
        self.config_data = {}
        self.language_packs = {}
        self.current_language = "en"
        self.file_manager = FileManager(get_temp_dir(), self.config.get("backup_dir"), [])
        self.load_language_packs("kocrd/config/language")
        self.load_messages("kocrd/config/message/messages.json")

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
        message = self.get_message(key) or "Unknown message"
        return message.format(*args, **kwargs) if message else "Unknown message"

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

    def send_message_to_queue(self, queue_name, message):
        try:
            # 큐에 메시지 전송 로직 구현
            logging.info(f"Message sent to queue '{queue_name}': {message}")
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"RabbitMQ 연결 오류: {e}")
            raise

    def _process_ocr_request(self, message, data):
        file_path = data.get("file_path")
        logging.info(message)
    def load_and_merge(self, config_files: List[str]):
        for file_path in config_files:
            config_data = self.file_manager.read_json(file_path)
            if config_data is None:
                continue
            self.config_data = merge_configs(self.config_data, config_data)

    def get(self, key_path, default=None):
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

    def load_language_packs(self, lang_dir):
        for filename in os.listdir(lang_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(lang_dir, filename)
                lang_pack = self.file_manager.read_json(file_path)
                language_code = lang_pack.get("language_code")
                if language_code:
                    self.language_packs[language_code] = lang_pack
                else:
                    logging.warning(f"Language pack '{filename}' does not have 'language_code' attribute.")
        self.current_language = self._determine_language()
    def load_messages(self, message_file_path):
        self.messages = self.file_manager.read_json(message_file_path)

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
            logging.info(self._message("db_init_success"))
        except (SQLAlchemyError, IOError, KeyError) as e:
            logging.error(self._message("db_init_fail", error=e))
            raise RuntimeError("Database initialization failed.") from e

    def handle_db_exception(self, func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except SQLAlchemyError as e:
                logging.error(f"Database error: {e}")
                raise
        return wrapper

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
    def initialize_managers(self, system_manager):
        managers_config = self.get_managers()
        for manager_name, manager_config in managers_config.items():
            module_path = manager_config["module"]
            class_name = manager_config["class"]
            dependencies = manager_config.get("dependencies", [])
            kwargs = manager_config.get("kwargs", {})

            dependencies_instances = [
                system_manager.managers[dep] for dep in dependencies
            ]

            try:
                module = __import__(module_path, fromlist=[class_name])
                manager_class = getattr(module, class_name)

                system_manager.managers[manager_name] = manager_class(
                    *dependencies_instances, **kwargs
                )
            except ImportError as e:
                logging.error(self._message("error.import_error", module=module_path, error=e))
            except AttributeError as e:
                logging.error(self._message("error.attribute_error", class_name=class_name, module=module_path, error=e))
            except Exception as e:
                logging.error(self._message("error.manager_init_error", error=e))

    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        """AI 모델 실행 프로세스 트리거"""
        manager = self.get_manager(process_type)
        if manager:
            manager.handle_process(data)
        elif process_type == "database_packaging":
            self.get_manager("temp_file").database_packaging()
        elif process_type == "ai_training":
            self.get_manager("ai_training").request_ai_training(data)
        elif process_type == "generate_text":
            ai_manager = self.get_manager("ai_prediction")
            if ai_manager:
                return ai_manager.generate_text(data.get("command", ""))
            else:
                logging.error("AIManager가 초기화되지 않았습니다.")
        else:
            logging.warning(f"🔴 알 수 없는 프로세스 유형: {process_type}")
            QMessageBox.warning(self.main_window, "오류", "알 수 없는 작업 유형입니다.")

    def handle_error(self, category, code, exception, additional_message=None):
        message_id = f"{category}_{code}"
        error_message = self.get_message(message_id)
        if additional_message:
            error_message += f" - {additional_message}"
        log_message = error_message.format(error=exception)
        logging.error(log_message)
        show_message_box_safe(error_message.format(error=exception), "오류")

    def handle_document_exception(self, parent, category, code, exception, additional_message=None):
        message_id = f"{category}_{code}"
        error_message = self.get_message(message_id)
        if additional_message:
            error_message += f" - {additional_message}"
        log_message = error_message.format(error=exception)
        logging.error(log_message)
        show_message_box_safe(error_message.format(error=exception), "오류")
        return log_message
