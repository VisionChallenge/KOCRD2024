# kocrd/ 
# ├── __init__.py
# ├── main.py               # 프로그램 실행 진입점
# ├── user.py               # 사용자 정보와 권한 관리 
# ├── system.py             # 시스템 전반 관리
# └── system/                  # 각 기능별 매니저 모듈
#    ├── system_assistance.py
#    │   ├── ai_prediction_manager.py # AI 예측
#    │   ├── ai_data_manager.py     # AI 이벤트 처리
#    │   ├── ai_training_manager.py  # AI 모델 훈련
#    │   ├── ocr_utils.py           # OCR 유틸리티 함수들
#    │   ├── document_processor.py   # 문서 처리
#    │   ├── document_table_view.py  # 문서 테이블 뷰
#    │   ├── document_controller.py  # 문서 컨트롤러
#    │   ├── embedding_utils.py  # 접근 유틸리티 함수들
#    │   ├── file_utils.py     # 파일 유틸리티 함수들
#    │   ├── config.py
#    │   ├── ui.py   #UI
#    │   │   ├── class settings_ui  # 설정 다이얼로그 UI
#    │   │   └── class main_window # 메인 윈도우 UI 및 로직
#    │   ├── config/ 
#    │   │  ├── development.json
#    │   │  └── language/
#    │   │  	 ├── __init__.py
#    │   │  	 ├── ko.json
#    │   │  	 └── en.json
#    │   └── ui/ 
#    │	  	 ├── menubar_manager.py    # 메뉴바 관리
#    │	  	 ├── monitoring_ui_system.py # 모니터링 UI 관리
#    │	  	 └── document_ui_system.py # 문서 UI 관리
#    ├── main_window.py        # 메인 윈도우 UI 및 로직
#    ├── temp_file_manager.py    # 임시 파일 관리 (큐 메시지 처리)
#    ├── rabbitmq_manager.py    # RabbitMQ 관리
#    ├── ocr_manager.py         # OCR 작업
#    ├── ai_model_manager.py     # AI 모델 로드 및 관리
#    └── document_manager.py     # 문서 관리 (열기, 저장 등)
