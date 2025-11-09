"""
Улучшенный Circuit Breaker для API Gateway
"""
from datetime import datetime, timedelta
import threading
from logger import logger

class CircuitBreaker:
    """
    Улучшенный Circuit Breaker с метриками и статусом
    
    Состояния:
    - closed: Нормальная работа, запросы проходят
    - open: Сервис недоступен, запросы блокируются
    - half_open: Тестовый режим после таймаута
    """
    
    def __init__(self, service_name, timeout=3, error_threshold=0.5, 
                 reset_timeout=10, min_requests=5, success_threshold=2):
        """
        :param service_name: Имя сервиса для логирования
        :param timeout: Таймаут запроса в секундах
        :param error_threshold: Порог ошибок (0.5 = 50%)
        :param reset_timeout: Время до попытки восстановления (секунды)
        :param min_requests: Минимум запросов для открытия
        :param success_threshold: Успешных запросов для закрытия в half-open
        """
        self.service_name = service_name
        self.timeout = timeout
        self.error_threshold = error_threshold
        self.reset_timeout = reset_timeout
        self.min_requests = min_requests
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.half_open_success = 0  # Счетчик успехов в half-open
        self.last_failure_time = None
        self.state = 'closed'
        self.lock = threading.Lock()
        
        # Метрики
        self.total_requests = 0
        self.total_failures = 0
        self.last_state_change = datetime.now()
    
    def call(self, func, *args, **kwargs):
        """
        Выполняет функцию через Circuit Breaker
        
        :param func: Функция для вызова
        :return: Результат функции
        :raises: Exception если circuit открыт или функция вызвала ошибку
        """
        with self.lock:
            self.total_requests += 1
            
            if self.state == 'open':
                # Проверяем, не пора ли попробовать снова
                if datetime.now() - self.last_failure_time > timedelta(seconds=self.reset_timeout):
                    self.state = 'half_open'
                    self.half_open_success = 0
                    self.last_state_change = datetime.now()
                    logger.info(
                        f'{self.service_name} circuit breaker: half-open',
                        service=self.service_name,
                        state_duration=(datetime.now() - self.last_state_change).total_seconds()
                    )
                else:
                    logger.warning(
                        f'{self.service_name} circuit breaker: open (blocking request)',
                        service=self.service_name,
                        remaining_time=(self.reset_timeout - (datetime.now() - self.last_failure_time).total_seconds())
                    )
                    raise Exception(f'Circuit breaker is open for {self.service_name}')
        
        # Выполняем запрос
        try:
            result = func(*args, **kwargs)
            
            # Успешный запрос
            with self.lock:
                self.success_count += 1
                
                if self.state == 'half_open':
                    self.half_open_success += 1
                    
                    # Если достаточно успешных запросов, закрываем circuit
                    if self.half_open_success >= self.success_threshold:
                        old_state = self.state
                        self.state = 'closed'
                        self.failure_count = 0
                        self.success_count = 0
                        self.last_state_change = datetime.now()
                        
                        logger.info(
                            f'{self.service_name} circuit breaker: closed',
                            service=self.service_name,
                            previous_state=old_state,
                            recovery_successes=self.half_open_success
                        )
            
            return result
            
        except Exception as e:
            # Запрос провалился
            with self.lock:
                self.failure_count += 1
                self.total_failures += 1
                self.last_failure_time = datetime.now()
                
                if self.state == 'half_open':
                    # В half-open режиме любая ошибка снова открывает circuit
                    self.state = 'open'
                    self.last_state_change = datetime.now()
                    
                    logger.error(
                        f'{self.service_name} circuit breaker: reopened',
                        service=self.service_name,
                        exc_info=e
                    )
                    
                elif self.state == 'closed':
                    # Проверяем, нужно ли открыть circuit
                    total = self.failure_count + self.success_count
                    
                    if total >= self.min_requests:
                        error_rate = self.failure_count / total
                        
                        if error_rate >= self.error_threshold:
                            self.state = 'open'
                            self.last_state_change = datetime.now()
                            
                            logger.error(
                                f'{self.service_name} circuit breaker: opened',
                                service=self.service_name,
                                total_requests=total,
                                failure_count=self.failure_count,
                                error_rate=error_rate,
                                threshold=self.error_threshold
                            )
            
            raise e
    
    def get_stats(self):
        """
        Возвращает статистику Circuit Breaker
        """
        with self.lock:
            total = self.failure_count + self.success_count
            error_rate = (self.failure_count / total) if total > 0 else 0
            
            return {
                'service': self.service_name,
                'state': self.state,
                'total_requests': self.total_requests,
                'total_failures': self.total_failures,
                'window_requests': total,
                'window_failures': self.failure_count,
                'window_successes': self.success_count,
                'error_rate': error_rate,
                'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
                'last_state_change': self.last_state_change.isoformat()
            }
    
    def reset(self):
        """
        Принудительный сброс Circuit Breaker (для админа)
        """
        with self.lock:
            old_state = self.state
            self.state = 'closed'
            self.failure_count = 0
            self.success_count = 0
            self.half_open_success = 0
            self.last_state_change = datetime.now()
            
            logger.info(
                f'{self.service_name} circuit breaker: manually reset',
                service=self.service_name,
                previous_state=old_state
            )
