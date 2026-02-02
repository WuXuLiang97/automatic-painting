import os
from configparser import ConfigParser
from dataclasses import dataclass, replace
from typing import Optional
from .logger import get_logger

logger = get_logger('config_manager')

# 默认配置
_DEFAULTS = {
    'SERVER': {
        'host': '0.0.0.0',
        'port': '12345'
    },
    'RUNTIME': {
        'max_workers': '4',
        'task_queue_size': '50',
        'per_thread_models': 'true',  # 是否每线程独立模型
        'omp_threads': '',
        'mkl_threads': ''
    },
    'MODEL': {
        'warmup': 'true',
        'enable_mkldnn': 'true'
    }
}

CONFIG_FILE_NAME = '工具人.ini'


def _locate_ini():
    base_dir = os.path.dirname(os.path.dirname(__file__))  # service 目录
    candidates = [
        os.path.join(base_dir, CONFIG_FILE_NAME),  # service/工具人.ini
        os.path.join(os.getcwd(), CONFIG_FILE_NAME),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _load_config():
    parser = ConfigParser()
    # 先填充默认值
    for section, kv in _DEFAULTS.items():
        if not parser.has_section(section):
            parser.add_section(section)
        for k, v in kv.items():
            parser.set(section, k, v)

    ini_path = _locate_ini()
    if ini_path:
        try:
            parser.read(ini_path, encoding='utf-8')
        except Exception as e:
            logger.warning(f"读取配置文件失败: {e}, 将使用默认配置", exc_info=True)
    else:
        logger.info("未找到工具人.ini，使用默认配置")
    return parser


def _to_bool(v: str):
    return str(v).lower() in ('1', 'true', 'yes', 'on')


def _validate_config(parser: ConfigParser) -> list:
    """
    验证配置值的有效性
    
    Args:
        parser: 配置解析器
    
    Returns:
        错误列表，如果为空则表示配置有效
    """
    errors = []
    
    # 验证端口号
    try:
        port = parser.getint('SERVER', 'port', fallback=int(_DEFAULTS['SERVER']['port']))
        if not (1 <= port <= 65535):
            errors.append(f"端口号必须在 1-65535 之间，当前值: {port}")
    except (ValueError, TypeError) as e:
        errors.append(f"端口号格式错误: {e}")
    
    # 验证最大工作线程数
    try:
        max_workers = parser.getint('RUNTIME', 'max_workers', fallback=int(_DEFAULTS['RUNTIME']['max_workers']))
        if max_workers < 1:
            errors.append(f"最大工作线程数必须 >= 1，当前值: {max_workers}")
        elif max_workers > 100:
            errors.append(f"最大工作线程数建议 <= 100，当前值: {max_workers}（过大可能影响性能）")
    except (ValueError, TypeError) as e:
        errors.append(f"最大工作线程数格式错误: {e}")
    
    # 验证任务队列大小
    try:
        task_queue_size = parser.getint('RUNTIME', 'task_queue_size', fallback=int(_DEFAULTS['RUNTIME']['task_queue_size']))
        if task_queue_size < 1:
            errors.append(f"任务队列大小必须 >= 1，当前值: {task_queue_size}")
    except (ValueError, TypeError) as e:
        errors.append(f"任务队列大小格式错误: {e}")
    
    # 验证 OMP 线程数（如果提供）
    omp_threads_str = parser.get('RUNTIME', 'omp_threads', fallback='')
    if omp_threads_str and omp_threads_str.strip():
        try:
            omp_threads = int(omp_threads_str)
            if omp_threads < 1:
                errors.append(f"OMP 线程数必须 >= 1，当前值: {omp_threads}")
        except (ValueError, TypeError) as e:
            errors.append(f"OMP 线程数格式错误: {e}")
    
    # 验证 MKL 线程数（如果提供）
    mkl_threads_str = parser.get('RUNTIME', 'mkl_threads', fallback='')
    if mkl_threads_str and mkl_threads_str.strip():
        try:
            mkl_threads = int(mkl_threads_str)
            if mkl_threads < 1:
                errors.append(f"MKL 线程数必须 >= 1，当前值: {mkl_threads}")
        except (ValueError, TypeError) as e:
            errors.append(f"MKL 线程数格式错误: {e}")
    
    # 验证布尔值（通过尝试转换来验证）
    bool_keys = [
        ('RUNTIME', 'per_thread_models'),
        ('MODEL', 'warmup'),
        ('MODEL', 'enable_mkldnn'),
    ]
    for section, key in bool_keys:
        try:
            value = parser.get(section, key, fallback=_DEFAULTS.get(section, {}).get(key, 'true'))
            # 尝试转换为布尔值，如果失败会抛出异常
            _to_bool(value)
        except Exception as e:
            errors.append(f"配置项 [{section}]{key} 的布尔值格式错误: {value}，错误: {e}")
    
    return errors


@dataclass
class Settings:
    host: str
    port: int
    max_workers: int
    task_queue_size: int
    per_thread_models: bool
    model_warmup: bool
    enable_mkldnn: bool
    omp_threads: Optional[int]
    mkl_threads: Optional[int]


_parser = _load_config()

# 验证配置
_config_errors = _validate_config(_parser)
if _config_errors:
    error_msg = "配置验证失败，发现以下错误：\n" + "\n".join(f"  - {e}" for e in _config_errors)
    logger.error(error_msg)
    raise ValueError(error_msg)

# 创建配置对象
settings = Settings(
    host=_parser.get('SERVER', 'host', fallback=_DEFAULTS['SERVER']['host']),
    port=_parser.getint('SERVER', 'port', fallback=int(_DEFAULTS['SERVER']['port'])),
    max_workers=_parser.getint('RUNTIME', 'max_workers', fallback=int(_DEFAULTS['RUNTIME']['max_workers'])),
    task_queue_size=_parser.getint('RUNTIME', 'task_queue_size', fallback=int(_DEFAULTS['RUNTIME']['task_queue_size'])),
    per_thread_models=_to_bool(_parser.get('RUNTIME', 'per_thread_models', fallback=_DEFAULTS['RUNTIME']['per_thread_models'])),
    model_warmup=_to_bool(_parser.get('MODEL', 'warmup', fallback=_DEFAULTS['MODEL']['warmup'])),
    enable_mkldnn=_to_bool(_parser.get('MODEL', 'enable_mkldnn', fallback=_DEFAULTS['MODEL']['enable_mkldnn'])),
    omp_threads=_parser.getint('RUNTIME', 'omp_threads', fallback=None) if _parser.get('RUNTIME', 'omp_threads', fallback='').strip() and _parser.get('RUNTIME', 'omp_threads', fallback='').isdigit() else None,
    mkl_threads=_parser.getint('RUNTIME', 'mkl_threads', fallback=None) if _parser.get('RUNTIME', 'mkl_threads', fallback='').strip() and _parser.get('RUNTIME', 'mkl_threads', fallback='').isdigit() else None,
)

# 立即设置环境变量（如未在外部显式设置）
if settings.omp_threads is not None and 'OMP_NUM_THREADS' not in os.environ:
    os.environ['OMP_NUM_THREADS'] = str(settings.omp_threads)
if settings.mkl_threads is not None and 'MKL_NUM_THREADS' not in os.environ:
    os.environ['MKL_NUM_THREADS'] = str(settings.mkl_threads)


def reload_config() -> tuple[bool, Optional[str], Optional[Settings]]:
    """重新加载配置文件
    
    Returns:
        tuple[bool, Optional[str], Optional[Settings]]: 
            (是否成功, 错误消息, 新的配置对象)
            如果成功，返回 (True, None, new_settings)
            如果失败，返回 (False, error_message, None)
    """
    try:
        # 重新加载配置
        new_parser = _load_config()
        
        # 验证新配置
        errors = _validate_config(new_parser)
        if errors:
            error_msg = "配置验证失败：\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(f"配置重载失败: {error_msg}")
            return False, error_msg, None
        
        # 创建新的配置对象
        new_settings = Settings(
            host=new_parser.get('SERVER', 'host', fallback=_DEFAULTS['SERVER']['host']),
            port=new_parser.getint('SERVER', 'port', fallback=int(_DEFAULTS['SERVER']['port'])),
            max_workers=new_parser.getint('RUNTIME', 'max_workers', fallback=int(_DEFAULTS['RUNTIME']['max_workers'])),
            task_queue_size=new_parser.getint('RUNTIME', 'task_queue_size', fallback=int(_DEFAULTS['RUNTIME']['task_queue_size'])),
            per_thread_models=_to_bool(new_parser.get('RUNTIME', 'per_thread_models', fallback=_DEFAULTS['RUNTIME']['per_thread_models'])),
            model_warmup=_to_bool(new_parser.get('MODEL', 'warmup', fallback=_DEFAULTS['MODEL']['warmup'])),
            enable_mkldnn=_to_bool(new_parser.get('MODEL', 'enable_mkldnn', fallback=_DEFAULTS['MODEL']['enable_mkldnn'])),
            omp_threads=new_parser.getint('RUNTIME', 'omp_threads', fallback=None) if new_parser.get('RUNTIME', 'omp_threads', fallback='').strip() and new_parser.get('RUNTIME', 'omp_threads', fallback='').isdigit() else None,
            mkl_threads=new_parser.getint('RUNTIME', 'mkl_threads', fallback=None) if new_parser.get('RUNTIME', 'mkl_threads', fallback='').strip() and new_parser.get('RUNTIME', 'mkl_threads', fallback='').isdigit() else None,
        )
        
        # 更新环境变量（如果需要）
        if new_settings.omp_threads is not None:
            os.environ['OMP_NUM_THREADS'] = str(new_settings.omp_threads)
        if new_settings.mkl_threads is not None:
            os.environ['MKL_NUM_THREADS'] = str(new_settings.mkl_threads)
        
        logger.info("配置重载成功")
        return True, None, new_settings
        
    except Exception as e:
        error_msg = f"配置重载异常: {e}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, None
