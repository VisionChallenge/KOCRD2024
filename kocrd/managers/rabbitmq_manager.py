import pika
import logging
import json
import os
from kocrd.config.loader import ConfigLoader, load_json, merge_configs, get_temp_dir
from kocrd.config.message.message_handler import MessageHandler

class RabbitMQManager:
    def __init__(self, config):
        self.config = config
        self.host = config.get("rabbitmq.host")
        self.port = config.get("rabbitmq.port")
        self.user = config.get("rabbitmq.user")
        self.password = config.get("rabbitmq.password")
        self.virtual_host = config.get("rabbitmq.virtual_host")
        self.message_handler = MessageHandler(self.config)
        self.connection = None
        self.channel = None
        self._connect()

    def _connect(self):
        try:
            rabbitmq_settings = self.config
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.virtual_host,
                credentials=credentials
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            self._declare_queues(rabbitmq_settings)

            logging.info("🟢 RabbitMQ 연결 및 채널 생성 완료.")

        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"🔴 RabbitMQ 연결 실패: {e}")
            raise

        except Exception as e:
            logging.error(f"🔴 RabbitMQ 설정 중 오류: {e}")
            raise

    def _declare_queues(self, rabbitmq_settings):
        queues = [
            rabbitmq_settings["rabbitmq.events_queue"],
            rabbitmq_settings["rabbitmq.prediction_requests_queue"],
            rabbitmq_settings["rabbitmq.prediction_results_queue"],
            rabbitmq_settings["rabbitmq.feedback_queue"]
        ]
        for queue in queues:
            self.channel.queue_declare(queue=queue, durable=True)  # durable=True: 큐가 broker 재시작 후에도 유지되도록 설정
            logging.info(f"🟢 큐 '{queue}' 선언 완료.")

    def publish(self, queue, message):
        try:
            self.channel.basic_publish(
                exchange=self.config.get("rabbitmq.exchange_name"), # exchange 이름 설정
                routing_key=self.config.get("rabbitmq.routing_key"), # routing key 설정
                body=message
            )
            logging.info(f"🟢 메시지 게시: {message} (큐: {queue})")
        except pika.exceptions.AMQPChannelError as e:
            logging.error(f"🔴 메시지 게시 실패: {e}")
            # 재연결 시도 등의 추가 로직 고려
        except Exception as e:
            logging.error(f"🔴 메시지 게시 중 오류: {e}")

    def consume(self, queue, callback):
        try:
            self.channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=False)
            logging.info(f"🟢 큐 '{queue}'에서 메시지 수신 시작.")
            self.channel.start_consuming()  # 이 메서드는 blocking 메서드입니다.
        except pika.exceptions.AMQPChannelError as e:
            logging.error(f"🔴 메시지 수신 실패: {e}")
            # 재연결 시도 등의 추가 로직 고려
        except KeyboardInterrupt:
            logging.info("🟢 수동 인터럽트 발생. RabbitMQ 수신 중지.")
            self.stop_consuming()
        except Exception as e:
            logging.error(f"🔴 메시지 수신 중 오류: {e}")

    def stop_consuming(self):
        if self.channel and self.channel.is_open:
            self.channel.stop_consuming()

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
            logging.info("🟢 RabbitMQ 연결 종료.")

    def __del__(self): # RabbitMQManager 객체가 사라질때 close() 호출
        self.close()