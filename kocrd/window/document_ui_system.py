# file_name: document_ui_system.py
import logging
import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QTextEdit, QProgressBar, QTableWidget, QHeaderView, QMessageBox, QInputDialog, QTableWidgetItem
from PyQt5.QtCore import Qt
import sys
import os

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from kocrd.window.monitoring_ui_system import MonitoringUISystem
from kocrd.config.config import text_manager, AppConfig # text_manager와 AppConfig import
class DocumentUISystem:
    def __init__(self, main_window, system_manager, ocr_manager):
        self.main_window = main_window
        self.system_manager = system_manager # system_manager 추가
        self.ocr_manager = ocr_manager     # ocr_manager 추가
        self.table_widget = None
        # progress_bar를 main_window를 부모로 하여 초기화합니다.
        self.progress_bar = QProgressBar(main_window)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # text_manager와 AppConfig를 직접 참조합니다.
        self.text_manager = text_manager
        self.app_config = AppConfig

    def _execute_action(self, action, confirmation_key=None, success_key=None, error_key=None, **kwargs):
        if confirmation_key:
            reply = QMessageBox.question(
                self.main_window,
                self.text_manager.get_text("general", "CONFIRMATION_TITLE", default="확인"), # '확인' 메시지 키가 있다면 사용
                self.text_manager.get_text("general", confirmation_key).format(**kwargs),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        try:
            result = action() if callable(action) else None
            if success_key:
                QMessageBox.information(
                    self.main_window,
                    self.text_manager.get_text("general", "COMPLETION_TITLE", default="완료"), # '완료' 메시지 키가 있다면 사용
                    self.text_manager.get_text("general", success_key).format(**kwargs)
                )
            return result
        except Exception as e:
            logging.error(f"Error: {e}")
            if error_key:
                QMessageBox.warning(
                    self.main_window,
                    self.text_manager.get_text("general", "ERROR_TITLE", default="오류"), # '오류' 메시지 키가 있다면 사용
                    self.text_manager.get_text("general", error_key).format(**kwargs)
                )

    def get_widget(self):
        """문서 테이블과 관련 UI 요소(progress_bar 포함)를 포함하는 컨테이너 위젯을 생성하고 반환합니다."""
        container_widget = QWidget()
        layout = QVBoxLayout(container_widget)

        # 문서 테이블 생성 및 설정
        self.table_widget = QTableWidget()
        # UI 설정에서 테이블 컬럼 정보 로드 (AppConfig 사용)
        table_columns_config = self.app_config.UI_SETTINGS["components"]["table_columns"]
        self.table_widget.setColumnCount(len(table_columns_config))
        self.table_widget.setHorizontalHeaderLabels([col["name"] for col in table_columns_config])

        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setStretchLastSection(True)

        layout.addWidget(self.table_widget)

        # ProgressBar를 테이블 아래에 추가
        layout.addWidget(self.progress_bar)

        container_widget.setLayout(layout)
        return container_widget

    def create_table_widget(self):
        """문서 테이블 생성."""
        self.table_widget = QTableWidget()

        # UI 설정에서 테이블 컬럼 정보 로드 (AppConfig 사용)
        table_columns_config = self.app_config.UI_SETTINGS["components"]["table_columns"]
        self.table_widget.setColumnCount(len(table_columns_config))
        self.table_widget.setHorizontalHeaderLabels([col["name"] for col in table_columns_config])

        # 헤더 조정
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setStretchLastSection(True)

        return self.table_widget

    def clear_table(self):
        """파일 테이블을 초기화합니다."""
        # 메시지 키 수정 (202: 확인, 203: 완료)
        self._execute_action(self._clear_table_action, confirmation_key="202", success_key="203")

    def _clear_table_action(self):
        self.table_widget.setRowCount(0)  # 모든 행 삭제
        logging.info(self.text_manager.get_text("general", "203")) # general 카테고리 명시

    def filter_documents(self, criteria):
        """문서 필터링."""
        # _execute_with_logging 호출 시 카테고리 명시
        # self.main_window.document_ui_system 인스턴스에 직접 접근하여 filter_table 호출
        self._execute_with_logging(
            lambda: self.filter_table(criteria), # DocumentUISystem 자신의 filter_table 메서드 호출
            success_key="311", success_category="log",
            error_key="201", error_category="general"
        )

    def filter_table(self, criteria):
        """주어진 기준으로 테이블 데이터를 필터링합니다.
        criteria는 딕셔너리 형태일 수 있습니다. 예: {"column_name": "value"}
        이 예시에서는 간단히 '파일 이름'으로만 필터링하도록 구현합니다.
        실제 구현은 필터링 기준에 따라 복잡해질 수 있습니다."""

        if not self.table_widget:
            logging.warning("Table widget is not initialized.")
            return

        # 모든 행을 기본적으로 보이게 설정
        for row in range(self.table_widget.rowCount()):
            self.table_widget.showRow(row)

        # 필터링 기준이 없으면 바로 반환 (모두 보임)
        if not criteria:
            return

        # 'criteria' 딕셔너리에서 필터링할 컬럼과 값을 가져옵니다.
        # 예시: criteria = {"파일 이름": "example.pdf"}
        # 실제로는 여러 기준이 복합적으로 적용될 수 있습니다.
        for column_name, filter_value in criteria.items():
            if not filter_value: # 값이 비어있으면 해당 기준은 무시
                continue

            filter_value_lower = str(filter_value).lower()
            column_index = -1

            # 컬럼 이름으로 인덱스 찾기
            table_columns_config = self.app_config.UI_SETTINGS["components"]["table_columns"]
            for idx, col_data in enumerate(table_columns_config):
                if col_data["name"] == column_name:
                    column_index = idx
                    break

            if column_index == -1:
                logging.warning(f"Column '{column_name}' not found for filtering.")
                continue

            for row in range(self.table_widget.rowCount()):
                item = self.table_widget.item(row, column_index)
                if item:
                    cell_text = item.text().lower()
                    if filter_value_lower not in cell_text:
                        self.table_widget.hideRow(row) # 조건에 맞지 않으면 숨김

        logging.info(f"Documents filtered with criteria: {criteria}")

    def update_document_info(self, database_manager):
        """선택된 문서의 정보를 업데이트합니다."""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            self._show_message_box("208") # "208": "Please select a document to edit."
            return

        selected_row = selected_items[0].row()
        current_file_name = self.table_widget.item(selected_row, 0).text()
        new_type, ok = QInputDialog.getText(self.main_window, self.text_manager.get_text("general", "UPDATE_DOC_TYPE_TITLE", default="문서 유형 수정"), f"{current_file_name}의 새로운 문서 유형을 입력하세요:")
        if ok and new_type:
            # 메시지 키 수정 (207: 성공, 204: 오류)
            self._execute_action(
                lambda: self._update_document_type(database_manager, current_file_name, new_type, selected_row),
                success_key="207", # "207": "문서 유형이 성공적으로 업데이트되었습니다."
                error_key="204"  # "204": "An error occurred while updating the document type:"
            )

    def _update_document_type(self, database_manager, current_file_name, new_type, selected_row):
        database_manager.update_document_type(current_file_name, new_type)
        self.table_widget.setItem(selected_row, 1, QTableWidgetItem(new_type))
        logging.info(f"Updated document type for {current_file_name} to {new_type}") # 특정 메시지 키가 없으므로 f-string 유지

    def search_documents(self, keyword, column_index=None, match_exact=False):
        """문서 검색 기능을 구현합니다."""
        if not keyword.strip():
            for row in range(self.table_widget.rowCount()):
                self.table_widget.showRow(row)
            logging.info(self.text_manager.get_text("general", "209")) # general 카테고리 명시
            return

        for row in range(self.table_widget.rowCount()):
            match_found = False
            for col in range(self.table_widget.columnCount()):
                if column_index is not None and col != column_index:
                    continue

                item = self.table_widget.item(row, col)
                if item:
                    cell_text = item.text().lower()
                    keyword_lower = keyword.lower()
                    if (match_exact and cell_text == keyword_lower) or (not match_exact and keyword_lower in cell_text):
                        match_found = True
                        break

            if match_found:
                self.table_widget.showRow(row)
            else:
                self.table_widget.hideRow(row)

        logging.info(f"Document search completed for keyword: {keyword}") # 특정 메시지 키가 없으므로 f-string 유지

    def delete_document(self, file_name, database_manager):
        """문서를 삭제합니다."""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            self._show_message_box("208") # "208": "Please select a document to edit." (generic select message)
            return

        selected_row = selected_items[0].row()
        file_name = self.table_widget.item(selected_row, 0).text()
        # 메시지 키 (205: 확인, 206: 성공)
        self._execute_action(
            lambda: self._delete_document_action(database_manager, file_name, selected_row),
            confirmation_key="205", # "205": "Do you want to delete the document '{file_name}'?"
            success_key="206", # "206": "The document '{file_name}' has been deleted."
            file_name=file_name
        )
    def _delete_document_action(self, database_manager, file_name, selected_row):
        self.table_widget.removeRow(selected_row)
        database_manager.delete_document(file_name)
        logging.info(self.text_manager.get_text("general", "206").format(file_name=file_name)) # general 카테고리 명시

    def _show_message_box(self, confirmation_key, success_key=None, action=None, **kwargs):
        reply = QMessageBox.question(
            self.main_window,
            self.text_manager.get_text("general", "CONFIRMATION_TITLE", default="확인"),
            self.text_manager.get_text("general", confirmation_key).format(**kwargs),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes and action:
            action()
            if success_key:
                QMessageBox.information(
                    self.main_window,
                    self.text_manager.get_text("general", "COMPLETION_TITLE", default="완료"),
                    self.text_manager.get_text("general", success_key).format(**kwargs)
                )

    def _execute_with_logging(self, action, success_key, success_category, error_key, error_category):
        try:
            action()
            logging.info(self.text_manager.get_text(success_category, success_key)) # 카테고리 명시
        except Exception as e:
            logging.error(f"Error: {e}")
            QMessageBox.warning(
                self.main_window,
                self.text_manager.get_text("general", "ERROR_TITLE", default="오류"),
                self.text_manager.get_text(error_category, error_key) # 카테고리 명시
            )