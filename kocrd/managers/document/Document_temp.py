# document_temp.py: 문서 임시 파일 관리를 위한 클래스입니다.
import os
import tempfile
import logging
import shutil
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from kocrd.config.loader import ConfigLoader  # ConfigLoader import 추가

class DocumentTempManager:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.temp_files = []
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True)
        logging.info(f"DocumentTempManager initialized with temp_dir: {self.temp_dir}")

    def create_temp_file(self, content, suffix=".tmp"):
        """임시 파일을 생성하고 내용을 작성합니다."""
        file_path = tempfile.NamedTemporaryFile(delete=False, suffix=suffix).name
        if self.handle_file_operation("write", file_path, content):  # 변경
            self.temp_files.append(file_path)
            logging.info(f"Temporary file created: {file_path}")
            return file_path
        return None

    def read_temp_file(self, file_path):
        """임시 파일의 내용을 읽어 반환합니다."""
        return self.handle_file_operation("read", file_path)  # 변경

    def delete_temp_file(self, file_path):
        """임시 파일을 삭제합니다."""
        if self.handle_file_operation("delete", file_path):  # 변경
            self.temp_files.remove(file_path)
            logging.info(f"Temporary file deleted: {file_path}")

    def cleanup(self):
        """모든 임시 파일을 삭제합니다."""
        for file_path in self.temp_files:
            self.delete_temp_file(file_path)  # 변경
        self.temp_files = []
        logging.info("All temporary files cleaned up.")

    def backup_temp_files(self):
        """임시파일을 백업합니다."""
        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                backup_path = os.path.join(self.backup_dir, filename) # 백업 경로 설정
                if os.path.isfile(file_path):
                    if not self.handle_file_operation("copy", file_path, destination=backup_path): # 변경
                        return False # 백업 실패 시 False 반환
            logging.info("Temporary files backed up.")
            return True
        except Exception as e:
            logging.error(self.config_loader.get_message("error.507", e=e))
            return False

    def restore_temp_files(self):
        """백업된 임시파일을 복원합니다."""
        try:
            for filename in os.listdir(self.backup_dir):
                file_path = os.path.join(self.backup_dir, filename)
                restore_path = os.path.join(self.temp_dir, filename) # 복원 경로 설정
                if os.path.isfile(file_path):
                    if not self.handle_file_operation("copy", file_path, destination=restore_path): # 변경
                        return False # 복원 실패 시 False 반환
            logging.info("Temporary files restored.")
            return True
        except Exception as e:
            logging.error(self.config_loader.get_message("error.507", e=e))
            return False

    def cleanup_all_temp_files(self, retention_time: int = 3600):
        """임시 디렉토리의 모든 파일 정리 (보관 기간 적용)."""
        cutoff_time = datetime.now() - timedelta(seconds=retention_time)

        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    if file_creation_time < cutoff_time:
                        os.remove(file_path)
                        logging.info(f"Expired temporary file removed: {file_path}")
            logging.info(f"Temporary directory cleaned.")
        except FileNotFoundError:
            logging.warning(self.config_loader.get_message("warning.401", temp_dir=self.temp_dir))
        except Exception as e:
            logging.error(self.config_loader.get_message("error.507", e=e))

    def cleanup_specific_files(self, files: Optional[List[str]]):
        """특정 파일들을 정리합니다."""
        if files:
            for file_path in files:
                try:
                    os.remove(file_path)
                    logging.info(f"File removed: {file_path}")
                except FileNotFoundError:
                    logging.warning(self.config_loader.get_message("warning.401", file_path=file_path))
                except Exception as e:
                    logging.error(self.config_loader.get_message("error.507", e=e))
        else:
            self.cleanup_all_temp_files()
    def handle_file_operation(self, operation, file_path, content=None, destination=None):
        """파일 작업을 공통적으로 처리하는 함수 (확장)"""
        try:
            if operation == "write":
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                return True
            elif operation == "read":
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            elif operation == "delete":
                os.remove(file_path)
                return True
            elif operation == "copy":  # 파일 복사 기능 추가
                shutil.copy2(file_path, destination)  # 메타데이터 보존을 위해 copy2 사용
                return True
            elif operation == "move": # 파일 이동 기능 추가
                shutil.move(file_path, destination)
                return True
            else:
                logging.error(self.config_loader.get_message("error.507", e=f"Unsupported operation: {operation}"))
                return False
        except FileNotFoundError:
            logging.warning(self.config_loader.get_message("warning.401", file_path=file_path))
            return False
        except Exception as e:
            logging.error(self.config_loader.get_message("error.507", e=e))
            return False