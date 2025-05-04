# tests/test_main_ui.py
import sys
import unittest
from PyQt5.QtWidgets import QApplication
from main_ui import MainWindow

class TestMainWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication(sys.argv)  # QApplication 객체 생성

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()  # 테스트 종료 시 QApplication 종료

    def setUp(self):
        self.main_window = MainWindow()  # MainWindow 인스턴스 생성

    def test_window_initialization(self):
        self.assertIsNotNone(self.main_window)  # MainWindow가 None이 아닌지 확인
        self.assertTrue(self.main_window.isVisible())  # 창이 표시되는지 확인

    def test_splitter_ratio(self):
        self.main_window.set_splitter_ratio(0.3)
        ratio = self.main_window.get_splitter_ratio()
        self.assertEqual(ratio, 0.3)  # Splitter 비율이 올바르게 설정되었는지 확인

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
