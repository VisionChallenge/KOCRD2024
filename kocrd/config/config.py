# kocrd/config/config.py
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from kocrd.User import FeedbackEventHandler
from kocrd.config.loader import ConfigLoader
from kocrd.config.message.message_handler import MessageHandler
from kocrd.utils.file_utils import FileManager, show_message_box_safe # file_utils 함수 import

def load_config(file_path: str) -> dict:
    """JSON 파일을 로드하여 딕셔너리로 반환."""
    with open(file_path, 'r') as f:
        return json.load(f)

def get_temp_dir() -> str:
    """임시 디렉토리 경로를 반환."""
    temp_dir = os.path.join(os.environ.get("TEMP", os.path.expanduser("~/.tmp")), "ocr_manager")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

class RabbitMQConfig:
    def __init__(self, config):
        self.host = config.get("rabbitmq.host")  # config.get() 사용
        self.port = config.get("rabbitmq.port")  # config.get() 사용
        self.user = config.get("rabbitmq.user")  # config.get() 사용
        self.password = config.get("rabbitmq.password")  # config.get() 사용
        self.virtual_host = config.get("rabbitmq.virtual_host")  # config.get() 사용
class FilePathConfig:
    def __init__(self, config):
        self.models = config.get("file_paths.models")  # config.get() 사용
        self.document_embedding = config.get("file_paths.document_embedding")  # config.get() 사용
        self.document_types = config.get("file_paths.document_types")  # config.get() 사용
        self.temp_files = config.get("file_paths.temp_files")  # config.get() 사용
class UIConfig:
    def __init__(self, config):
        self.language = config.get("ui.language", "ko")  # config.get() 사용, 기본값 설정
        self.id_mapping = config.get("ui.id_mapping")  # config.get() 사용
        self.settings = config.get("ui.settings")  # config.get() 사용
class Config:
    def __init__(self, config_file):
        self.config_data = {}
        self.config_loader = ConfigLoader()
        self.config_loader.load_and_merge([config_file, "config/queues.json", "kocrd/config/message/messages.json"])  # load_and_merge 호출
        self.temp_dir = self.get("file_paths.temp_files")
        self.backup_dir = os.path.join(self.temp_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True) # ensure_directory_exists 제거 후 os.makedirs 사용
        self.temp_files = []
        self.file_manager = FileManager(self.temp_dir, self.backup_dir, self.temp_files)
        self.rabbitmq = RabbitMQConfig(self)  # self 전달
        self.file_paths = FilePathConfig(self)  # self 전달
        self.ui = UIConfig(self)  # self 전달
        self.message_handler = MessageHandler(self.config_loader)
    def get(self, key_path, default=None):
        return self.config_loader.get(key_path, default)
    def validate(self, key_path: str, validator: callable, message: str):
        self.config_loader.validate(key_path, validator, message)
    def get_rabbitmq_settings(self):
        return self.get("rabbitmq") # get 메서드 사용
    def get_file_paths(self):
        return self.get("file_paths") # get 메서드 사용
    def get_constants(self):
        return self.get("constants")
    def get_ui_settings(self):
        return self.get("ui.settings")
    def get_ui_id_mapping(self):
        return self.get("ui.id_mapping")
    def get_managers(self):
        return self.get("managers")
    def get_message(self, message_id, *args, **kwargs):
        return self.message_handler.get_message(message_id, *args, **kwargs)
    def get_queue_name(self, queue_type):
        return self.config_loader.get_queue_name(queue_type)
    def get_database_url(self):
        return self.get("database_url")
    def get_file_settings(self):
        return self.get("file_settings")
    def handle_document_exception(self, parent, category, code, exception, additional_message=None):
        message_id = f"{category}_{code}"
        error_message = self.get_message(message_id)
        if additional_message:
            error_message += f" - {additional_message}"

        log_message = error_message.format(error=exception)
        logging.error(log_message)
        show_message_box_safe(error_message.format(error=exception), "오류")
    def cleanup_all_temp_files(self, retention_time: int = 3600):
        self.file_manager.cleanup_all_temp_files(retention_time) # file_manager 사용
    def cleanup_specific_files(self, files: Optional[List[str]]):
        self.file_manager.cleanup_specific_files(files) # file_manager 사용
    def get_setting(self, setting_path):
        return self.config_loader.get_setting(setting_path)
    def create_ocr_engine(self, engine_type: str):
        return self.config_loader.create_ocr_engine(engine_type)
    def create_ai_model(self, model_type: str):
        return self.config_loader.create_ai_model(model_type)
    def send_message_to_queue(self, queue_name: str, message: dict):
        return self.config_loader.send_message_to_queue(queue_name, message)
    def handle_message(self, handler_instance, ch, method, properties, body):
        return self.config_loader.handle_message(handler_instance, ch, method, properties, body)

# config 인스턴스 생성 (기존 코드 유지)
config = Config("config/development.json")

class SystemManager:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.managers = {}

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

import logging

def handle_error(system_manager, event_name, message_id, error=None, **kwargs):
    message = get_message(message_id, error=error, **kwargs)
    if message:
        logging.error(message)
    else:
        logging.error(f"Message with ID '{message_id}' not found.")
    # 필요에 따라 system_manager를 사용하여 이벤트 트리거
    # system_manager.trigger_event(event_name, {"error_message": str(message)})

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
