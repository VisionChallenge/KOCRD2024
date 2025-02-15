# kocrd/managers/document/document_controller.py

import logging
import os
import json
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QWidget, QVBoxLayout
import pandas as pd
from fpdf import FPDF
from kocrd.managers.document.document_table_view import DocumentTableView
from kocrd.managers.document.document_manager import DocumentManager
from kocrd.config.loader import ConfigLoader  # ConfigLoader import 추가

config_path = os.path.join(os.path.dirname(__file__), '..', 'managers_config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

DEFAULT_REPORT_FILENAME = config["DEFAULT_REPORT_FILENAME"]
DEFAULT_EXCEL_FILENAME = config["DEFAULT_EXCEL_FILENAME"]
VALID_FILE_EXTENSIONS = config["VALID_FILE_EXTENSIONS"]
MAX_FILE_SIZE = config["MAX_FILE_SIZE"]
MESSAGE_QUEUE = config["MESSAGE_QUEUE"]
MESSAGE_TYPES = config["message_types"]
QUEUES = config["queues"]
LOGGING_INFO = config["messages"]["log"]
LOGGING_WARNING = config["messages"]["warning"]
LOGGING_ERROR = config["messages"]["error"]

class DocumentController(QWidget):
    def __init__(self, document_processor, parent, system_manager): # system_manager 추가
        self.document_processor = document_processor
        self.parent = parent
        self.system_manager = system_manager
        self.message_queue_manager = system_manager.message_queue_manager # message_queue_manager 추가
        self.document_table_view = DocumentTableView(self)
        self.document_manager = DocumentManager(self.system_manager, self.parent, self.message_queue_manager)
        self.config_loader = ConfigLoader()  # ConfigLoader 인스턴스 생성
        self.init_ui()
        logging.info("DocumentController initialized.")
    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(self.document_table_view)
        self.setLayout(layout)
    def get_ui(self):
        return self.document_table_view
    def open_file_dialog(self):
        file_dialog = QFileDialog(self.parent, "문서 가져오기")
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_paths, _ = file_dialog.getOpenFileNames(
            self.parent, "문서 가져오기", "", f"모든 파일 (*.*);;텍스트 파일 (*.txt);;PDF 파일 (*.pdf);;이미지 파일 (*.png *.jpg);;엑셀 파일 (*.xlsx);;워드 파일 (*.docx)"
        )
        return file_paths
    def import_documents(self):
        file_paths = self.open_file_dialog()
        if not file_paths:
            return

        document_infos = self.document_processor.process_multiple_documents(file_paths)
        if document_infos:
            for document_info in document_infos:
                self.document_table_view.add_document(document_info)
    def generate_report(self, output_path=None):
        """보고서를 생성합니다."""
        default_report_filename = self.config_loader.get("DEFAULT_REPORT_FILENAME")  # 변경
        headers, data = self.document_manager.get_table_data(include_headers=True)  # 변경
        extracted_texts = []
        extracted_texts.append("\t".join(headers))
        for row in data:  # 변경
            extracted_texts.append("\t".join(row))

        if not output_path:
            output_path, _ = QFileDialog.getSaveFileName(
                self.parent, "보고서 저장", default_report_filename, "Text Files (*.txt);;All Files (*)"
            )
            if not output_path:
                QMessageBox.warning(self.parent, "저장 취소", "보고서 저장이 취소되었습니다.")
                return

        if not extracted_texts:
            QMessageBox.warning(self.parent, "보고서 생성 오류", "보고서에 포함할 데이터가 없습니다.")
            return

        try:
            with open(output_path, 'w', encoding='utf-8') as report_file:
                report_file.write("\n".join(extracted_texts))
            logging.info(f"Report saved to {output_path}")
            QMessageBox.information(self.parent, "저장 완료", f"보고서가 저장되었습니다: {output_path}")
        except Exception as e:
            self.document_manager.handle_document_exception(self.parent, "document", "520", e, "보고서 저장 중 오류 발생")
    def export_to_pdf(self, filename="output.pdf"):
        """PDF 파일로 저장합니다."""
        data = self.document_manager.get_table_data()  # 변경

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for row in data:
            for item in row:
                pdf.cell(40, 10, txt=str(item), border=1)
            pdf.ln()
        pdf.output(filename)
        logging.info(f"PDF saved to {filename}.")
    def save_to_excel(self, file_path=None):
        """Excel 파일로 저장합니다."""
        default_excel_filename = self.config_loader.get("DEFAULT_EXCEL_FILENAME")  # 변경
        headers, data = self.document_manager.get_table_data(include_headers=True)  # 변경
        df = pd.DataFrame(data, columns=headers)  # 변경

        try:
            if not file_path:
                file_path, _ = QFileDialog.getSaveFileName(
                    self.parent, "Excel 파일 저장", default_excel_filename, "Excel Files (*.xlsx);;All Files (*)"
                )
                if not file_path:
                    QMessageBox.warning(self.parent, "저장 취소", "Excel 파일 저장이 취소되었습니다.")
                    return
            if not os.path.splitext(file_path)[-1].lower() == '.xlsx':
                file_path += '.xlsx'

            df.to_excel(file_path, index=False, engine='openpyxl')
            logging.info(f"Data saved to Excel: {file_path}")
            QMessageBox.information(self.parent, "저장 완료", f"Excel 파일로 문서 정보가 저장되었습니다: {file_path}")
        except (PermissionError, IOError, Exception) as e:
            self.document_manager.handle_document_exception(self.parent, "document", "520", e, "Excel 파일 저장 중 오류 발생")            
    def clear_table(self):
        self.document_table_view.clear_table()
    def filter_documents(self, criteria):
        self.document_table_view.filter_table(criteria)
    def get_selected_file_name(self):
        return self.document_table_view.get_selected_file_name()
    def load_document(self, file_path):
        document_info = self.document_processor.process_single_document(file_path)
        if document_info:
            self.document_table_view.add_document(document_info)
    def search_documents(self, keyword, column_index=None, match_exact=False):
        """문서를 검색합니다."""
        if not keyword.strip():
            for row in range(self.document_table_view.table_widget.rowCount()):
                self.document_table_view.table_widget.showRow(row)
            logging.info("Search keyword is empty. Showing all rows.")
            return

        found_any = False

        try:
            for row in range(self.document_table_view.table_widget.rowCount()):
                match_found = False
                for col in range(self.document_table_view.table_widget.columnCount()):
                    if column_index is not None and col != column_index:
                        continue

                    item = self.document_table_view.table_widget.item(row, col)
                    if item and self.is_match_found(keyword, item.text(), match_exact):
                        match_found = True
                        found_any = True
                        break

                if match_found:
                    self.document_table_view.table_widget.showRow(row)
                else:
                    self.document_table_view.table_widget.hideRow(row)

            if not found_any:
                QMessageBox.information(self, "검색 결과", "검색 결과가 없습니다.")

            logging.info(f"Document search completed for keyword: {keyword}")
        except Exception as e:
            self.document_manager.handle_document_exception(self.parent, "document", "520", e, "문서 검색 중 오류 발생")  # 변경
    def start_consuming(self):
        """메시지 큐에서 메시지를 소비."""
        try:
            self.message_queue_manager.start_consuming()
        except Exception as e:
            logging.error(self.config_loader.get_message("error.520", error=e))  # 변경
    def send_message(self, message):
        """메시지를 큐에 전송."""
        try:
            queue_name = QUEUES["document_queue"]
            self.document_processor.send_message(queue_name, message)
            logging.info(f"Message sent to queue '{queue_name}': {message}")
        except Exception as e:
            logging.error(self.config_loader.get_message("error.520", error=e))  # 변경