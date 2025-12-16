import threading
import time
from pathlib import Path
from typing import Optional, Callable
from queue import Queue

from src.rag.config import DOCUMENTS_DIR, AUTO_BACKGROUND_INGEST
from src.rag.logger import logger
from src.rag.ingest import ingest_from_directory


class DocumentWatcher:
    """Фоновый worker для отслеживания и обновления документов."""
    
    def __init__(self, watch_dir: Optional[Path] = None, check_interval: int = 30):
        self.watch_dir = watch_dir or DOCUMENTS_DIR
        self.check_interval = check_interval
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.last_check = {}
        self.callback: Optional[Callable] = None
        
    def set_callback(self, callback: Callable):
        """Устанавливает callback для уведомления об обновлениях."""
        self.callback = callback
        
    def start(self):
        """Запускает фоновый worker."""
        if self.running:
            logger.warning("Worker уже запущен")
            return
            
        if not AUTO_BACKGROUND_INGEST:
            logger.info("Фоновое обновление отключено в конфиге")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        logger.info(f"DocumentWatcher запущен (интервал: {self.check_interval}с)")
        
    def stop(self):
        """Останавливает фоновый worker."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("DocumentWatcher остановлен")
        
    def _watch_loop(self):
        """Основной цикл отслеживания."""
        while self.running:
            try:
                self._check_for_updates()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Ошибка в DocumentWatcher: {str(e)}")
                time.sleep(self.check_interval)
                
    def _check_for_updates(self):
        """Проверяет наличие новых или изменённых файлов."""
        if not self.watch_dir.exists():
            return
            
        current_files = {}
        for file_format in [".pdf", ".txt", ".md"]:
            for file_path in self.watch_dir.glob(f"*{file_format}"):
                try:
                    stat = file_path.stat()
                    current_files[str(file_path)] = stat.st_mtime
                except (OSError, IOError):
                    pass
        
        # Проверяем новые или изменённые файлы
        changes_detected = False
        for file_path, mtime in current_files.items():
            if file_path not in self.last_check or self.last_check[file_path] != mtime:
                changes_detected = True
                logger.info(f"Обнаружено изменение: {Path(file_path).name}")
                self.last_check[file_path] = mtime
        
        # Проверяем удалённые файлы
        for file_path in list(self.last_check.keys()):
            if file_path not in current_files:
                logger.info(f"Файл удалён: {Path(file_path).name}")
                del self.last_check[file_path]
                changes_detected = True
        
        if changes_detected:
            try:
                logger.info("Запуск фонового обновления документов...")
                documents = ingest_from_directory(force_update=False)
                logger.info(f"Обновлено {len(documents)} документов")
                
                if self.callback:
                    self.callback(documents)
            except Exception as e:
                logger.error(f"Ошибка при фоновом обновлении: {str(e)}")


class TaskQueue:
    """Очередь задач для асинхронной обработки."""
    
    def __init__(self, num_workers: int = 2):
        self.queue = Queue()
        self.num_workers = num_workers
        self.workers = []
        self.running = False
        
    def start(self):
        """Запускает worker'ы."""
        self.running = True
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"TaskWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        logger.info(f"TaskQueue запущена с {self.num_workers} worker'ами")
        
    def stop(self):
        """Останавливает worker'ы."""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=5)
        logger.info("TaskQueue остановлена")
        
    def submit(self, task_func, *args, **kwargs):
        """Добавляет задачу в очередь."""
        self.queue.put((task_func, args, kwargs))
        
    def _worker_loop(self):
        """Основной цикл worker'а."""
        while self.running:
            try:
                task_func, args, kwargs = self.queue.get(timeout=1)
                try:
                    task_func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Ошибка при выполнении задачи: {str(e)}")
            except:
                pass


# Глобальные экземпляры
_watcher: Optional[DocumentWatcher] = None
_task_queue: Optional[TaskQueue] = None


def init_workers(watch_interval: int = 30, num_task_workers: int = 2):
    """Инициализирует и запускает all workers."""
    global _watcher, _task_queue
    
    try:
        _watcher = DocumentWatcher(check_interval=watch_interval)
        _watcher.start()
        
        _task_queue = TaskQueue(num_workers=num_task_workers)
        _task_queue.start()
        
        logger.info("Workers инициализированы")
    except Exception as e:
        logger.error(f"Ошибка при инициализации workers: {str(e)}")


def shutdown_workers():
    """Останавливает все workers."""
    global _watcher, _task_queue
    
    try:
        if _watcher:
            _watcher.stop()
        if _task_queue:
            _task_queue.stop()
        logger.info("Workers остановлены")
    except Exception as e:
        logger.error(f"Ошибка при остановке workers: {str(e)}")


def submit_background_task(task_func, *args, **kwargs):
    """Отправляет задачу в фоновую очередь."""
    if _task_queue:
        _task_queue.submit(task_func, *args, **kwargs)
    else:
        logger.warning("TaskQueue не инициализирована")


def set_watcher_callback(callback: Callable):
    """Устанавливает callback для watcher'а."""
    if _watcher:
        _watcher.set_callback(callback)
