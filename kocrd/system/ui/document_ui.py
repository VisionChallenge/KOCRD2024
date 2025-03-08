# kocrd/system/ui/document_ui.py
import logging
import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QAction, QTextEdit, QProgressBar, QTableWidget, QHeaderView, QMessageBox, QInputDialog,  QListWidget, QTableWidgetItem, QMenu
from cv2 import add
from kocrd.system.document_manager import DocumentManager
from kocrd.system.database_manager import DatabaseManager
from kocrd.system.main_ui import MainWindow, MessageBox
from kocrd.system.config.config_module import Config, LanguageController
from PyQt5.QtCore import Qt,pyqtSignal
from PyQt5.QtGui import QCursor

class DocumentUI(QWidget):
    def __init__(self, main_window: MainWindow, database_manager: DatabaseManager):
        super().__init__()
        self.main_window = main_window
        self.table_widget = None
        self.progress_bar = QProgressBar(main_window)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.message_box = MessageBox(self.config)
        self.document_manager = DocumentManager(main_window, database_manager)
        self.config = Config("config/ui.json")
        self.language_controller = LanguageController()
        self.factionsList = QListWidget()
        self.import_documents = self.document_manager.import_documents
        self.clear_table = self.document_manager.clear_table
        self.init_ui()

    def init_ui(self):
        self.table_widget = self.create_table_widget()
        self.layout.addWidget(self.table_widget)
        self.setLayout(self.layout)
        self.table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)  # table_widget에 컨텍스트 메뉴 설정
        self.table_widget.customContextMenuRequested.connect(self.handle_click_event) # table_widget에 시그널 연결

    def create_table_widget(self):
        """문서 테이블 생성."""
        table_widget = QTableWidget()
        columns = self.config.get("Default_column", [])
        table_widget.setColumnCount(len(columns))
        table_widget.setHorizontalHeaderLabels([self.config.language_controller.get_message(f"column.{col['order']:03d}", "UI") for col in columns])
        
        header = table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(True)
        return table_widget


    def handle_click_event(self, pos):
        menu = QMenu(self.table_widget) # table_widget를 메뉴에 전달
        if self.table_widget.rowCount() == 0:  # 테이블이 비어 있는지 확인
            self.D_UI_Menu_L(menu)
        else:
            self.D_UI_Menu_T(menu)
        menu.exec_(self.table_widget.mapToGlobal(pos)) # table_widget에 상대적 좌표를 절대적 좌표로 변환

    def D_UI_Menu_L(self, menu: QMenu):
        """빈 레이아웃일 때의 메뉴 항목을 추가합니다."""
        menu.addAction(self.language_controller.get_message("017", "UI")).triggered.connect(self.action1_triggered) # 열추가
        menu.addAction(self.language_controller.get_message("018", "UI")).triggered.connect(self.action2_triggered) # 정렬
        menu.addAction(self.language_controller.get_message("013", "UI")).triggered.connect(self.clear_table) # 초기화
        menu.addAction(self.language_controller.get_message("015", "UI")).triggered.connect(self.import_documents) # 파일가져오기

    def action1_triggered(self):
        self.add_column()
    def action2_triggered(self):
        self.sort_table()

    def D_UI_Menu_T(self, menu: QMenu):
        """table_widget일 때의 메뉴 항목을 추가합니다."""
        menu.addAction(self.language_controller.get_message("018", "UI")).triggered.connect(self.action2_triggered) # 정렬
        menu.addAction(self.language_controller.get_message("019", "UI")).triggered.connect(self.action3_triggered) # 열선택
