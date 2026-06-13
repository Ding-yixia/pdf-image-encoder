"""交叉引用表(XRef)和trailer构造"""

class XRefTable:
    """PDF交叉引用表"""

    def __init__(self):
        self.entries: list[int] = [0]  # entry 0 = free (offset=0)

    def add_entry(self, offset: int) -> int:
        """添加一个条目, 返回对象编号"""
        obj_num = len(self.entries)
        self.entries.append(offset)
        return obj_num

    @property
    def size(self) -> int:
        return len(self.entries)

    def serialize(self) -> bytes:
        """序列化xref表。每个条目恰好20字节(PDF规范§7.5.4)"""
        parts = []
        parts.append(b'xref\n')
        parts.append(f'0 {self.size}\n'.encode('ascii'))
        # entry 0: free (generation 65535)
        parts.append(b'0000000000 65535 f \n')
        # entries 1..N: in-use
        for offset in self.entries[1:]:
            parts.append(f'{offset:010d} 00000 n \n'.encode('ascii'))
        return b''.join(parts)


def make_trailer(size: int, root_obj: int) -> str:
    """构造PDF trailer"""
    return f'trailer\n<< /Size {size} /Root {root_obj} 0 R >>'
