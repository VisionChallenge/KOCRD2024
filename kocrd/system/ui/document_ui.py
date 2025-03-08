# kocrd/system/ui/document_ui.py
import logging
import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QTextEdit, QProgressBar, QTableWidget, QHeaderView, QMessageBox, QInputDialog, QTableWidgetItem, QMenu
from kocrd.system.document_manager import DocumentManager
from kocrd.system.database_manager import DatabaseManager
from kocrd.system.main_ui import MainWindow, MessageBox
from kocrd.system.config.config_module import Config, LanguageController
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor

class DocumentUI(QWidget):
    def __init__(self, main_window: MainWindow, config: Config, database_manager: DatabaseManager, document_manager: DocumentManager, message_box: MessageBox, LanguageController: LanguageController):
        super().__init__()
        self.main_window = main_window
        self.table_widget = None
        self.progress_bar = QProgressBar(main_window)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.message_box = MessageBox(self.config)
        self.document_manager = DocumentManager(main_window, database_manager, message_box)
        self.config = Config
        self.language_controller = LanguageController
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.create_table_widget())
        self.setLayout(layout)
        self.layout().setContextMenuPolicy(Qt.CustomContextMenu)
        self.layout().customContextMenuRequested.connect(self.handle_layout_right_click)

    def create_table_widget(self):
        """문서 테이블 생성."""
        self.table_widget = QTableWidget()
        columns = self.config.get("Default_column", [])
        self.table_widget.setColumnCount(len(columns))
        self.table_widget.setHorizontalHeaderLabels([self.config.language_controller.get_message(f"column.{col['order']:03d}", "UI") for col in columns])

        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setStretchLastSection(True)

        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.table_widget.clicked.connect(self.handle_left_click)

        return self.table_widget

    def handle_click_event(self, pos):
        menu = QMenu(self)
        if self.layout(True):
            self.D_UI_Menu_L(menu)
            menu.exec_(self.mapToGlobal(pos))
        else:
            self.D_UI_Menu_T(menu)
            menu.exec_(QCursor.pos())


    def D_UI_Menu_L(self, menu):
        """빈 레이아웃일 때의 메뉴 항목을 추가합니다."""
        menu.addAction(self.language_controller.get_message("017", "UI"))
        menu.addAction(self.language_controller.get_message("018", "UI"))
        menu.addAction(self.language_controller.get_message("013", "UI"))
        menu.addAction(self.language_controller.get_message("015", "UI"))

    def D_UI_Menu_T(self, menu):
        """table_widget일 때의 메뉴 항목을 추가합니다."""
        menu.addAction(self.language_controller.get_message("018", "UI"))
        menu.addAction(self.language_controller.get_message("019", "UI"))

    def clear_table(self):
        self.document_manager.clear_table()

    def update_document_info(self):
        """선택된 문서의 정보를 업데이트합니다."""
        selected_items = self.document_manager.get_selected_items()
        if not selected_items:
            self.message_box.show_warning_message(self.message_handler.get_message("MSG", "208"))
            return

        selected_row = selected_items[0].row()
        current_file_name = self.document_manager.get_item_text(selected_row, 0)
        new_type, ok = QInputDialog.getText(self, "문서 유형 수정", f"{current_file_name}의 새로운 문서 유형을 입력하세요:")
        if ok and new_type:
            self.document_manager.update_document_type(current_file_name, new_type, selected_row)

