"""配置管理模块"""
import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """全局配置"""
    input_dir: Path = Path(r'D:\wallpapers')
    output_dir: Path = Path('output')
    encoders: list[str] = field(default_factory=lambda: ['LZW', 'DCT', 'Flate',
                                                         'JPX', 'CCITT', 'RLE'])
    image_count: int = 3
    max_size: int = 300
    jpeg_quality: int = 85
    verbose: bool = False

    @classmethod
    def from_yaml(cls, path: Optional[Path] = None) -> 'Config':
        if path is None:
            path = Path(__file__).parent.parent / 'config' / 'default.yaml'
        if not path.exists():
            return cls()
        with open(path, encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})

    def to_yaml(self, path: Path):
        data = {k: str(v) if isinstance(v, Path) else v
                for k, v in self.__dict__.items()}
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
