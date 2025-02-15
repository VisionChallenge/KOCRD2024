# kocrd/config/message/message_handler.py
import json
import logging
from typing import Callable, Dict, Optional, Any
import os

from kocrd.config.loader import ConfigLoader

class MessageHandler:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.message_handlers: Dict[str, Callable[[str, Dict[str, Any]], None]] = {
            "MSG": self._handle_message,
            "LOG": self._handle_message,
            "WARN": self._handle_message,
            "ERR": self._handle_message,
            "ID": self._handle_message,
            "OCR": self._handle_message,
        }

    def get_message(self, message_id: str, *args, **kwargs) -> Optional[str]:
        return self.config_loader.get_message(message_id, *args, **kwargs)

    def _handle_message(self, message_id, data, message_type):
        try:
            message = self.get_message(message_id, **data)
            if message_type in ["LOG", "WARN", "ERR", "ID", "MSG"]:
                log_function = getattr(logging, message_type.lower())
                log_function(message)
            elif message_type == "OCR":
                self.training_event_handler.handle_ocr_request(data.get("file_path"))
                logging.info(message)
        except Exception as e:
            logging.error(f"Error handling {message_type} message: {message_id} - {e}")

    def process_message(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            message_type = message.get("type")
            message_id = message.get("id")
            data = message.get("data", {})
            handler = self.message_handlers.get(message_type)

            if handler:
                handler(message_id, data, message_type)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                logging.warning(f"Unknown message type: {message_type}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        except json.JSONDecodeError as e:
            logging.error(f"JSON 파싱 오류: {body} - {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logging.error(f"메시지 처리 중 오류: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)