import logging
from typing import Dict, Any, List, Optional
import os
from kocrd.config.loader import ConfigLoader
from kocrd.config.message.message_handler import MessageHandler
from kocrd.utils.file_utils import FileManager, show_message_box_safe

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
    def __init__(self, config_loader: ConfigLoader):
        self.language = config_loader.get("ui.language", "ko")
        self.id_mapping = config_loader.get("ui.id_mapping")
        self.settings = config_loader.get("ui.settings")

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

    def get(self, key_path, default=None):
        return self.config_loader.get(key_path, default)
    def validate(self, key_path: str, validator: callable, message: str):
        self.config_loader.validate(key_path, validator, message)

    def get_message(self, message_id, *args, **kwargs):
        return self.message_handler.get_message(message_id, *args, **kwargs)

    def handle_document_exception(self, parent, category, code, exception, additional_message=None):
        message_id = f"{category}_{code}"
        error_message = self.get_message(message_id)
        if additional_message:
            error_message += f" - {additional_message}"
        log_message = error_message.format(error=exception)
        logging.error(log_message)
        show_message_box_safe(error_message.format(error=exception), "오류")

    def handle_message(self, ch, method, properties, body):
        return self.config_loader.handle_message(ch, method, properties, body)

    def send_message(self, queue_name: str, message: dict):
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

    def initialize_managers(self, system_manager):
        return self.config_loader.initialize_managers(system_manager)

    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        return self.config_loader.trigger_process(process_type, data)

    def handle_error(self, category, code, exception, additional_message=None):
        return self.config_loader.handle_error(category, code, exception, additional_message)

    def send_message_to_queue(self, queue_name: str, message: dict):
        return self.config_loader.send_message_to_queue(queue_name, message)

config = Config("config/development.json")