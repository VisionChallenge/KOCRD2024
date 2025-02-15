# kocrd/managers/ai_managers/ai_training_manager.py
import logging
import json
import os
from sklearn.model_selection import train_test_split
from PyQt5.QtWidgets import QMessageBox

from kocrd.config.config import config

class AITrainingManager:
    def __init__(self, model_manager, settings_manager, system_manager, ai_data_manager):
        self.model_manager = model_manager
        self.settings_manager = settings_manager
        self.system_manager = system_manager
        self.ai_data_manager = ai_data_manager
        self.document_embedding_path = self.settings_manager.get_setting("document_embedding_path")

    def prepare_training_data(self, data, features, label):
        try:
            X = data[features]
            y = data[label]
            return train_test_split(X, y, test_size=0.2)
        except KeyError as e:
            logging.error(config.get_message("501", error=e))
            return None, None, None, None
        except Exception as e:
            logging.error(config.get_message("505", error=e))
            return None, None, None, None

    def train_model(self, data, features, label):
        """모델을 훈련합니다."""
        try:
            if self.model_manager.model is None:
                raise ValueError("학습할 TensorFlow 모델이 없습니다.")
            logging.info("AI 모델 학습 시작...")

            # 문서 분석 중지
            self.system_manager.stop_document_analysis()

            # 이전 문서와 데이터베이스 검토
            previous_data = self.ai_data_manager.load_previous_data()
            self.model_manager.train_with_previous_data(previous_data)

            result = self.model_manager.train(data, features, label)
            logging.info("AI 모델 학습 완료.")

            # 문서 분석 재개
            self.system_manager.start_document_analysis()

            return result
        except ValueError as e:
            logging.error(config.get_message("05", error=e, category="error")) # config.get_message() 사용, category 추가
            return None
        except Exception as e:
            logging.error(config.get_message("05", error=e, category="error")) # config.get_message() 사용, category 추가
            return None

    def apply_parameters(self, parameters):
        """모델에 하이퍼파라미터 적용."""
        try:
            self.model_manager.apply_parameters(parameters)
            logging.info("Parameters applied successfully.")
        except Exception as e:
            logging.error(config.get_message("05", error=e, category="error")) # config.get_message() 사용, category 추가

    def train_with_parameters(self, file_path, features, label):
        """사용자가 제공한 파라미터 파일로 모델을 학습."""
        try:
            with open(file_path, "r", encoding="utf-8") as param_file:
                parameters = json.load(param_file)
            self.apply_parameters(parameters)
            data = self.ai_data_manager.load_data()
            if data is not None:
                self.train_model(data, features, label)
            logging.info("Model training completed with provided parameters.")
            QMessageBox.information(None, "학습 완료", "모델 학습이 성공적으로 완료되었습니다.")
        except json.JSONDecodeError as e:
            logging.error(config.get_message("512", error=e, category="file_error")) # config.get_message() 사용, category 추가
        except FileNotFoundError as e:
            logging.error(config.get_message("505", error=e, category="file_error")) # config.get_message() 사용, category 추가
        except Exception as e:
            logging.error(config.get_message("505", error=e, category="training_error")) # config.get_message() 사용, category 추가