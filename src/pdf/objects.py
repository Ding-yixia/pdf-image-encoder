"""PDF对象构造: Stream, Dictionary, Name等PDF基本元素的序列化"""
from typing import Optional


def encode_name(name: str) -> str:
    """编码PDF Name对象: /Name"""
    if not name.startswith('/'):
        name = '/' + name
    return name


def encode_string(text: str) -> str:
    """编码PDF字符串: (text)"""
    escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    return '(' + escaped + ')'


def encode_dict(entries: dict, indent: int = 0) -> str:
    """编码PDF Dictionary: << /Key value >>"""
    pad = '  ' * indent
    items = []
    for k, v in entries.items():
        key = encode_name(k) if not k.startswith('/') else k
        items.append(f'{pad}  {key} {v}')
    return '<<\n' + '\n'.join(items) + f'\n{pad}>>'


def encode_stream(data: bytes, extra: Optional[dict] = None) -> tuple[str, bytes]:
    """
    构造PDF流对象。

    返回: (字典声明字符串, 编码后数据)
    """
    # 直接使用原始数据, 外部已确定Filter
    return data


def make_stream_object(obj_num: int, data: bytes, dictionary: dict) -> str:
    """构造 PDF "N 0 obj <<...>> stream ... endstream endobj" """
    lines = [f'{obj_num} 0 obj']
    lines.append(encode_dict(dictionary))
    lines.append('stream')
    # stream数据后直接跟endstream, 数据行单独处理
    dict_part = '\n'.join(lines)
    return dict_part, data


class PdfObject:
    """PDF间接对象"""

    def __init__(self, obj_num: int, content: str):
        self.obj_num = obj_num
        self.content = content

    def serialize(self) -> bytes:
        return f'{self.obj_num} 0 obj\n{self.content}\nendobj\n'.encode('latin-1')


class PdfStream:
    """PDF流对象"""

    def __init__(self, obj_num: int, data: bytes, dictionary: dict):
        self.obj_num = obj_num
        self.data = data
        self.dictionary = dictionary

    def serialize(self) -> bytes:
        # 必须保证二进制数据中不包含 endstream/endobj 序列
        dict_str = encode_dict(self.dictionary)
        result = f'{self.obj_num} 0 obj\n{dict_str}\nstream\n'.encode('latin-1')
        result += self.data
        result += b'\nendstream\nendobj\n'
        return result

    @property
    def byte_size(self) -> int:
        return len(self.data)
