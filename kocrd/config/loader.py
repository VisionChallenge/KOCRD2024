# kocrd/config/loader.py
import json
import logging
import os
from typing import Callable, Dict, Optional, Any
from kocrd.utils.file_utils import show_message_box_safe
import importlib  # 모듈 동적 로딩을 위한 import

class ConfigLoader:
    def __init__(self):
        self.config_data = {}

    def _load(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"error": "FILE_NOT_FOUND", "message": f"File not found: {file_path}"}
        except json.JSONDecodeError:
            return {"error": "INVALID_JSON_FORMAT", "message": f"Invalid JSON format: {file_path}"}
        except Exception as e:
            return {"error": "FILE_LOAD_ERROR", "message": f"Error loading file: {file_path} - {e}"}

    def _merge_configs(self, config1: dict, config2: dict) -> dict:
        merged = config1.copy()
        merged.update(config2)
        return merged

    def create_ocr_engine(self, engine_type: str):
        try:
            module_name = f"kocrd.ocr_engines.{engine_type}_ocr" # 모듈 이름 규칙 정의
            module = importlib.import_module(module_name) # 모듈 동적 로딩
            class_name = engine_type.capitalize() + "OCR"  # 클래스 이름 규칙 정의
            ocr_engine_class = getattr(module, class_name)
            return ocr_engine_class() # 인스턴스 생성
        except ImportError:
            logging.error(f"OCR 엔진 모듈을 찾을 수 없습니다: {engine_type}")
            return None
        except AttributeError:
            logging.error(f"OCR 엔진 클래스를 찾을 수 없습니다: {engine_type}")
            return None
        except Exception as e:
            logging.error(f"OCR 엔진 생성 중 오류: {e}")
            return None


    def create_ai_model(self, model_type: str):
        try:
            module_name = f"kocrd.ai_models.{model_type}_model"  # 모듈 이름 규칙 정의
            module = importlib.import_module(module_name)  # 모듈 동적 로딩
            class_name = model_type.capitalize() + "Model"  # 클래스 이름 규칙 정의
            ai_model_class = getattr(module, class_name)
            return ai_model_class()  # 인스턴스 생성
        except ImportError:
            logging.error(f"AI 모델 모듈을 찾을 수 없습니다: {model_type}")
            return None
        except AttributeError:
            logging.error(f"AI 모델 클래스를 찾을 수 없습니다: {model_type}")
            return None
        except Exception as e:
            logging.error(f"AI 모델 생성 중 오류: {e}")
            return None

    def send_message_to_queue(self, queue_name: str, message: dict):
        try:
            queue_config = self.get("queues." + queue_name)
            if not queue_config:
                raise ValueError(f"Queue configuration not found for '{queue_name}'")
            import pika
            connection = pika.BlockingConnection(pika.ConnectionParameters(**queue_config))
            channel = connection.channel()
            channel.queue_declare(queue=queue_name)
            channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(message))
            connection.close()
        except Exception as e:
            logging.error(f"Error sending message to queue '{queue_name}': {e}")
            show_message_box_safe(f"메시지 전송 오류: {e}", "오류")

    def handle_message(self, handler_instance, ch, method, properties, body):
        try:
            message = json.loads(body)
            # 메시지 처리 로직 (기존 코드 유지)
        except json.JSONDecodeError as e:
            logging.error(f"JSON 디코딩 오류: {e}. 메시지 내용: {body}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logging.error(f"메시지 처리 오류: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

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

    def get_message(self, message_id: str, *args, **kwargs) -> Optional[str]:
        messages = self.get("messages")
        if messages:
            message = messages.get(message_id)
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

    def load_and_merge(self, config_files: list):
        for file_path in config_files:
            config_data = self._load(file_path)
            if "error" in config_data:
                self.handle_error(logging, "config_error", "512", config_data["message"])  # 수정: config_data["message"]
                continue
            self.config_data = self._merge_configs(self.config_data, config_data)