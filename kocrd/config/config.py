# kocrd/config/config.py

import json
import logging
from datetime import datetime
import os
from typing import Dict, Any, List, Union, Optional

# 실제 애플리케이션에서는 이 설정이 main.py 등 애플리케이션 진입점에서 이루어지는 것이 일반적입니다.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
class ConfigLoader:
    @staticmethod
    def load_json_file(file_path: str) -> Dict[str, Any]:
        """JSON 파일을 로드합니다."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {file_path}: {e}")
            return {}

class TextManager:
    """ 애플리케이션의 모든 텍스트(일반 메시지, 로그 메시지, UI 레이블 등)를 관리하는 클래스입니다.
    다국어 지원과 언어팩에 텍스트가 없는 경우 기본값(영어)으로 폴백하는 기능을 제공합니다.
    이 클래스는 싱글톤 패턴으로 구현되어 애플리케이션 전체에서 하나의 인스턴스만 존재하도록 보장합니다."""
    _instance: Optional['TextManager'] = None # 싱글톤 인스턴스를 저장할 클래스 변수

    def __new__(cls, *args, **kwargs):
        """
        싱글톤 패턴을 구현하는 메서드.
        TextManager의 인스턴스가 아직 없으면 새로 생성하고, 이미 있으면 기존 인스턴스를 반환합니다.
        """
        if cls._instance is None:
            cls._instance = super(TextManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, lang_dir: str = 'kocrd/config/language', # 언어팩 파일들이 저장된 디렉토리
                 default_texts_path: str = 'kocrd/config/default_texts.json'): # 병합된 기본 메시지/UI 파일 경로
        """
        TextManager를 초기화합니다.
        _initialized 플래그를 사용하여 싱글톤 인스턴스가 한 번만 초기화되도록 합니다.
        """
        if not hasattr(self, '_initialized'): # 이미 초기화되었는지 확인
            self._initialized = True # 초기화 플래그 설정
            self.lang_dir = lang_dir
            # default_texts.json의 "messages" 최상위 키 아래의 모든 내용 (general, log, ui)을 저장
            self.default_texts: Dict[str, Any] = {}
            self.lang_packs: Dict[str, Dict[str, Any]] = {} # 로드된 모든 언어팩 (예: {'ko': {...}, 'en': {...}})
            self.current_lang_pack: Dict[str, Any] = {} # 현재 활성화된 언어팩 (set_language 호출 시 업데이트됨)
            self.active_language_code: str = 'default' # 현재 활성화된 언어 코드 (예: 'ko', 'en', 'default')

            # 병합된 기본 텍스트 파일(default_texts.json)을 로드합니다.
            self._load_default_texts(default_texts_path)
            # 모든 언어팩 파일들을 로드합니다.
            self._load_all_language_packs()
            
            # 애플리케이션 시작 시 기본 언어를 'ko'로 설정 시도합니다.
            # 만약 'ko' 언어팩이 없으면 자동으로 'default' (default_texts.json의 기본값)로 폴백됩니다.
            self.set_language('ko')

    def _load_default_texts(self, default_texts_path: str):
        """
        default_texts.json 파일을 로드하여 기본 텍스트를 설정합니다.
        파일의 "messages" 키 아래 내용이 self.default_texts에 저장됩니다.
        """
        all_data = ConfigLoader.load_json_file(default_texts_path)
        # default_texts.json의 "messages" 최상위 키 아래의 내용을 가져옵니다.
        self.default_texts = all_data.get("messages", {})
        logging.info(f"Default texts (messages and UI) loaded from {default_texts_path}")

    def _load_all_language_packs(self):
        """
        'kocrd/config/language' 디렉토리 내의 모든 JSON 파일을 언어팩으로 로드합니다.
        각 언어팩은 default_texts.json의 구조와 유사하게 'general', 'log', 'ui' 등의
        최상위 카테고리를 포함하도록 병합됩니다.
        """
        self.lang_packs: Dict[str, Dict[str, Any]] = {}
        if os.path.exists(self.lang_dir):
            for filename in os.listdir(self.lang_dir):
                if filename.endswith(".json"):
                    lang_code = filename[:-5]
                    lang_path = os.path.join(self.lang_dir, filename)
                    lang_data = ConfigLoader.load_json_file(lang_path)
                    
                    # 언어팩 데이터가 'general', 'log', 'ui' 최상위 키를 가지며 
                    # 그 아래에 해당 언어의 텍스트가 정의되어 있다고 가정합니다.
                    merged_pack = {
                        "general": lang_data.get("general", {}),
                        "log": lang_data.get("log", {}),
                        "ui": lang_data.get("ui", {})
                    }
                    self.lang_packs[lang_code] = merged_pack
                    logging.info(f"Language pack '{lang_code}' loaded from {lang_path}")
        else:
            logging.warning(f"Language directory '{self.lang_dir}' not found. No additional language packs will be loaded.")

    def set_language(self, lang_code: str):
        """
        애플리케이션의 활성 언어를 설정합니다.
        지정된 'lang_code'에 해당하는 언어팩이 'lang_packs'에 존재하면 해당 언어로 설정하고,
        존재하지 않거나 'default'로 설정하면 기본 텍스트(default_texts.json)를 사용합니다.
        """
        if lang_code in self.lang_packs:
            self.active_language_code = lang_code
            self.current_lang_pack = self.lang_packs[lang_code]
            logging.info(f"Active language set to '{lang_code}'.")
        elif lang_code == 'default':
            self.active_language_code = 'default'
            self.current_lang_pack = {} # 언어팩을 비워 기본 팩으로만 동작하도록 합니다.
            logging.info("Active language set to 'default'.")
        else:
            logging.warning(f"Language pack for '{lang_code}' not found. Using default texts.")
            self.active_language_code = 'default'
            self.current_lang_pack = {}

    def _get_nested_value(self, data: Dict[str, Any], path_segments: List[str]) -> Optional[Any]:
        """
        딕셔너리 또는 리스트에서 점(.)으로 구분된 경로 세그먼트(예: "table_columns.0.name")를 사용하여
        중첩된 값을 안전하게 가져옵니다. 딕셔너리 키와 리스트 인덱스 모두 처리합니다.
        경로 중간에 값이 없거나 타입이 일치하지 않으면 None을 반환합니다.
        """
        current_data = data
        for segment in path_segments:
            if isinstance(current_data, dict):
                current_data = current_data.get(segment)
            elif isinstance(current_data, list) and segment.isdigit():
                try:
                    index = int(segment)
                    if 0 <= index < len(current_data):
                        current_data = current_data[index]
                    else:
                        return None
                except ValueError:
                    return None
            else:
                return None
            
            if current_data is None:
                return None
        return current_data

    def get_text(self, *path_segments: str, **replacements: Any) -> Union[str, List[Any], Dict[str, Any]]:
        """
        지정된 경로 세그먼트(예: "general", "701" 또는 "ui", "components", "menus", "0", "name")를 기반으로
        텍스트를 검색하고 포맷팅합니다.
        
        검색 우선순위:
        1. 현재 활성화된 언어팩 (self.current_lang_pack)
        2. 기본 텍스트 (self.default_texts - default_texts.json에서 로드된 전체 내용)
        
        :param path_segments: 텍스트가 저장된 JSON 경로를 나타내는 가변 인자(문자열).
                              첫 번째 세그먼트는 'general', 'log', 'ui'와 같은 최상위 카테고리여야 합니다.
        :param replacements: 메시지 내의 플레이스홀더({key})를 대체할 키워드 인자.
        :return: 포맷팅된 문자열, 또는 경로가 가리키는 값이 문자열이 아닌 경우 리스트나 딕셔너리.
                 텍스트를 찾지 못하거나 포맷팅 오류 발생 시 오류 메시지 문자열을 반환합니다.
        """
        if not path_segments:
            logging.error("No path segments provided to get_text.")
            return "ERROR: No text path provided."

        text_template: Optional[Union[str, List[Any], Dict[str, Any]]] = None

        # 1. 현재 언어 팩에서 텍스트 탐색 시도
        if self.current_lang_pack:
            text_template = self._get_nested_value(self.current_lang_pack, list(path_segments))

        # 2. 현재 언어 팩에서 텍스트를 찾지 못하면 기본 팩에서 탐색 시도
        if text_template is None:
            text_template = self._get_nested_value(self.default_texts, list(path_segments))

        if text_template is not None:
            # 결과가 딕셔너리이고 'name' 키를 포함하는 경우 (UI 요소에서 흔함), 'name' 값으로 대체
            # 예: {"name": "File", "actions": [...]} -> "File"만 가져옴
            if isinstance(text_template, dict) and "name" in text_template and len(path_segments) > 0 and path_segments[-1] == "name":
                # 만약 경로의 마지막 세그먼트가 'name'이고, 그 결과가 dict이고 'name' 키를 가진다면
                # 해당 'name'의 값을 텍스트로 사용합니다. (ui.json의 "name": "파일" 같은 경우)
                text_template = text_template["name"]
            elif isinstance(text_template, dict) and "label" in text_template and len(path_segments) > 0 and path_segments[-1] == "label":
                # 버튼 등에서 "label" 필드가 텍스트인 경우
                text_template = text_template["label"]
            
            if isinstance(text_template, str):
                try:
                    return text_template.format(**replacements)
                except KeyError as e:
                    logging.error(f"Missing replacement key '{e}' for text path '{'.'.join(path_segments)}'. Raw template: '{text_template}'")
                    return f"FORMAT_ERROR: Missing key '{e}' for '{'.'.join(path_segments)}'"
                except Exception as e:
                    logging.error(f"Error formatting text for path '{'.'.join(path_segments)}': {e}. Raw template: '{text_template}'")
                    return f"FORMAT_ERROR: {'.'.join(path_segments)} ({e})"
            else:
                logging.debug(f"Retrieved non-string text for path '{'.'.join(path_segments)}'. Returning raw data.")
                return text_template
        else:
            logging.warning(f"Text not found for path: '{'.'.join(path_segments)}'.")
            return f"TEXT_NOT_FOUND: {'.'.join(path_segments)}"

# TextManager의 전역 싱글톤 인스턴스를 생성합니다.
text_manager = TextManager(default_texts_path='kocrd/config/default_texts.json')

class FilePathConfig:
    def __init__(self, config: Dict[str, Any]):
        self.models = config["models"]
        self.document_embedding = config["document_embedding"]
        self.document_types = config["document_types"]
        self.temp_files = config["temp_files"]

class LanguageConfig:
    def __init__(self, lang_dir: str):
        self.lang_packs = {}
        for filename in os.listdir(lang_dir):
            if filename.endswith(".json"):
                lang_code = filename[:-5]
                lang_path = os.path.join(lang_dir, filename)
                try:
                    with open(lang_path, "r", encoding="utf-8") as f:
                        lang_pack = json.load(f)
                        if "language" not in lang_pack:
                            raise ValueError(f"Language pack '{filename}' must have 'language' attribute.")
                        self.lang_packs[lang_code] = lang_pack
                except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
                    print(f"Error loading language pack '{filename}': {e}")

    def load_language_pack(self, lang_code: str) -> Dict[str, Any]:
        lang_path = os.path.join(LANG_DIR, f"{lang_code}.json")
        try:
            with open(lang_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading default language pack '{lang_code}': {e}")
            return {}
class AppConfig:
    """애플리케이션의 정적 설정 데이터를 중앙 관리하는 클래스입니다.managers.json, queues.json, ui.json(텍스트 제외), 그리고 기타 고정된 경로 등을 포함합니다."""
    # Manager 설정 (kocrd/config/managers.json에서 로드)
    # .get("managers", {})를 사용하여 파일에 "managers" 키가 없어도 오류 없이 빈 딕셔너리 반환
    MANAGERS: Dict[str, Any] = ConfigLoader.load_json_file('kocrd/config/managers.json').get("managers", {})

    # Queue 설정 (kocrd/config/queues.json에서 로드)
    QUEUES: Dict[str, Any] = ConfigLoader.load_json_file('kocrd/config/queues.json').get("queues", {})

    # 파일 경로 설정 (이전 config.py의 FilePathConfig와 유사한 역할)
    # 실제 파일 시스템 경로를 나타내는 정적 데이터
    FILE_PATHS: Dict[str, str] = {
        "models": "model/", # 모델 파일 디렉토리
        "document_embedding": "embeddings/", # 문서 임베딩 저장 디렉토리
        "document_types": "document_types/", # 문서 타입 정의 파일 디렉토리
        "temp_files": "temp/" # 임시 파일 저장 디렉토리
    }
    
    # OCR 도구 설정 (Tesseract 경로 등)
    OCR_SETTINGS: Dict[str, str] = {
        "tesseract_cmd": "C:/Program Files/Tesseract-OCR/tesseract.exe", # Tesseract 실행 파일 경로
        "tessdata_dir": "C:/Program Files/Tesseract-OCR/tessdata" # Tesseract 훈련 데이터 경로
    }
    # UI_SETTINGS는 이제 default_texts.json의 "ui" 카테고리 전체를 참조합니다.
    UI_SETTINGS: Dict[str, Any] = text_manager.default_texts.get('ui', {})

    # 기타 정적 설정들을 여기에 추가할 수 있습니다.
    DATABASE_URL: str = "dev_database_url" # 데이터베이스 연결 URL

    FILE_HANDLING_SETTINGS: Dict[str, Any] = {
        "default_report_filename": "report.txt",
        "default_excel_filename": "documents.xlsx",
        "valid_file_extensions": {'.pdf', '.docx', '.xlsx', '.txt', '.csv', '.png', '.jpg', '.jpeg'},
        "max_file_size": 10 * 1024 * 1024  # 10MB
    }

# --- 전략 패턴을 위한 인터페이스 및 팩토리 클래스 정의 ---
# 이 부분은 변경 없이 그대로 유지됩니다. 설정 값은 AppConfig에서 가져오도록 수정합니다.
class OCREngine:
    """OCR 엔진의 인터페이스 (추상 클래스)"""
    def perform_ocr(self, image: Any) -> str:
        raise NotImplementedError

class TesseractOCR(OCREngine):
    """Tesseract OCR 엔진 구현"""
    def perform_ocr(self, image: Any) -> str:
        import pytesseract
        # Tesseract 실행 경로 및 데이터 경로를 OCR_SETTINGS에서 가져와 설정
        pytesseract.pytesseract.tesseract_cmd = AppConfig.OCR_SETTINGS["tesseract_cmd"]
        # pytesseract.pytesseract.tessdata_dir_config = f'--tessdata-dir "{AppConfig.OCR_SETTINGS["tessdata_dir"]}"' # 필요시 설정
        return pytesseract.image_to_string(image)

class CloudVisionOCR(OCREngine):
    """Google Cloud Vision OCR 엔진 구현 (예시)"""
    def perform_ocr(self, image: Any) -> str:
        # Cloud Vision API 호출 로직 (실제 구현 필요)
        logging.info("Calling Cloud Vision API (dummy implementation)")
        return "Cloud Vision OCR result (dummy)"

class AIModel:
    """AI 모델의 인터페이스 (추상 클래스)"""
    def predict(self, data: Any) -> Any:
        raise NotImplementedError

class ClassificationModel(AIModel):
    """문서 분류 AI 모델 구현 (예시)"""
    def predict(self, data: Any) -> Any:
        # 분류 모델 예측 로직 (실제 구현 필요)
        logging.info(f"Performing classification prediction on: {data[:50]}...") # 데이터 일부만 로깅
        return "classified_document_type"

class ObjectDetectionModel(AIModel):
    """객체 탐지 AI 모델 구현 (예시)"""
    def predict(self, data: Any) -> Any:
        # 객체 탐지 모델 예측 로직 (실제 구현 필요)
        logging.info("Performing object detection (dummy implementation)")
        return {"objects_detected": ["dummy_object1", "dummy_object2"]}

# 팩토리 패턴을 위한 팩토리 클래스 정의
class OCREngineFactory:
    """OCR 엔진 객체를 생성하는 팩토리 클래스"""
    @staticmethod
    def create_engine(engine_type: str) -> OCREngine:
        if engine_type == "tesseract":
            return TesseractOCR()
        elif engine_type == "cloud_vision":
            return CloudVisionOCR()
        else:
            raise ValueError(f"Unknown OCR engine type: {engine_type}")

class AIModelFactory:
    """AI 모델 객체를 생성하는 팩토리 클래스"""
    @staticmethod
    def create_model(model_type: str) -> AIModel:
        if model_type == "classification":
            return ClassificationModel()
        elif model_type == "object_detection":
            return ObjectDetectionModel()
        else:
            raise ValueError(f"Unknown AI model type: {model_type}")

# 설정 파일에서 전략 선택 (AppConfig.UI_SETTINGS를 통해 접근)
# ui.json 내에 "settings" 키가 있다면 해당 키에서 "ocr_engine"과 "ai_model"을 가져옵니다.
ocr_engine_type = AppConfig.UI_SETTINGS.get("settings", {}).get("ocr_engine", "tesseract")
ai_model_type = AppConfig.UI_SETTINGS.get("settings", {}).get("ai_model", "classification")

# 팩토리를 사용하여 OCR 엔진 및 AI 모델 객체 생성
ocr_engine = OCREngineFactory.create_engine(ocr_engine_type)
ai_model = AIModelFactory.create_model(ai_model_type)
