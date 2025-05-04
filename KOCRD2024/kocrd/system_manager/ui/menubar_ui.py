# kocrd/system/ui/menubar_ui.py
from PyQt5.QtWidgets import QMenuBar, QAction, QMenu, qApp
from kocrd.system_manager.config.config_module import Config
from kocrd.system_manager.ui.preferenceswindow_ui import Preferenceswindow

class Menubar:
    """메뉴바 이벤트 및 UI 관리 클래스."""
    def __init__(self, parent, config_path="config/ui.json"):
        self.parent = parent  # parent 위젯 저장
        self.menu_bar = QMenuBar(parent)  # parent 위젯에 메뉴바 생성
        self.config_path = config_path
        self.config = Config(self.config_path)
        self.preferenceswindow = Preferenceswindow(self.parent)
        self.setup_menus()
        self.parent.setMenuBar(self.menu_bar)
        self.addAction = QMenu.addAction

    def setup_menus(self):
        """메뉴바 설정."""
        self.menu_bar.addMenu(self.file_menu())
        self.menu_bar.addMenu(self.edit_menu())
        self.menu_bar.addMenu(self.settings_menu())
        self.menu_bar.addMenu(self.help_menu())

    def file_menu(self):
        """파일 메뉴."""
        file_menu = QMenu(self.config.link_text_processor("UI", "001"), self.parent)  # 메뉴 이름 설정
        self._create_action(file_menu, "UI", "005")  # 저장
        self._create_action(file_menu, "UI", "007")  # 열기
        file_menu.addSeparator()
        exit_action = self._create_action(file_menu, "UI", "004")  # 종료
        if exit_action:
            exit_action.triggered.connect(qApp.quit)
        return file_menu
    def edit_menu(self):
        """편집 메뉴."""
        edit_menu = QMenu(self.config.link_text_processor("UI", "002"), self.parent)
        self._create_action(edit_menu, "UI", "002")  # 편집
        return edit_menu
    def settings_menu(self):
        """설정 메뉴."""
        settings_menu = QMenu(self.config.link_text_processor("UI", "003"), self.parent)
        settings_action = self._create_action(settings_menu, "UI", "009")  # "환경 설정" 액션 생성 및 메뉴에 추가
        if settings_action:  # 액션이 성공적으로 생성되었는지 확인
            settings_action.triggered.connect(self.show_settings_dialog)
        self._create_action(settings_menu, "UI", "003")  # 설정
        return settings_menu
    def show_settings_dialog(self):
        self.preferenceswindow.exec_() # 환경 설정 다이얼로그 표시

    def help_menu(self):
        """도움말 메뉴."""
        help_menu = QMenu(self.config.link_text_processor("UI", "008"), self.parent) # 도움말 메뉴
        self._create_action(help_menu, "UI", "008")  # 도움말
        return help_menu

    def _create_action(self, menu, message_type, message_id):
        """QAction 생성 및 메뉴에 추가."""
        message = self.config.link_text_processor(message_type, message_id)
        if message:
            action = QAction(message, self.parent)  # parent 위젯을 부모로 설정
            menu.addAction(action)
            return action  # 생성된 action 반환
        return None
