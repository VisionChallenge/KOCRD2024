# file_name: document_ui_system.py
import logging
import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QTextEdit, QProgressBar, QTableWidget, QHeaderView, QMessageBox, QInputDialog, QTableWidgetItem
from PyQt5.QtCore import Qt
import sys
import os
from main_window import MainWindow
  # main_window.py에서 MainWindow 클래스를 가져옵니다.
# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from kocrd.window.monitoring_ui_system import MonitoringUISystem
from kocrd.config.config import AppConfig, text_manager
class DocumentUISystem:
    def __init__(self, main_window):
        self.main_window = main_window
        self.table_widget = None
        # progress_bar를 main_window를 부모로 하여 초기화합니다.
        self.progress_bar = QProgressBar(main_window)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # 메시지 및 UI 설정을 main_window에서 가져옵니다.
        # main_window는 messages.json 및 ui.json을 로드하여 각각 self.messages, self.ui_config 속성으로 제공해야 합니다.
        self.messages = self.main_window.messages
        self.ui_config = self.main_window.ui_config

    def _execute_action(self, action, confirmation_key=None, success_key=None, error_key=None, **kwargs):
        if confirmation_key:
            reply = QMessageBox.question(
                self.main_window, "확인",
                self.main_window.get_message(confirmation_key).format(**kwargs), # main_window의 get_message 사용
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        try:
            result = action() if callable(action) else None
            if success_key:
                QMessageBox.information(self.main_window, "완료", self.main_window.get_message(success_key).format(**kwargs)) # main_window의 get_message 사용
            return result
        except Exception as e:
            logging.error(f"Error: {e}")
            if error_key:
                QMessageBox.warning(self.main_window, "오류", self.main_window.get_message(error_key)) # main_window의 get_message 사용

    def get_widget(self):
        """문서 테이블과 관련 UI 요소(progress_bar 포함)를 포함하는 컨테이너 위젯을 생성하고 반환합니다."""
        container_widget = QWidget()
        layout = QVBoxLayout(container_widget)

        # 문서 테이블 생성 및 설정
        self.table_widget = QTableWidget()
        # UI 설정에서 테이블 컬럼 정보 로드
        self.table_widget.setColumnCount(len(self.ui_config["components"]["table_columns"]))
        self.table_widget.setHorizontalHeaderLabels([col["name"] for col in self.ui_config["components"]["table_columns"]])

        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setStretchLastSection(True)

        layout.addWidget(self.table_widget)

        # ProgressBar를 테이블 아래에 추가
        # 이미 __init__에서 초기화되었으므로 여기서는 레이아웃에 추가만 합니다.
        layout.addWidget(self.progress_bar)

        container_widget.setLayout(layout)
        return container_widget

    def create_table_widget(self):
        """문서 테이블 생성."""
        self.table_widget = QTableWidget()

        # UI 설정에서 테이블 컬럼 정보 로드
        self.table_widget.setColumnCount(len(self.ui_config["components"]["table_columns"]))
        self.table_widget.setHorizontalHeaderLabels([col["name"] for col in self.ui_config["components"]["table_columns"]])

        # 헤더 조정
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)  # 컬럼 자동 크기 조정
        header.setStretchLastSection(True)

        return self.table_widget

    def clear_table(self):
        """파일 테이블을 초기화합니다."""
        self._execute_action(self._clear_table_action, "202", "203") # "201"은 오류 메시지이므로 "202"로 수정했습니다.
    def _clear_table_action(self):
        self.table_widget.setRowCount(0)  # 모든 행 삭제
        logging.info(self.main_window.get_message("203")) # main_window의 get_message 사용

    def filter_documents(self, criteria):
        """UIManager를 통해 문서 필터링."""
        self._execute_with_logging(
            lambda: self.main_window.system_manager.ui_control_manager.document_ui.filter_table(criteria),
            "311",
            "201"
        )

    def update_document_info(self, database_manager):
        """선택된 문서의 정보를 업데이트합니다."""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            self._show_message_box("208") # main_window의 get_message 사용 (내부 호출)
            return

        selected_row = selected_items[0].row()
        current_file_name = self.table_widget.item(selected_row, 0).text()
        new_type, ok = QInputDialog.getText(self.main_window, "문서 유형 수정", f"{current_file_name}의 새로운 문서 유형을 입력하세요:")
        if ok and new_type:
            self._execute_action(
                lambda: self._update_document_type(database_manager, current_file_name, new_type, selected_row),
                success_key="207", # 메시지 파일에 따르면 '문서 유형이 성공적으로 업데이트되었습니다.'는 "207"에 가깝습니다.
                error_key="204" # 메시지 파일에 따르면 'An error occurred while updating the document type:'는 "204"입니다.
            )

    def _update_document_type(self, database_manager, current_file_name, new_type, selected_row):
        database_manager.update_document_type(current_file_name, new_type)
        self.table_widget.setItem(selected_row, 1, QTableWidgetItem(new_type))
        logging.info(f"Updated document type for {current_file_name} to {new_type}")

    def search_documents(self, keyword, column_index=None, match_exact=False):
        """문서 검색 기능을 구현합니다."""
        if not keyword.strip():
            for row in range(self.table_widget.rowCount()):
                self.table_widget.showRow(row)
            logging.info(self.main_window.get_message("209")) # main_window의 get_message 사용
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

        logging.info(f"Document search completed for keyword: {keyword}")

    def delete_document(self, file_name, database_manager):
        """문서를 삭제합니다."""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            self._show_message_box("208") # main_window의 get_message 사용 (내부 호출)
            return

        selected_row = selected_items[0].row()
        file_name = self.table_widget.item(selected_row, 0).text()
        self._execute_action(
            lambda: self._delete_document_action(database_manager, file_name, selected_row),
            confirmation_key="208", # 메시지 파일에 따르면 '문서 '{file_name}'을(를) 삭제하시겠습니까?'는 "208"에 가깝습니다.
            success_key="209", # 메시지 파일에 따르면 '문서 '{file_name}'이(가) 삭제되었습니다.'는 "209"입니다.
            file_name=file_name
        )
    def _delete_document_action(self, database_manager, file_name, selected_row):
        self.table_widget.removeRow(selected_row)
        database_manager.delete_document(file_name)
        logging.info(self.main_window.get_message("209").format(file_name=file_name)) # main_window의 get_message 사용

    def _show_message_box(self, confirmation_key, success_key=None, action=None, **kwargs):
        reply = QMessageBox.question(
            self.main_window, "확인",
            self.main_window.get_message(confirmation_key).format(**kwargs), # main_window의 get_message 사용
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes and action:
            action()
            if success_key:
                QMessageBox.information(self.main_window, "완료", self.main_window.get_message(success_key).format(**kwargs)) # main_window의 get_message 사용

    def _execute_with_logging(self, action, success_key, error_key):
        try:
            action()
            logging.info(self.main_window.get_message(success_key)) # main_window의 get_message 사용
        except Exception as e:
            logging.error(f"Error: {e}")
            QMessageBox.warning(self.main_window, "오류", self.main_window.get_message(error_key)) # main_window의 get_message 사용
