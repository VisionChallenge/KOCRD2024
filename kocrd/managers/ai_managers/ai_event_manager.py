# kocrd/managers/ai_managers/ai_event_manager.py
import logging
from PIL import Image, UnidentifiedImageError  # PIL import 위치 변경

from kocrd.config.config import config
from kocrd.managers.ai_managers.ai_training_manager import AITrainingManager
from kocrd.User import FeedbackEventHandler
from kocrd.config.message.message_handler import MessageHandler
from kocrd.config.loader import ConfigLoader  # ConfigLoader import 추가

class AIEventManager:
    def __init__(self, system_manager, settings_manager, model_manager, ai_data_manager, error_handler, queues):
        self.system_manager = system_manager
        self.settings_manager = settings_manager
        self.model_manager = model_manager
        self.ai_data_manager = ai_data_manager
        self.error_handler = error_handler
        self.queues = queues
        self.ai_training_manager = AITrainingManager(model_manager, settings_manager, system_manager, ai_data_manager)
        self.feedback_event_handler = FeedbackEventHandler(ai_data_manager, error_handler)
        self.message_handler = MessageHandler()
        self.config_loader = ConfigLoader("path/to/config.json")  # ConfigLoader 인스턴스 생성

    def handle_message(self, ch, method, properties, body):
        self.config_loader.handle_message(self, ch, method, properties, body)  # config_loader.handle_message() 사용

    def handle_ocr_request(self, file_path):
        try:
            extracted_text = self._perform_ocr(file_path)
            self.system_manager.trigger_event("ocr_completed", {"file_path": file_path, "extracted_text": extracted_text})
        except Exception as e:
            self._handle_error("ocr_failed", "518", error=e, file_path=file_path)

    def _perform_ocr(self, file_path):
        ocr_engine_type = self.config_loader.get("ui.settings.ocr_engine")  # config_loader.get() 사용
        try:
            ocr_engine = self.config_loader.create_ocr_engine(ocr_engine_type)
            image = Image.open(file_path)
            extracted_text = ocr_engine.perform_ocr(image)
            return extracted_text
        except ValueError as e:
            self._handle_error("ocr_engine_error", "517", error=e) # 메시지 ID 사용
            raise
        except ImportError as e:
            self._handle_error("ocr_engine_error", "401") # 메시지 ID 사용
            raise
        except FileNotFoundError as e:
            self._handle_error("ocr_engine_error", "403") # 메시지 ID 사용
            raise
        except UnidentifiedImageError as e:
            self._handle_error("ocr_engine_error", "502", page_num="알 수 없는 페이지") # 메시지 ID 사용
            raise
        except Exception as e:
            self._handle_error("ocr_engine_error", "518", error=e) # 메시지 ID 사용
            raise

    def handle_training_start(self, features, label):
        try:
            data = self.ai_data_manager.load_data()
            if data is None:
                raise ValueError("No training data available. Please check the data source.")

            X_train, X_test, y_train, y_test = self.ai_training_manager.prepare_training_data(data, features, label)
            if X_train is None:
                raise ValueError("Failed to prepare training data. Please verify the feature and label configuration.")

            result = self.ai_training_manager.train_model((X_train, X_test, y_train, y_test), features, label)
            if result is None:
                raise ValueError("Model training failed. Please check the training process and parameters.")

            model_save_path = self.model_manager.save_model(result)
            if model_save_path:
                logging.info(f"Model saved to: {model_save_path}")

            self.system_manager.trigger_event("training_completed", {"model_path": model_save_path})

        except Exception as e:
            self._handle_error("training_failed", f"훈련 중 오류 발생: {e}")

    def handle_ocr_event(self, file_path, extracted_text):
        logging.info("Handling OCR completion event.")
        prediction_request = {
            "type": "PREDICT_DOCUMENT_TYPE",
            "data": {"text": extracted_text, "file_path": file_path},
            "reply_to": self.queues["events_queue"],
        }
        self.config_loader.send_message_to_queue(self.queues["prediction_requests"], prediction_request)  # config_loader.send_message_to_queue() 사용

    def handle_hyperparameter_change(self, hyperparameters):
        try:
            self.ai_training_manager.apply_parameters(hyperparameters)
            logging.info(f"Hyperparameters changed: {hyperparameters}")
            self.system_manager.trigger_event("hyperparameters_changed", hyperparameters)

        except (KeyError, ValueError) as e:
            self._handle_error("hyperparameters_change_failed", f"하이퍼파라미터 변경 중 오류 발생: {e}")
        except Exception as e:
            self._handle_error("hyperparameters_change_failed", f"하이퍼파라미터 변경 중 오류 발생: {e}")

    def handle_training_data_change(self, data_path):
        try:
            data = self.ai_data_manager.load_data(data_path)
            if data is None:
                raise ValueError("No training data available. Please check the data source.")
            logging.info(f"Training data changed: {data_path}")
            self.system_manager.trigger_event("training_data_changed", data_path)

        except (FileNotFoundError, ValueError) as e:
            self._handle_error("training_data_change_failed", f"훈련 데이터 변경 중 오류 발생: {e}")
        except Exception as e:
            self._handle_error("training_data_change_failed", f"훈련 데이터 변경 중 오류 발생: {e}")

    def handle_model_save_request(self, source_path, destination_path):
        try:
            config.file_manager.copy_file(source_path, destination_path)  # config.file_manager 사용
            logging.info(f"Model saved to {destination_path}")
        except Exception as e:
            self._handle_error("model_save_failed", f"모델 저장 중 오류 발생: {e}")

    def _handle_error(self, event_name, message_id, *args, **kwargs):
        config.handle_error(self.system_manager, "error", message_id, None,  *args, **kwargs) # config.handle_error() 사용
