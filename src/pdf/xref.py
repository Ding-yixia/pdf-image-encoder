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

    def serialize(self) -> str:
        """序列化xref表"""
        lines = ['xref', f'0 {self.size}']
        # entry 0: free
        lines.append(f'{"0":0>10} {"65535":5} f')
        # entries 1..N: in-use
        for offset in self.entries[1:]:
            lines.append(f'{offset:0>10} {"00000":5} n')
        return '\n'.join(lines)


def make_trailer(size: int, root_obj: int) -> str:
    """构造PDF trailer"""
    return f'trailer\n<< /Size {size} /Root {root_obj} 0 R >>'
