# kocrd/system/ui/monitoring_ui.py
import json
import logging
from PyQt5.QtWidgets import QProgressBar, QTextEdit, QLineEdit, QListWidget, QVBoxLayout, QWidget, QPushButton
from kocrd.system.config.config import Config

class MonitoringUI(QWidget):
    def __init__(self, parent=None, config_path="config/ui.json"):
        super().__init__(parent)
        self.config = Config(config_path)  # Config 클래스 사용
        self.init_ui()
    def init_ui(self):
        central_widget = QWidget(self.main_window)
        self.main_window.setCentralWidget(central_widget)
        central_widget.setLayout(QVBoxLayout())

        splitter = QSplitter(central_widget)
        central_widget.layout().addWidget(splitter)

        monitoring_ui_widget = self
        if isinstance(monitoring_ui_widget, QWidget):
            if monitoring_ui_widget.layout() is None:
                monitoring_layout = QVBoxLayout()
                monitoring_ui_widget.setLayout(monitoring_layout)
            else:
                monitoring_layout = monitoring_ui_widget.layout()
            monitoring_layout.addWidget(self.progress_bar)
            
            log_display = QTextEdit()
            log_display.setReadOnly(True)
            monitoring_layout.addWidget(log_display)

            for widget_config in self.config["monitoring_ui"]["widgets"]:
                widget = getattr(self.main_window, widget_config["name"])
                monitoring_layout.addWidget(widget)

        else:
            logging.error("Monitoring UI is not a QWidget. Cannot add progress bar.")

        splitter.setSizes([1000, 200])
        logging.info(self.config.coll_text("LOG", "328"))

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.progress_bar)
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)
        self.setLayout(layout)

        # Progress Bar
        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

        # Log Display
        self.log_display = QTextEdit(self)
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)

        # Chat Output
        self.chat_output = QTextEdit(self)
        self.chat_output.setReadOnly(True)
        layout.addWidget(self.chat_output)

        # Chat Input
        self.chat_input = QLineEdit(self)
        layout.addWidget(self.chat_input)

        # File List Widget
        self.file_list_widget = QListWidget(self)
        layout.addWidget(self.file_list_widget)

        # 초기화 버튼 추가
        self.clear_button = QPushButton(self.config.coll_text("UI", "013"), self)
        self.clear_button.clicked.connect(self.clear_table)
        layout.addWidget(self.clear_button)

        self.setLayout(layout)
        self.load_ui_config()

    def load_ui_config(self):
        """UI 설정을 로드하고 적용합니다."""
        try:
            components = self.config.get("components", {}).get("monitoring", {}).get("widgets", [])  # Config 클래스 사용
            for component in components:
                if component.get("name") == "progress_bar":
                    self.progress_bar.setValue(0)
                elif component.get("name") == "log_display":
                    self.log_display.setPlainText("")
                elif component.get("name") == "chat_output":
                    self.chat_output.setPlainText("")
                elif component.get("name") == "chat_input":
                    self.chat_input.setText("")
                elif component.get("name") == "file_list_widget":
                    self.file_list_widget.clear()
            logging.info(self.config.coll_text("LOG", "328"))  # coll_text 사용
        except KeyError as e:
            logging.error(f"Error loading UI configuration: {e}")

    def update_progress(self, value):
        """진행률을 업데이트합니다."""
        self.progress_bar.setValue(value)

    def append_log(self, message):
        """로그 메시지를 추가합니다."""
        self.log_display.append(message)

    def append_chat_output(self, message):
        """채팅 출력을 추가합니다."""
        self.chat_output.append(message)

    def generate_ai_response(self, message):
        """AI 응답 생성."""
        try:
            input_ids = self.tokenizer.encode(message, return_tensors="pt")
            pad_token_id = self.tokenizer.pad_token_id or self.tokenizer.eos_token_id
            attention_mask = (input_ids != pad_token_id).long()
            output = self.gpt_model.generate(
                input_ids=input_ids, attention_mask=attention_mask,
                max_new_tokens=50, pad_token_id=pad_token_id
            )
            return self.tokenizer.decode(output[0], skip_special_tokens=True)
        except Exception as e:
            self.config.send_text("ERR", "520")  # "AI 응답 처리 중 오류가 발생했습니다."
            return self.generate_ai_response(message)

    def update_file_list(self, documents):
        """가져온 파일 목록을 업데이트."""
        self.file_list_widget.clear()
        for doc in documents:
            self.file_list_widget.addItem(f"{doc['name']} ({doc['date']})")

    def clear_table(self):
        """파일 테이블을 초기화합니다."""
        self.parent().document_ui.clear_table()


def setup_monitoring_ui():
    # ...existing code...
    print(get_message(self.messages_config, "351"))  # Documents filtered successfully.
    # ...existing code...
    print(get_message(self.messages_config, "352"))  # Document search completed for keyword: {keyword}
    # ...existing code...
