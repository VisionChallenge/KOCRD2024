# ai_managers/ai_model_manager.py
import logging
import os
from typing import Optional, Tuple, Dict, Any

import tensorflow as tf
from transformers import GPT2Tokenizer, GPT2LMHeadModel

from kocrd.config.config import config
from kocrd_cpy.system.database_manager import DatabaseManager
from kocrd.managers.ai_managers.ai_training_manager import AITrainingManager
from kocrd.config.message.message_handler import MessageHandler
from kocrd.config.loader import ConfigLoader

def singleton(cls):
    instances = {}

    def getinstance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return singleton


@singleton
class AIModelManager:
    def __init__(self, database_manager: DatabaseManager, ai_training_manager: AITrainingManager, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.model_path = self.config_loader.get("file_paths.ai_model_path")
        self.gpt_model_path = self.config_loader.get("file_paths.gpt_model_path", "gpt2")
        self.model: Optional[tf.keras.Model] = None
        self.tokenizer: Optional[GPT2Tokenizer] = None
        self.gpt_model: Optional[GPT2LMHeadModel] = None
        self.database_manager = database_manager
        self.ai_training_manager = ai_training_manager
        self.message_handler = MessageHandler()
        self._load_models()
        self.config = config  # Config 객체를 사용하도록 변경

    def _handle_error(self, event_name, message_id, *args, **kwargs):
        config.handle_error(event_name, message_id, None, *args, **kwargs)

    def _load_models(self):
        self.model = self.config_loader.load_tensorflow_model(self.model_path)
        self.tokenizer, self.gpt_model = self.config_loader.load_gpt_model(self.gpt_model_path)

    def request_ai_training(self, features, label):
        try:
            logging.info("AI 학습 시작")
            self.train_ai(features, label)
            logging.info("AI 학습 완료")
        except Exception as e:
            self.config_loader.handle_error(self. "ai_training_error", "505", error=e)
            raise

    def train_ai(self, features, label):
        """AI 모델 학습."""
        try:
            # 학습 데이터 준비
            data = self.database_manager.load_training_data()
            if data is None:
                raise ValueError("No training data available. Please check the data source.")

            # 모델 생성
            model_type = self.config_loader.get("ui.settings.ai_model", "classification")
            self.model = self.config_loader.create_ai_model(model_type)
            if self.model is None:
                raise ValueError(f"AI 모델 생성 실패: {model_type}")

            # 모델 학습
            self.ai_training_manager.train_model(self.model, data, features, label)

        except Exception as e:
            self.config_loader.handle_error(self. "ai_model_training_error", "505", error=e)
            raise

    def generate_text(self, command: str) -> Optional[str]:
        """GPT 모델을 사용하여 텍스트 생성"""
        if not self.tokenizer or not self.gpt_model:
            logging.error("GPT 모델 또는 토크나이저가 초기화되지 않았습니다.")
            return "GPT 모델 초기화 오류"
        try:
            input_ids = self.tokenizer.encode(command, return_tensors="pt")
            pad_token_id = self.tokenizer.pad_token_id or self.tokenizer.eos_token_id
            attention_mask = (input_ids != pad_token_id).long()
            output = self.gpt_model.generate(input_ids=input_ids, attention_mask=attention_mask, max_new_tokens=50,
                                            pad_token_id=pad_token_id)
            return self.tokenizer.decode(output[0], skip_special_tokens=True)
        except Exception as e:
            self.config_loader.handle_error(self.system_manager, "gpt_text_generation_error", "505", error=e)
            return "GPT 텍스트 생성 오류"

    def save_generated_text_to_db(self, file_name: str, text: str):
        """생성된 텍스트를 데이터베이스에 저장."""
        if not self.database_manager:
            logging.error("DatabaseManager가 설정되지 않았습니다.")
            return

        try:
            self.database_manager.save_text(file_name, text)
            logging.info(f"Generated text saved to database: {file_name}")
        except Exception as e:
            self.config_loader.handle_error(self.system_manager, "text_save_error", "505", error=e)
            raise

    def save_model(self, save_path: str) -> None:
        """모델 저장."""
        if not self.model:
            raise ValueError("저장할 모델이 없습니다.")
        try:
            self.model.save(save_path)
            logging.info(f"모델 저장 완료: {save_path}")
        except Exception as e:
            self.config_loader.handle_error(self.system_manager, "model_save_error", "505", error=e)
            raise

    def apply_trained_model(self, model_path: str) -> None:
        """학습된 모델 적용."""
        try:
            logging.info(f"학습된 모델 로딩 중: {model_path}")
            self.model = tf.keras.models.load_model(model_path)
            logging.info("모델 로딩 완료")
        except FileNotFoundError as e:
            self.config_loader.handle_error(self.system_manager, "model_file_error", "505", error=e, model_path=model_path)
            raise
        except Exception as e:
            self.config_loader.handle_error(self.system_manager, "model_apply_error", "505", error=e)
            raise