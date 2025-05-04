# kocrd/system/config/config_module.py
from calendar import c
import logging
import re
from typing import Dict, Any, Optional, List
import os
import json
import pika
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text
from kocrd.system_manager.system_loder.file_utils import FileManager, show_message_box_safe
from kocrd.system_manager.temp_file_manager import TempFileManager
from kocrd.system_manager.main_ui import MainWindow
from kocrd.system_manager.message_and_queue_manager import (
    MessageHandler,
    LanguageController,
    RabbitMQConfig,
    MessageType,
)

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
        self.message_handler = MessageHandler(self, self.language_controller)
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
                logging.error(f"설정 파일 로드 실패: {file_path} - {e}")
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
            self.message_handler.handle_message(
                MessageType.ERR, "525", {"error": str(e)}, additional_message="데이터베이스 초기화 실패"
            )
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
                self.message_handler.handle_message(
                    MessageType.ERR, "manager_import_error", {"error": str(e)}, additional_message=f"매니저 '{manager_name}' 모듈 임포트 오류: {module_path}"
                )
            except AttributeError as e:
                self.message_handler.handle_message(
                    MessageType.ERR, "manager_attribute_error", {"error": str(e)}, additional_message=f"매니저 '{manager_name}' 클래스 속성 오류: {class_name} in {module_path}"
                )
            except Exception as e:
                self.message_handler.handle_message(
                    MessageType.ERR, "manager_initialization_error", {"error": str(e)}, additional_message=f"매니저 '{manager_name}' 초기화 오류"
                )

    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        """AI 모델 실행 프로세스 트리거"""
        manager = self.manager_instances.get(process_type)
        if manager:
            try:
                manager.handle_process(data)
            except Exception as e:
                self.message_handler.handle_message(
                    MessageType.ERR, "517", {"error": str(e)}, additional_message=f"프로세스 '{process_type}' 실행 실패"
                )
        elif process_type == "database_packaging":
            if hasattr(self, "temp_file"):
                try:
                    self.temp_file.database_packaging()
                except Exception as e:
                    self.message_handler.handle_message(
                        MessageType.ERR, "519", {"error": str(e)}, additional_message="데이터베이스 패키징 실패"
                    )
            else:
                self.message_handler.handle_message(
                    MessageType.ERR, "509", {"error": "temp_file 매니저 인스턴스 없음"}
                )
        elif process_type == "ai_training":
            if hasattr(self, "ai_training"):
                try:
                    self.ai_training.request_ai_training(data)
                except Exception as e:
                    self.message_handler.handle_message(
                        MessageType.ERR, "518", {"error": str(e)}, additional_message="AI 학습 요청 실패"
                    )
            else:
                self.message_handler.handle_message(
                    MessageType.ERR, "524", {"error": "ai_training 매니저 인스턴스 없음"}
                )
        elif process_type == "generate_text":
            if hasattr(self, "ai_prediction"):
                try:
                    return self.ai_prediction.generate_text(data.get("command", ""))
                except Exception as e:
                    self.message_handler.handle_message(
                        MessageType.ERR, "520", {"error": str(e)}, additional_message="텍스트 생성 실패"
                    )
            else:
                self.message_handler.handle_message(
                    MessageType.ERR, "524", {"error": "ai_prediction 매니저 인스턴스 없음"}
                )

    def get_setting(self, setting_path):
        return self.get(setting_path)

    def create_ocr_engine(self, engine_type: str):  # OCR 엔진 생성 로직
        try:
            pass
        except Exception as e:
            self.message_handler.handle_message(
                MessageType.ERR, "516", {"error": str(e)}, additional_message=f"OCR 엔진 생성 실패: {engine_type}"
            )
            return None

    def create_ai_model(self, model_type: str):
        try:
            # AI 모델 생성 로직
            pass
        except Exception as e:
            self.message_handler.handle_message(
                MessageType.ERR, "520", {"error": str(e)}, additional_message=f"AI 모델 생성 실패: {model_type}"
            )
            return None

    def load_gpt_model(self, gpt_model_path):
        try:
            logging.info("GPT 모델 로딩 중...")
            tokenizer = GPT2Tokenizer.from_pretrained(gpt_model_path)
            gpt_model = GPT2LMHeadModel.from_pretrained(gpt_model_path)
            logging.info(f"GPT 모델 로딩 완료: {gpt_model_path}")
            return tokenizer, gpt_model
        except Exception as e:
            self.message_handler.handle_message(
                MessageType.ERR, "511", {"error": str(e)}, additional_message=f"GPT 모델 로드 실패: {gpt_model_path}"
            )
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
                self.message_handler.handle_message(
                    MessageType.ERR, "529", {"error": str(e)}, additional_message=f"파일 작업 '{operation}' 실패: {file_path}"
                )
                return False
        else:
            self.message_handler.handle_message(
                MessageType.ERR, "524", {"error": f"지원하지 않는 파일 작업: {operation}"}
            )
            return False

    def handle_db_exception(self, func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except SQLAlchemyError as e:
                self.message_handler.handle_message(
                    MessageType.ERR, "525", {"error": str(e)}, additional_message="데이터베이스 오류 발생"
                )
                raise
        return wrapper

    def cleanup_all_temp_files(self, retention_time: int = 3600):
        try:
            return self.temp_file_manager.cleanup_all_temp_files(retention_time)
        except OSError as e:
            self.message_handler.handle_message(
                MessageType.ERR, "507", {"error": str(e)}, additional_message="임시 파일 정리 실패"
            )
            return False

    def cleanup_specific_files(self, files: Optional[List[str]]):
        try:
            return self.temp_file_manager.cleanup_specific_files(files)
        except OSError as e:
            self.message_handler.handle_message(
                MessageType.ERR, "507", {"error": str(e)}, additional_message="임시 파일 정리 실패"
            )
            return False

    @handle_db_exception
    def execute_and_log(self, engine, query, params, success_message):
        try:
            with engine.connect() as conn:
                conn.execute(query, params)
            logging.info(success_message)
        except SQLAlchemyError as e:
            self.message_handler.handle_message(
                MessageType.ERR, "513", {"error": str(e)}, additional_message="데이터베이스 쿼리 실패"
            )
            raise

    @handle_db_exception
    def execute_and_fetch(self, engine, query, error_message, params=None):
        try:
            with engine.connect() as conn:
                result = conn.execute(query, params or {})
            return [dict(row) for row in result]
        except SQLAlchemyError as e:
            self.message_handler.handle_message(
                MessageType.ERR, "513", {"error": str(e)}, additional_message="데이터베이스 쿼리 실패"
            )
            raise

config = Config("config/development.json")
