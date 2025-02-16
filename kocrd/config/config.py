# kocrd/config/config.py
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from kocrd.User import FeedbackEventHandler
from kocrd.config.loader import ConfigLoader, load_json, merge_configs, get_temp_dir
from kocrd.config.message.message_handler import MessageHandler
from kocrd.utils.file_utils import FileManager, show_message_box_safe, load_json_file

def load_config(file_path: str) -> dict:
    """JSON 파일을 로드하여 딕셔너리로 반환."""
    return load_json_file(file_path)

def merge_configs(config1: dict, config2: dict) -> dict:
    merged = config1.copy()
    merged.update(config2)
    return merged

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
        self.config_loader = ConfigLoader(config_file) # ConfigLoader에 config_file 전달
        self.config_loader.load_and_merge([config_file, "config/queues.json", "kocrd/config/message/messages.json"])
        self.temp_dir = self.get("file_paths.temp_files")
        self.backup_dir = os.path.join(self.temp_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.temp_files = []
        self.file_manager = FileManager(self.temp_dir, self.backup_dir) # temp_files 제거
        self.rabbitmq = RabbitMQConfig(self)
        self.file_paths = FilePathConfig(self)
        self.ui = UIConfig(self)
        self.message_handler = MessageHandler(self.config_loader)
        self.initialize_managers() # 매니저 초기화
        self.managers = {} # 매니저 인스턴스 저장
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
        return self.message_handler.get_message(message_id, *args, **kwargs) # MessageHandler의 get_message 호출
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
    def handle_message(self, ch, method, properties, body): # handler_instance 제거
        return self.config_loader.handle_message(ch, method, properties, body)
    def send_message(self, queue_name: str, message: dict): # send_message 이름 변경
        return self.config_loader.send_message_to_queue(queue_name, message)
    def cleanup_all_temp_files(self, retention_time: int = 3600):
        self.file_manager.cleanup_all_temp_files(retention_time)
    def cleanup_specific_files(self, files: Optional[List[str]]):
        self.file_manager.cleanup_specific_files(files)
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

config = Config("config/development.json")