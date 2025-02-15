import pika
import logging
from kocrd.config.loader import ConfigLoader
from kocrd.config.message.message_handler import MessageHandler

class RabbitMQManager:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.message_handler = MessageHandler(self.config_loader)
        self.connection = None
        self.channel = None
        self._connect()

    def _connect(self):
        try:
            rabbitmq_settings = self.config_loader.get_rabbitmq_settings()
            credentials = pika.PlainCredentials(rabbitmq_settings["RABBITMQ_USER"], rabbitmq_settings["RABBITMQ_PASSWORD"])
            parameters = pika.ConnectionParameters(
                host=rabbitmq_settings["RABBITMQ_HOST"],
                port=rabbitmq_settings["RABBITMQ_PORT"],
                virtual_host=rabbitmq_settings["RABBITMQ_VIRTUAL_HOST"],
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
            rabbitmq_settings["RABBITMQ_EVENTS_QUEUE"],
            rabbitmq_settings["RABBITMQ_PREDICTION_REQUESTS_QUEUE"],
            rabbitmq_settings["RABBITMQ_PREDICTION_RESULTS_QUEUE"],
            rabbitmq_settings["RABBITMQ_FEEDBACK_QUEUE"]
        ]
        for queue in queues:
            self.channel.queue_declare(queue=queue, durable=True)
            logging.info(f"🟢 큐 '{queue}' 선언 완료.")

    def publish(self, queue, message):
        try:
            self.channel.basic_publish(
                exchange=self.config_loader.get("rabbitmq.RABBITMQ_EXCHANGE_NAME"),
                routing_key=self.config_loader.get("rabbitmq.RABBITMQ_ROUTING_KEY"),
                body=message
            )
            logging.info(f"🟢 메시지 게시: {message} (큐: {queue})")
        except pika.exceptions.AMQPChannelError as e:
            logging.error(f"🔴 메시지 게시 실패: {e}")
        except Exception as e:
            logging.error(f"🔴 메시지 게시 중 오류: {e}")

    def consume(self, queue, callback):
        try:
            self.channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=False)
            logging.info(f"🟢 큐 '{queue}'에서 메시지 수신 시작.")
            self.channel.start_consuming()
        except pika.exceptions.AMQPChannelError as e:
            logging.error(f"🔴 메시지 수신 실패: {e}")
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

    def __del__(self):
        self.close()