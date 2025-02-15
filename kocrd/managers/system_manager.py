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

from kocrd.managers.ocr.ocr_manager import OCRManager
from kocrd.managers.temp_file_manager import TempFileManager
from kocrd.managers.database_manager import DatabaseManager
from kocrd.window.menubar_manager import MenubarManager
from kocrd.managers.document.document_manager import DocumentManager
from kocrd.managers.ai_managers.ai_model_manager import AIModelManager
from kocrd.config.loader import ConfigLoader
from kocrd.managers.manager_factory import ManagerFactory
from kocrd.config.message.message_handler import MessageHandler
from kocrd.managers.rabbitmq_manager import RabbitMQManager
from kocrd.Settings.settings_manager import SettingsManager # SettingsManager import 유지
from kocrd.utils.embedding_utils import EmbeddingUtils # EmbeddingUtils import 유지
from kocrd.handlers.training_event_handler import TrainingEventHandler

class SystemManager:
    def __init__(self, config_files: list, main_window=None):
        self.config_loader = ConfigLoader()
        self.config_loader.load_and_merge(config_files)
        self.main_window = main_window
        self.manager_factory = ManagerFactory(self.config_loader)
        self.managers = {}
        self.message_handler = MessageHandler(self.config_loader)
        self.rabbitmq_manager = RabbitMQManager(self.config_loader)
        self.ai_model_manager = AIModelManager.get_instance()
        self.training_event_handler = TrainingEventHandler(self, self.ai_model_manager)
        self._initialize_managers()
        self.config = self.config_loader

    def _initialize_managers(self):
        managers_config = self.config_loader.get_managers()
        for manager_name, manager_config in managers_config.items():
            self.managers[manager_name] = self.manager_factory.create_manager(manager_name, manager_config)

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

    def handle_message(self, ch, method, properties, body):
        """RabbitMQ 메시지를 처리합니다."""
        self.message_handler.handle_message(ch, method, properties, body, self)

    def handle_error(self, message, error_message_key=None):
        if error_message_key:
            logging.error(f"{message} (Error Key: {error_message_key})")
        else:
            logging.error(message)
        QMessageBox.critical(self.main_window, "Error", message)

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
from kocrd.window.main_window import MainWindow