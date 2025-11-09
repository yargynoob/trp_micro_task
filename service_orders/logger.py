"""
Модуль для структурированного логирования в Service Orders
"""
import logging
import json
import sys
from datetime import datetime
from flask import request, g
import traceback

class StructuredLogger:
    """Класс для структурированного логирования в JSON формате"""
    
    def __init__(self, name, level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Удаляем существующие handlers
        self.logger.handlers = []
        
        # Создаем handler для вывода в консоль
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        # Используем JSON formatter
        formatter = JsonFormatter()
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        self.logger.propagate = False
    
    def _get_context(self):
        """Получение контекстной информации из запроса"""
        context = {}
        
        # Пытаемся получить информацию из Flask request context
        try:
            if request:
                context['request_id'] = getattr(g, 'request_id', None) or request.headers.get('X-Request-ID')
                context['method'] = request.method
                context['path'] = request.path
                context['remote_addr'] = request.remote_addr
                
                # Информация о пользователе из токена
                if hasattr(request, 'user') and request.user:
                    context['user_id'] = request.user.get('user_id')
                    context['user_email'] = request.user.get('email')
        except RuntimeError:
            # Нет контекста Flask
            pass
        
        return context
    
    def info(self, message, **kwargs):
        """Логирование информационного сообщения"""
        extra = self._get_context()
        extra.update(kwargs)
        self.logger.info(message, extra={'structured': extra})
    
    def error(self, message, exc_info=None, **kwargs):
        """Логирование ошибки"""
        extra = self._get_context()
        extra.update(kwargs)
        
        if exc_info:
            extra['exception'] = {
                'type': exc_info.__class__.__name__,
                'message': str(exc_info),
                'traceback': traceback.format_exc()
            }
        
        self.logger.error(message, extra={'structured': extra})
    
    def warning(self, message, **kwargs):
        """Логирование предупреждения"""
        extra = self._get_context()
        extra.update(kwargs)
        self.logger.warning(message, extra={'structured': extra})
    
    def debug(self, message, **kwargs):
        """Логирование отладочной информации"""
        extra = self._get_context()
        extra.update(kwargs)
        self.logger.debug(message, extra={'structured': extra})

class JsonFormatter(logging.Formatter):
    """Formatter для вывода логов в JSON формате"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'service': 'service_orders'
        }
        
        # Добавляем структурированные данные
        if hasattr(record, 'structured'):
            log_data.update(record.structured)
        
        # Добавляем информацию об исключении
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data, ensure_ascii=False)

# Создаем глобальный экземпляр логгера
logger = StructuredLogger('service_orders')

def log_request():
    """Middleware для логирования входящих запросов"""
    from flask import g
    
    # Получаем request_id из заголовков
    request_id = request.headers.get('X-Request-ID', 'unknown')
    g.request_id = request_id
    
    # Логируем входящий запрос
    logger.info(
        'Incoming request',
        method=request.method,
        path=request.path,
        query_params=dict(request.args),
        request_id=request_id
    )

def log_response(response):
    """Middleware для логирования ответов"""
    # Добавляем X-Request-ID в заголовки ответа
    if hasattr(g, 'request_id'):
        response.headers['X-Request-ID'] = g.request_id
    
    # Логируем ответ
    logger.info(
        'Outgoing response',
        status_code=response.status_code,
        content_length=response.content_length
    )
    
    return response
