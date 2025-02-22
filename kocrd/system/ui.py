# kocrd/system/ui.py
from calendar import c

from kocrd.system.ui.document_ui import DocumentUISystem
from kocrd.system.ui.monitoring_ui_system import MonitoringUISystem
from kocrd.system.ui.menubar_ui import MenubarManager
from kocrd.system.ui.messagebox_ui import MessageBoxUI
from kocrd.system.ui.preferenceswindow_ui import Preferenceswindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.document_ui_system = DocumentUISystem(self)  # DocumentUISystem 인스턴스 생성
        self.monitoring_ui_system = MonitoringUISystem(self)  # MonitoringUISystem 인스턴스 생성
        self.menubar_manager = MenubarManager(self)
        self.messagebox_ui = MessageBoxUI(self.messages, self.error_messages)
        self.preferences_window = Preferenceswindow(self)

        self.init_ui()

    def init_ui(self):
        self.document_ui_system.init_ui()
        self.monitoring_ui_system.init_ui()

    def mwnubar_load(self):
        self.menubar_manager.setup_menus()  # 메뉴바 설정

    def closeEvent(self, event):
        self.messagebox_ui.closeEvent(event)
        event.accept()

    def show_preferences_window(self):
        self.preferences_window.show()