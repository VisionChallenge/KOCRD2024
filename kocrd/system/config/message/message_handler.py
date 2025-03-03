# kocrd/config/message/message_handler.py
import json
import logging
from typing import Callable, Dict, Optional, Any
import os
import pika
from kocrd.system.config.config_module import Config, LanguageController
from typing import Dict, Callable, Any, Optional

class MessageHandler:
    def __init__(self, config):
        self.config = Config
        self.language_controller = LanguageController
        self.message_handlers: Dict[str, Callable[[str, Dict[str, Any]], Optional[str]]] = {
            "MSG": self._handle_message,
            "LOG": self._handle_message,
            "WARN": self._handle_message,
            "ERR": self._handle_message,
            "ID": self._handle_message,
            "OCR": self._handle_message,
        }

    def _handle_message(self, message_id: str, data: Dict[str, Any], message_type: str) -> Optional[str]:
        """메시지 타입과 메시지 ID에 해당하는 메시지를 반환합니다."""
        return self.language_controller.get_message(message_type, message_id)
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

    def send_message(self, queue_name, message):
        try:
            # 큐에 메시지 전송 로직 구현 (pika 사용 등)
            logging.info(f"Message sent to queue '{queue_name}': {message}")
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"RabbitMQ 연결 오류: {e}")
            raise
