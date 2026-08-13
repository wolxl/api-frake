"""把 api_framework 加入 Python 搜索路径，解决导入问题"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
