# kocrd/utils/file_utils.py
import shutil
from typing import List
import logging
import chardet
from typing import Dict, Optional, Any
from datetime import datetime
import os
import tempfile
from kocrd.config.config import config
import json

class FileManager:
    def __init__(self, temp_dir, backup_dir, temp_files):
        self.temp_dir = temp_dir
        self.backup_dir = backup_dir
        self.temp_files = temp_files

    def create_temp_file(self, content, suffix=".tmp"):
        try:
            with tempfile.NamedTemporaryFile(mode="w+", suffix=suffix, dir=self.temp_dir, delete=False) as temp_file:
                temp_file.write(content)
                file_path = temp_file.name
                logging.info(f"Temporary file created: {file_path}")
                self.temp_files.append(file_path)
                return file_path
        except Exception as e:
            logging.error(f"임시 파일 생성 오류: {e}")
            return None
    def copy_file(self, source_path: str, destination_path: str, metadata: bool = False) -> str:
        try:
            if metadata:
                shutil.copy2(source_path, destination_path)
            else:
                shutil.copy(source_path, destination_path)
            logging.info(f"파일 복사 완료: {destination_path}")
            return destination_path
        except FileNotFoundError:
            logging.error(f"파일을 찾을 수 없습니다: {source_path}")
            raise
        except OSError as e:
            logging.error(f"파일 복사 오류: {e}")
            raise
    def delete_file(self, file_path):
        try:
            os.remove(file_path)
            logging.info(f"파일 삭제: {file_path}")
            return True
        except FileNotFoundError:
            logging.warning(f"파일을 찾을 수 없습니다: {file_path}")
            return False
        except Exception as e:
            logging.error(f"파일 삭제 오류: {e}")
            return False
    def read_file(self, file_path: str, file_type: str = "auto") -> Optional[Any]:
        if file_type == "auto":
            file_type = self._determine_file_type(file_path)
        if file_type == "json":
            return self.read_json(file_path)
        elif file_type == "text":
            return self.read_text(file_path)
        else:
            logging.warning(f"Unsupported file type or extension: {file_path}")
            return None

    def write_file(self, file_path: str, content: Any, file_type: str = "auto") -> bool:
        if file_type == "auto":
            file_type = self._determine_file_type(file_path)  # 파일 타입 추론
        if file_type == "json":
            return self.write_json(file_path, content)
        elif file_type == "text":
            return self.write_text(file_path, content)
        else:
            logging.warning(f"Unsupported file type or extension: {file_path}")
            return False
    def _determine_file_type(self, file_path: str) -> str:
        if file_path.endswith((".json", ".yaml", ".yml")):
            return "json"
        elif file_path.endswith(".txt"):
            return "text"
        return "unknown"  # or raise an exception

    def move_file(self, source_path: str, destination_path: str) -> str:
        try:
            shutil.move(source_path, destination_path)
            logging.info(f"파일 이동 완료: {destination_path}")
            return destination_path
        except FileNotFoundError:
            logging.error(f"파일을 찾을 수 없습니다: {source_path}")
            raise
        except OSError as e:
            logging.error(f"파일 이동 오류: {e}")
            raise

    def read_json(self, file_path: str) -> Optional[dict]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading JSON {file_path}: {e}")
            return None

    def read_text(self, file_path: str) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError as e:
            logging.error(f"Error loading text {file_path}: {e}")
            return None
    def write_text(self, file_path: str, content: str) -> bool:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except OSError as e:
            logging.error(f"Error writing text {file_path}: {e}")
            return False
    def write_json(self, file_path: str, data: dict) -> bool:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)  # ensure_ascii=False 추가
            return True
        except OSError as e:
            logging.error(f"Error writing JSON {file_path}: {e}")
            return False

    def cleanup_all_temp_files(self, retention_time: int = 3600):
        """임시 디렉토리의 모든 파일 정리 (보관 기간 적용)."""
        now = datetime.now().timestamp()
        for filename in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, filename)
            if self.file_exists(file_path):
                try:
                    file_stat = os.stat(file_path)
                    file_time = file_stat.st_mtime
                    if now - file_time > retention_time:
                        self.delete_file(file_path)
                        logging.info(f"임시 파일 삭제: {file_path}")
                except Exception as e:
                    logging.error(f"임시 파일 삭제 중 오류: {e}")
    def cleanup_specific_files(self, files: Optional[List[str]]):
        """특정 파일들을 정리합니다."""
        if files:
            for file_path in files:
                if self.file_exists(file_path):
                    try:
                        self.delete_file(file_path)
                        logging.info(f"특정 파일 삭제: {file_path}")
                    except Exception as e:
                        logging.error(f"특정 파일 삭제 중 오류: {e}")
    def backup_temp_files(self):
        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                backup_path = os.path.join(self.backup_dir, filename)
                if os.path.isfile(file_path):
                    try:
                        self.copy_file(file_path, backup_path)
                    except Exception as e:
                        logging.error(f"백업 중 오류: {e}")
                        return False
            logging.info("Temporary files backed up.")
            return True
        except Exception as e:
            logging.error(config.get_message("507", e=e))
            return False
    def restore_temp_files(self):
        try:
            for filename in os.listdir(self.backup_dir):
                file_path = os.path.join(self.backup_dir, filename)
                restore_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    try:
                        self.copy_file(file_path, restore_path)
                    except Exception as e:
                        logging.error(f"복원 중 오류: {e}")
                        return False
            logging.info("Temporary files restored.")
            return True
        except Exception as e:
            logging.error(config.get_message("507", e=e))
            return False
    def detect_encoding(self, file_path: str) -> str:
        """파일의 인코딩을 감지합니다.

        Raises:
            FileNotFoundError: 파일을 찾을 수 없는 경우 발생합니다.
            OSError: 파일 읽기 중 오류가 발생한 경우 발생합니다.
        
        Returns:
            str: 감지된 인코딩 (감지 실패 시 'utf-8' 반환)
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result.get('encoding')
            confidence = result.get('confidence', 0)
            if encoding is None:
                logging.warning(f"인코딩 감지 실패. 기본값 utf-8 사용. 파일 경로: {file_path}")
                return "utf-8"
            logging.info(f"Detected encoding: {encoding} (Confidence: {confidence})")
            return encoding
        except FileNotFoundError:
            logging.error(f"파일을 찾을 수 없습니다: {file_path}")
            raise
        except OSError as e:
            logging.error(f"파일 읽기 오류: {e}")
            raise

    def file_exists(self, file_path: str) -> bool:
        """파일이 존재하는지 확인합니다."""
        return os.path.isfile(file_path)

def show_message_box_safe(message: str, title: str = "오류", icon: Any = None) -> None:
    """안전하게 메시지 박스를 표시합니다. PyQt5가 설치되어 있지 않으면 로깅합니다."""
    try:
        from PyQt5.QtWidgets import QMessageBox
        if icon is None:
            icon = QMessageBox.Critical
        QMessageBox.critical(None, title, message)
    except ImportError:
        logging.warning("PyQt5가 설치되어 있지 않아 메시지 박스를 표시할 수 없습니다.")
        logging.error(message)

def load_json_file(file_path: str) -> dict:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON format: {file_path}")
        return {}
    except Exception as e:
        logging.error(f"Error loading file: {file_path} - {e}")
        return {}