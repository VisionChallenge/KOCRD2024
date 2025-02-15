# kocrd/managers/ai_managers/ai_ocr_running.py
import logging
import json
import pika
import time
from typing import Callable, Dict, Any

import pika.exceptions
from kocrd.config.loader import ConfigLoader  # ConfigLoader import 추가

from kocrd.managers.ai_managers.ai_model_manager import AIModelManager

class AIOCRRunning:
    def __init__(self, system_manager, ai_data_manager):
        self.system_manager = system_manager
        self.ai_data_manager = ai_data_manager
        self.ai_model_manager = AIModelManager.get_instance()
        self.rabbitmq_manager = self.ai_model_manager.rabbitmq_manager
        self.config_loader = ConfigLoader("path/to/config.json")  # ConfigLoader 인스턴스 생성

    def create_ai_request(self, message_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": message_type,
            "data": data,
            "reply_to": self.config_loader.get("queues.events")  # config_loader.get() 사용
        }

    def handle_ocr_result(self, ch, method, properties, body):
        """OCR 결과 메시지 처리."""
        self.config_loader.handle_message(self, ch, method, properties, body)  # config_loader.handle_message() 사용
        try:
            message = json.loads(body)
            self.config_loader.send_message_to_queue("events_queue", message)  # config_loader.send_message_to_queue() 사용
        except json.JSONDecodeError as e:
            logging.error(f"JSON 디코딩 오류: {e}. 메시지 내용: {body}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logging.error(f"메시지 처리 오류: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def consume_messages(self, queue_name: str, callback: Callable):
        """메시지 소비."""
        try:
            self.rabbitmq_manager.start_consuming_specific_queue(queue_name, callback)
            self.rabbitmq_manager.channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"RabbitMQ 연결 오류: {e}")
            print(f"RabbitMQ 연결에 실패했습니다. 5초 후 재시도합니다: {e}")
            time.sleep(5)
            self.consume_messages(queue_name, callback)  # 재귀 호출을 통한 재시도
        except KeyboardInterrupt:
            print('프로그램을 종료합니다.')
            self.rabbitmq_manager.close_connection()
        except Exception as e:
            logging.error(f"메시지 소비 중 오류: {e}")
            self.rabbitmq_manager.close_connection()

    def main(self):
        queue_name = self.config_loader.get("queues.ocr_results")  # config_loader.get() 사용
        self.consume_messages(queue_name, self.handle_ocr_result)