# file_name: document_manager

import os
import pika
import json
from fpdf import FPDF
import logging
import time
import threading
from PyQt5.QtWidgets import QWidget, QFileDialog, QMessageBox, QApplication
from sqlalchemy.exc import SQLAlchemyError
from pdf2image import convert_from_path
from typing import List, Optional
from PyQt5.QtWidgets import QMessageBox
from kocrd.system.config.config import config, get_message  # config import 추가
from kocrd.managers.document.document_temp import DocumentTempManager  # DocumentTempManager 임포트 추가
from kocrd.system_manager import SystemManager
from kocrd.system.config.loader import ConfigLoader  # ConfigLoader import 추가
from kocrd.system.config.message.message_handler import MessageHandler  # MessageHandler import 추가

config_path = os.path.join(os.path.dirname(__file__), 'Document_config.json')
message_handler = MessageHandler(config_path)  # MessageHandler 인스턴스 생성
config_loader = ConfigLoader(config_path)  # ConfigLoader 인스턴스 생성

MAX_FILE_SIZE = config_loader.get_config()["MAX_FILE_SIZE"]
MESSAGE_QUEUE = config_loader.get_config()["MESSAGE_QUEUE"]
MESSAGE_TYPES = config_loader.get_config()["message_types"]
QUEUES = config_loader.get_config()["queues"]
LOGGING_INFO = config_loader.get_config()["logging"]["info"]
LOGGING_WARNING = config_loader.get_config()["logging"]["warning"]
LOGGING_ERROR = config_loader.get_config()["logging"]["error"]

from ...kocrd.managers.document.document_controller import DocumentController
from .document_table_view import DocumentTableView # 상대 경로 import
from .document_processor import DocumentProcessor # 상대 경로 import
from .document_temp import DocumentTempManager  # DocumentTempManager 임포트 추가

class DocumentManager(QWidget):
    def __init__(self, ocr_manager, database_manager, message_queue_manager, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.message_queue_manager = message_queue_manager
        self.ocr_manager = ocr_manager
        self.temp_file_manager = DocumentTempManager()  # DocumentTempManager 인스턴스 생성
        self.document_processor = DocumentProcessor(database_manager, ocr_manager, parent, self, message_queue_manager)
        self.document_table_view = DocumentTableView(self)
        self.document_controller = DocumentController(self.document_processor, parent, self)
        self.system_manager = SystemManager(config)

        self.config = self.system_manager.get_config() # config 객체 가져오기
        self.config_loader = ConfigLoader()  # ConfigLoader 인스턴스 생성
        self.message_handler = MessageHandler(self.config_loader)  # MessageHandler 인스턴스 생성

        logging.info("DocumentManager initialized.")
    
    def add_document_to_table(self, document_info):
        self.document_table_view.add_document(document_info)
    def handle_document_exception(self, parent, category, code, exception, additional_message=None):
        """문서 관련 예외를 처리하고 메시지를 표시합니다."""

        message_id = f"{category}_{code}"
        error_message = self.message_handler.get_message(message_id)  # 변경
        if additional_message:
            error_message += f" - {additional_message}"

        log_message = error_message.format(error=exception)
        logging.error(log_message)
        QMessageBox.critical(parent, "오류", error_message.format(error=exception))

    def show_message(self, parent, title, message):
        """메시지를 표시합니다."""
        QMessageBox.information(parent, title, message)

    def save_document_info(self, document_info):
        """문서 정보를 데이터베이스에 저장."""
        self.database_manager.save_document_info(document_info)

    def update_document_info(self, document_info):
        """문서 정보를 업데이트."""
        self.database_manager.update_document_info(document_info)

    def delete_document(self, file_name):
        """문서를 데이터베이스에서 삭제."""
        self.database_manager.delete_document(file_name)

    def load_documents(self):
        """저장된 문서 정보를 로드."""
        return self.database_manager.load_documents()

    def send_message(self, message):
        """메시지를 큐에 전송."""
        try:
            queue_name = QUEUES["document_queue"]
            self.message_queue_manager.send_message(queue_name, message)
            logging.info(f"Message sent to queue '{queue_name}': {message}")
        except Exception as e:
            logging.error(self.message_handler.get_message("error.520", error=e))  # 변경

    def get_ui(self):
        return self.document_controller.get_ui()

    def search_documents(self, keyword, column_index=None, match_exact=False):
        self.document_controller.search_documents(keyword, column_index, match_exact)

    def save_ocr_images(self, pdf_file_path):
        self.document_processor.save_ocr_images(pdf_file_path)

    def save_feedback(self, feedback_data):
        self.document_processor.save_feedback(feedback_data)

    def get_valid_doc_types(self):
        return self.document_processor.get_valid_doc_types()

    def determine_document_type(self, text):
        return self.document_processor.determine_document_type(text)

    def export_to_pdf(self, data, filename="output.pdf"):
        self.document_controller.export_to_pdf(data, filename)

    def start_consuming(self):
        """메시지 큐에서 메시지 소비 시작."""
        self.message_queue_manager.start_consuming()

    def clear_table(self):
        self.document_table_view.clear_table()

    def filter_documents(self, criteria):
        self.document_table_view.filter_table(criteria)

    def get_selected_file_names(self):
        return self.document_table_view.get_selected_file_names()

    def load_document(self, file_path):
        document_info = self.document_processor.process_single_document(file_path)
        if document_info:
            self.document_table_view.add_document(document_info)

    def manage_temp_files(self):
        """임시 파일을 관리합니다."""
        self.temp_file_manager.cleanup()

    def read_temp_file(self, file_path):
        """임시 파일의 내용을 읽어 반환합니다."""
        return self.handle_file_operation("read", file_path)

    def is_match_found(self, keyword, cell_text, match_exact):
        """셀 텍스트에서 키워드가 존재하는지 확인"""
        keyword_lower = keyword.lower()
        cell_text_lower = cell_text.lower()

        if match_exact:
            return cell_text_lower == keyword_lower
        return keyword_lower in cell_text_lower

    def get_table_data(self, include_headers=False):
        """DocumentTableView의 데이터를 2D 리스트 형태로 반환 (헤더 포함 여부 선택 가능)"""
        data = []
        headers = self.document_table_view.headers  # DocumentTableView의 headers 속성 사용
        if headers is None:  # 헤더가 없을 경우 처리
            headers = []

        for row in range(self.document_table_view.table_widget.rowCount()):
            row_data = []
            for col in range(self.document_table_view.table_widget.columnCount()):
                item = self.document_table_view.table_widget.item(row, col)
                row_data.append(item.text() if item is not None else "")  # item이 None인 경우 "" 추가
            data.append(row_data)

        if include_headers:
            return headers, data
        else:
            return data

def process_document_task(ch, method, properties, body):
    message = json.loads(body)
    file_paths = message.get("file_paths")
    cleanup = message.get("cleanup")
    print(f"Received document processing task: {file_paths}")
    time.sleep(5)  # 문서 처리 작업 대신 5초 대기
    # 실제 문서 처리 로직 구현 (SystemManager의 handle_documents 로직을 여기에 옮김)
    # ...

def process_database_packaging_task(ch, method, properties, body):
    message = json.loads(body)
    print("Received database packaging task")
    time.sleep(5)  # 데이터베이스 패키징 작업 대신 5초 대기
    # 실제 데이터베이스 패키징 로직 구현 (SystemManager의 database_packaging 로직을 여기에 옮김)
    # ...

