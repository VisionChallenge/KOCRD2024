# kocrd/system/system_assistance.py
import logging
import json
import sys
import os
import pika
import pytesseract
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QMessageBox, QApplication
from PIL import Image, UnidentifiedImageError  # PIL import 위치 변경

import logging
from typing import Dict, Any, Optional
from kocrd.system.config.config_module import Config
from kocrd.config.message.message_handler import MessageHandler
from kocrd.managers.rabbitmq_manager import RabbitMQManager
from kocrd.system.ai_model_manager import AIModelManager
from kocrd.utils.embedding_utils import EmbeddingUtils
from kocrd.system.manager_factory import ManagerFactory  # ManagerFactory import 추가


class SystemAssistance:
    def __init__(self, config_files: list, main_window=None):
        self.config_loader.load_and_merge(config_files)
        self.main_window = main_window
        self.manager_factory = ManagerFactory(self.config_loader)
        self.managers = {}
        self.message_handler = MessageHandler(self.config_loader)
        self.rabbitmq_manager = RabbitMQManager(self.config_loader)
        self.ai_model_manager = AIModelManager.get_instance()
        self.config = Config(config_files)
        self.initialize_managers()

    def initialize_managers(self):
        # ManagerFactory를 사용하여 매니저 초기화
        self.managers = self.manager_factory.create_managers()
        for name, manager in self.managers.items():
            setattr(self, name, manager)

    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        """AI 모델 실행 프로세스 트리거"""
        return self.config.trigger_process(process_type, data)

    def handle_message(self, ch, method, properties, body):
        """RabbitMQ 메시지를 처리합니다."""
        self.config.handle_message(ch, method, properties, body)

    def handle_error(self, message, error_message_key=None):
        self.config.handle_error("system", "error", message, error_message_key)

    def run_embedding_generation(self):
        EmbeddingUtils.run_embedding_generation(self.config_loader)

    def close_rabbitmq_connection(self):
        self.rabbitmq_manager.close()

    def get_manager(self, manager_name: str) -> Optional[Any]:
        return self.managers.get(manager_name)

    def get_config(self):
        return self.config

# main_window 모듈을 나중에 임포트
from kocrd.system.main_window import MainWindow