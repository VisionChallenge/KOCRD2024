# file_name: system_manager.py
import logging
import json
import sys
import os
import pika
import pytesseract
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QMessageBox, QApplication
from PIL import Image, UnidentifiedImageError  # PIL import 위치 변경

from kocrd.system.ocr_manager import OCRManager
from kocrd.managers.temp_file_manager import TempFileManager
from kocrd.system.database_manager import DatabaseManager
from kocrd.window.menubar_manager import MenubarManager
from kocrd.system.document_manager import DocumentManager
from kocrd.system.ai_model_manager import AIModelManager
from kocrd.config.loader import ConfigLoader
from kocrd.managers.manager_factory import ManagerFactory
from kocrd.config.message.message_handler import MessageHandler
from kocrd.managers.rabbitmq_manager import RabbitMQManager
from kocrd.system.settings_manager import SettingsManager # SettingsManager import 유지
from kocrd.utils.embedding_utils import EmbeddingUtils # EmbeddingUtils import 유지
from kocrd.config.config import Config  # Config import 추가

class Systemassistance:
    def __init__(self, config_files: list, main_window=None):
        self.config_loader = ConfigLoader()
        self.config_loader.load_and_merge(config_files)
        self.main_window = main_window
        self.manager_factory = ManagerFactory(self.config_loader)
        self.managers = {}
        self.message_handler = MessageHandler(self.config_loader)
        self.rabbitmq_manager = RabbitMQManager(self.config_loader)
        self.ai_model_manager = AIModelManager.get_instance()
        self.training_event_handler = (self, self.ai_model_manager)
        self.config = Config(config_files)  # ConfigLoader 대신 Config 사용
        self.config.initialize_managers(self)  # Config에서 매니저 초기화

    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        """AI 모델 실행 프로세스 트리거"""
        return self.config.trigger_process(process_type, data)  # Config로 위임

    def handle_message(self, ch, method, properties, body):
        """RabbitMQ 메시지를 처리합니다."""
        self.config.handle_message(ch, method, properties, body)  # Config로 위임

    def handle_error(self, message, error_message_key=None):
        self.config.handle_error("system", "error", message, error_message_key)  # Config로 위임

    def run_embedding_generation(self):
        EmbeddingUtils.run_embedding_generation(self.config_loader)

    def close_rabbitmq_connection(self):
        self.rabbitmq_manager.close()

    def get_manager(self, manager_name: str) -> Optional[Any]:
        return self.managers.get(manager_name)

    def get_ui(self, ui_name: str) -> Optional[Any]:
        return self.uis.get(ui_name)

    def get_ai_model_manager(self):
        """AIModelManager 인스턴스 반환."""
        return self.managers.get("ai_model")

    def get_config(self):
        return self.config

# main_window 모듈을 나중에 임포트
from kocrd.system.main_window import MainWindow