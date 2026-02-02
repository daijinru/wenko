"""统一日志配置模块

提供按日期切割的文件日志和控制台双通道输出。
日志文件命名格式：workflow.YYYY-MM-DD.log
"""

import glob
import logging
import os
from datetime import datetime, timedelta
from logging.handlers import WatchedFileHandler
from pathlib import Path

# 日志保留天数
LOG_RETENTION_DAYS = 7

# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 日志目录路径（workflow 目录下的 logs/）
_workflow_dir = Path(__file__).parent
LOG_DIR = _workflow_dir / "logs"

_initialized = False


def _get_log_filename() -> Path:
    """获取当前日期的日志文件名"""
    today = datetime.now().strftime("%Y-%m-%d")
    return LOG_DIR / f"workflow.{today}.log"


def _cleanup_old_logs() -> None:
    """清理过期的日志文件"""
    cutoff_date = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    pattern = str(LOG_DIR / "workflow.*.log")

    for log_file in glob.glob(pattern):
        try:
            # 从文件名提取日期
            filename = os.path.basename(log_file)
            # workflow.2026-02-01.log -> 2026-02-01
            date_str = filename.replace("workflow.", "").replace(".log", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")

            if file_date < cutoff_date:
                os.remove(log_file)
        except (ValueError, OSError):
            # 忽略无法解析或删除的文件
            pass


def setup_logging(level: int = logging.INFO) -> None:
    """初始化日志配置

    配置 root logger 使用文件和控制台双通道输出。
    文件日志按日期命名，保留 LOG_RETENTION_DAYS 天。

    Args:
        level: 日志级别，默认 INFO
    """
    global _initialized
    if _initialized:
        return

    # 确保日志目录存在
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 清理过期日志
    _cleanup_old_logs()

    # 获取当前日期的日志文件路径
    log_file = _get_log_filename()

    # 创建 formatter
    formatter = logging.Formatter(LOG_FORMAT)

    # 创建文件 handler（使用 WatchedFileHandler 支持文件变化）
    file_handler = WatchedFileHandler(
        filename=str(log_file),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # 创建控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # 配置 root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除现有 handlers 避免重复
    root_logger.handlers.clear()

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    _initialized = True

    # 记录初始化日志
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger

    Args:
        name: logger 名称，通常使用 __name__

    Returns:
        配置好的 Logger 实例
    """
    if not _initialized:
        setup_logging()
    return logging.getLogger(name)
