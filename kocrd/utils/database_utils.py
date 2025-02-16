import logging
from sqlalchemy.exc import SQLAlchemyError

def execute_and_log(engine, query, params, success_message):
    """쿼리를 실행하고 성공 메시지를 로깅합니다."""
    try:
        with engine.connect() as conn:
            conn.execute(query, params)
        logging.info(success_message)
    except SQLAlchemyError as e:
        logging.error(f"Error executing query: {e}")
        raise

def execute_and_fetch(engine, query, error_message, params=None):
    """쿼리를 실행하고 결과를 반환합니다."""
    try:
        with engine.connect() as conn:
            result = conn.execute(query, params or {})
            return [dict(row) for row in result]
    except SQLAlchemyError as e:
        logging.error(f"{error_message}: {e}")
        return []
