# kocrd\system\document_manager.py

from calendar import c
import os
import re
import pika
import json
import logging
import time
from PyQt5.QtWidgets import QWidget, QFileDialog, QMessageBox, QApplication
from regex import R
from sqlalchemy.exc import SQLAlchemyError
from pdf2image import convert_from_path
from typing import List, Optional
from kocrd.system.config.config_module import Config
from kocrd.system.system_loder.document_table_view import DocumentTableView
from kocrd.system.system_loder.document_controller import DocumentController
from kocrd.system.system_loder.document_processor import DocumentProcessor
from kocrd.system.system_loder.document_temp import DocumentTempManager
from kocrd.system.ocr_manager import OCRManager
from kocrd.system.database_manager import DatabaseManager

class DocumentManager(QWidget):
    def __init__(self, database_manager, message_queue_manager, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.message_queue_manager = message_queue_manager
        self.ocr_manager = OCRManager()
        self.temp_file_manager = DocumentTempManager()  # DocumentTempManager 인스턴스 생성
        self.document_processor = DocumentProcessor(database_manager, parent, self, message_queue_manager)
        self.document_table_view = DocumentTableView(self)
        self.document_controller = DocumentController(self.document_processor, parent, self)
        self.database_manager = DatabaseManager()
        self.config = Config() # config 객체 가져오기

    def handle_document_exception(self, parent, category, code, exception, additional_message=None): #문서 관련 예외를 처리하고 메시지를 표시합니다
        message_id = f"{category}_{code}"
        error_message = self.config.link_text_processor(message_id)
        if additional_message:
            error_message += f" - {additional_message}"

        log_message = error_message.format(error=exception)
        logging.error(log_message)
        QMessageBox.critical(parent, "오류", error_message.format(error=exception))

    def show_message(self, parent, title, message):
        QMessageBox.information(parent, title, message)

    def update_document_type(self, current_file_name, new_type, selected_row): #문서 유형을 업데이트
        try:
            self.database_manager.update_document_type(current_file_name, new_type)
            self.document_table_view.update_item_text(selected_row, 1, new_type)
            logging.info(f"Updated document type for {current_file_name} to {new_type}")
        except Exception as e:
            logging.error(f"Error updating document type: {e}")
            self.message_box.show_error_message(self.message_handler.get_message("ERR", "205"))

    def send_message(self, message): #메시지를 큐에 전송
        try:
            queue_name = QUEUES["document_queue"]
            self.message_queue_manager.send_message(queue_name, message)
            logging.info(f"Message sent to queue '{queue_name}': {message}")
        except Exception as e:
            self.config.link_text_processor("520","ERR", exception=e)
            raise

    def is_match_found(self, keyword, cell_text, match_exact):
        return self.document_table_view.is_match_found(keyword, cell_text, match_exact)
    def get_table_data(self, include_headers=False):
        return self.document_table_view.get_table_data(include_headers)
    def start_consuming(self): #메시지 큐에서 메시지 소비 시작.
        self.message_queue_manager.start_consuming()
    def save_document_info(self, document_info): #문서 정보를 데이터베이스에 저장
        return self.database_manager.save_document_info(document_info)
    def add_document_to_table(self, document_info):
        return self.document_table_view.add_document(document_info)
    def delete_document(self, file_name): #문서를 데이터베이스에서 삭제
        return self.database_manager.delete_document(file_name)
    def sort_table(self): #테이블을 정렬
        return DocumentTableView.sort_table(self)
    def load_documents(self): #저장된 문서 정보를 로드
        return self.database_manager.load_documents()
    def update_document_info(self, document_info): #문서 정보를 업데이트
        return self.database_manager.update_document_info(document_info)
    def save_ocr_images(self, pdf_file_path): #PDF 파일에서 OCR 이미지를 추출하고 저장합니다
        return self.ocr_manager.save_ocr_images(pdf_file_path)
    def get_ui(self):
        return self.document_controller.get_ui()
    def get_valid_doc_types(self):
        return self.document_processor.get_valid_doc_types()
    def determine_document_type(self, text):
        return self.document_processor.determine_document_type(text)
    def import_documents(self): #문서 가져오기
        return DocumentController.import_documents(self)
    def get_selected_file_names(self):
        return self.document_table_view.get_selected_file_names()
    def read_temp_file(self, file_path): #임시 파일의 내용을 읽어 반환합니다
        return self.temp_file_manager.handle_file_operation("read", file_path)
    def manage_temp_files(self): #임시 파일을 관리합니다
        return self.temp_file_manager.cleanup()
    def clear_table(self):
        return self.document_table_view.clear_table()
    def filter_documents(self, criteria):
        return self.document_table_view.filter_table(criteria)
    def export_to_pdf(self, data, filename="output.pdf"):
        return self.document_controller.export_to_pdf(data, filename)
    def search_documents(self, keyword, column_index=None, match_exact=False):
        return self.document_controller.search_documents(keyword, column_index, match_exact)
    def save_feedback(self, feedback_data):
        return self.database_manager.save_feedback(feedback_data)
    def load_document(self, file_path):
        self.document_controller.load_document(file_path)

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

