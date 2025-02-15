# kocrd/config/loader.py
import json
import logging
from kocrd.utils.file_utils import show_message_box_safe
from kocrd.utils.error_utils import handle_error

class ConfigLoader:  # 클래스 이름 변경
    def __init__(self):  # config_files 인자 제거
        self.config_data = {}

    def _load(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"error": f"File not found: {file_path}"}
        except json.JSONDecodeError:
            return {"error": f"Invalid JSON format: {file_path}"}
        except Exception as e:
            return {"error": f"Error loading file: {file_path} - {e}"}

    def _merge_configs(self, config1: dict, config2: dict) -> dict:
        config1.update(config2)
        return config1

    def load_and_merge(self, config_files: list):  # 메서드 이름 변경
        for file_path in config_files:
            config_data = self._load(file_path)
            if "error" in config_data:
                handle_error(logging, "config_error", "512", config_data["error"])  # handle_error 활용
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

        return _get(self.config_data, key_path.split("."))

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