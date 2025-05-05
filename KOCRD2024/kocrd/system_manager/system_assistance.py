# kocrd/system/system_assistance.py
import logging
import json
import sys
import os
import pika
import pytesseract
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QMessageBox, QApplication, QMenu  # QMenu 추가
from PIL import Image, UnidentifiedImageError  # PIL import 위치 변경
from PyQt5.QtGui import QCursor

import logging
from typing import Dict, Any, Optional
from kocrd.system_manager.config.config_module import Config
from kocrd.managers.rabbitmq_manager import RabbitMQManager
from kocrd.system_manager.ai_model_manager import AIModelManager
from kocrd.utils.embedding_utils import EmbeddingUtils
from kocrd.system_manager.manager_factory import ManagerFactory  # ManagerFactory import 추가


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
    def message_queue_manager():
    def get_manager(self, manager_name: str) -> Optional[Any]:
        return self.managers.get(manager_name)

    def get_config(self):
        return self.config

# main_window 모듈을 나중에 임포트
from kocrd.system_manager.main_window import MainWindow