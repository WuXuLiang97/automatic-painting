import os
from configparser import ConfigParser
from dataclasses import dataclass
from typing import Optional

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
            print(f"读取配置文件失败: {e}, 将使用默认配置")
    else:
        print("未找到工具人.ini，使用默认配置")
    return parser


def _to_bool(v: str):
    return str(v).lower() in ('1', 'true', 'yes', 'on')


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
settings = Settings(
    host=_parser.get('SERVER', 'host', fallback=_DEFAULTS['SERVER']['host']),
    port=_parser.getint('SERVER', 'port', fallback=int(_DEFAULTS['SERVER']['port'])),
    max_workers=_parser.getint('RUNTIME', 'max_workers', fallback=int(_DEFAULTS['RUNTIME']['max_workers'])),
    task_queue_size=_parser.getint('RUNTIME', 'task_queue_size', fallback=int(_DEFAULTS['RUNTIME']['task_queue_size'])),
    per_thread_models=_to_bool(_parser.get('RUNTIME', 'per_thread_models', fallback=_DEFAULTS['RUNTIME']['per_thread_models'])),
    model_warmup=_to_bool(_parser.get('MODEL', 'warmup', fallback=_DEFAULTS['MODEL']['warmup'])),
    enable_mkldnn=_to_bool(_parser.get('MODEL', 'enable_mkldnn', fallback=_DEFAULTS['MODEL']['enable_mkldnn'])),
    omp_threads=_parser.getint('RUNTIME', 'omp_threads', fallback=None) if _parser.get('RUNTIME', 'omp_threads', fallback='').isdigit() else None,
    mkl_threads=_parser.getint('RUNTIME', 'mkl_threads', fallback=None) if _parser.get('RUNTIME', 'mkl_threads', fallback='').isdigit() else None,
)

# 立即设置环境变量（如未在外部显式设置）
if settings.omp_threads is not None and 'OMP_NUM_THREADS' not in os.environ:
    os.environ['OMP_NUM_THREADS'] = str(settings.omp_threads)
if settings.mkl_threads is not None and 'MKL_NUM_THREADS' not in os.environ:
    os.environ['MKL_NUM_THREADS'] = str(settings.mkl_threads)
