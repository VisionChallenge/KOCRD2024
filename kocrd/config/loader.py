# kocrd/config/loader.py
import json
import logging
import os
from typing import Callable, Dict, Optional, Any
from kocrd.utils.file_utils import show_message_box_safe
import importlib  # 모듈 동적 로딩을 위한 import

class ConfigLoader:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = self.load_config()
        self.config_data = {}
        self.language_packs = {}
        self.current_language = "en"
        self.load_language_packs("kocrd/config/language")
        self.load_messages("kocrd/config/message/messages.json")

    def load_config(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_config(self):
        return self.config

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
                lang_pack = self._load_json(file_path)
                language_code = lang_pack.get("language_code")
                if language_code:
                    self.language_packs[language_code] = lang_pack
                else:
                    logging.warning(f"Language pack '{filename}' does not have 'language_code' attribute.")
        self.current_language = self._determine_language()

    def load_messages(self, message_file_path):
        self.messages = self._load_json(message_file_path)

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