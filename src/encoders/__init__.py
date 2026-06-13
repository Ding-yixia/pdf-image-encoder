"""__init__: 编码器注册表"""
from .base import Encoder, EncodeParams
from .raw import RawEncoder
from .flate import FlateEncoder
from .dct import DCTEncoder
from .jpx import JPXEncoder
from .ccitt import CCITTEncoder
from .rle import RLEEncoder
from .lzw import LZWEncoder

from .alpha import AlphaEncoder

from .jbig2 import JBIG2Encoder

REGISTRY: dict[str, type[Encoder]] = {
    'Raw':   RawEncoder,
    'Flate': FlateEncoder,
    'DCT':   DCTEncoder,
    'JPX':   JPXEncoder,
    'CCITT': CCITTEncoder,
    'RLE':   RLEEncoder,
    'LZW':   LZWEncoder,
    'Alpha': AlphaEncoder,
    'JBIG2': JBIG2Encoder,
}

def get_encoder(name: str) -> Encoder:
    if name not in REGISTRY:
        raise ValueError(f"Unknown encoder: {name}, choices: {list(REGISTRY)}")
    return REGISTRY[name]()

def list_encoders() -> list[str]:
    return list(REGISTRY)
