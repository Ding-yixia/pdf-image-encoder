# PDF Image Encoder — 缺陷修复文档

## 修复概览

| 编号 | 严重性 | 文件 | 缺陷描述 |
|------|--------|------|----------|
| BUG-001 | 严重 | src/pdf/builder.py | 手动构建PDF时，页面字典被错误地序列化为Stream对象 |
| BUG-002 | 严重 | src/pdf/builder.py | 手动构建PDF时，SMask对象编号错误导致整个PDF结构损坏 |
| BUG-003 | 次要 | src/pdf/xref.py | XRef表格条目格式不符合PDF规范（非20字节） |
| BUG-004 | 次要 | src/pdf/builder.py | 直接访问params.smask缺少安全保护 |
| BUG-005 | 次要 | src/main.py | Windows终端GBK编码导致emoji输出崩溃 |

---

## BUG-001: 页面字典被错误序列化为Stream对象

**严重性**: 严重 — 导致所有手动构建的PDF（Raw/LZW/RLE/Alpha编码）无法被PDF阅读器正确解析

**文件**: `src/pdf/builder.py` — `_build_manual()` 方法

**现象**:
手动构建的PDF在大多数PDF阅读器中无法正常打开或显示空白页面。

**根因**:
PDF规范中，页面对象（`/Type /Page`）必须是字典（Dictionary），而非流（Stream）。原代码使用 `PdfStream` 将页面字典序列化为带有 `stream...endstream` 标记的流对象，并附加了 `/Filter /FlateDecode` 压缩。这违反了PDF规范，导致阅读器无法识别页面结构。

**原代码**:
```python
# --- obj 4(或3): 页面字典 (Flate压缩) ---
obj_n = OBJ_PAGE + smask_extra
page_dict_raw = (
    f'<< /Type /Page /Parent {OBJ_PAGES + smask_extra} 0 R'
    f' /MediaBox [0 0 612 792]'
    f' /Contents {OBJ_CONTENT + smask_extra} 0 R'
    f' /Resources << /XObject << /Im0 {OBJ_IMG} 0 R >> >>'
    f' >>'
)
page_comp = zlib.compress(page_dict_raw.encode('latin-1'))
xref.add_entry(len(pdf_bytes))
page_stream = PdfStream(obj_n, page_comp,
                        {'/Length': len(page_comp), '/Filter': '/FlateDecode'})
pdf_bytes.extend(page_stream.serialize())
```

**修复后**:
```python
# --- 页面字典 (必须是普通字典, 不能是Stream) ---
page_dict_raw = (
    f'<< /Type /Page /Parent {OBJ_PAGES} 0 R'
    f' /MediaBox [0 0 612 792]'
    f' /Contents {OBJ_CONTENT} 0 R'
    f' /Resources << /XObject << /Im0 {OBJ_IMG} 0 R >> >>'
    f' >>'
)
xref.add_entry(len(pdf_bytes))
page_obj = PdfObject(OBJ_PAGE, page_dict_raw)
pdf_bytes.extend(page_obj.serialize())
```

**修复要点**:
- 将 `PdfStream` 替换为 `PdfObject`，生成标准PDF字典对象
- 移除对页面字典的 Flate 压缩（字典不需要stream包装）
- 添加 `PdfObject` 的导入声明

---

## BUG-002: SMask对象编号错误导致PDF结构损坏

**严重性**: 严重 — Alpha编码（带透明度）生成的PDF完全损坏，对象编号与XRef表错位

**文件**: `src/pdf/builder.py` — `_build_manual()` 方法

**现象**:
Alpha编码器生成的PDF无法打开，SMask（透明度蒙版）对象在PDF中不可达。

**根因**:
原代码定义了固定的对象编号常量：
```python
OBJ_IMG = 1       # 图像XObject
OBJ_CONTENT = 2   # 页面内容流
OBJ_PAGE = 3      # 页面字典
OBJ_PAGES = 4     # 页面树
OBJ_CATALOG = 5   # Catalog
OBJ_SMASK = 6     # SMask (可选)
```

当SMask存在时，代码意图将SMask插入为第2个对象（obj 2），后续对象顺延。但实际存在三个错误：

1. **SMask对象编号错误**: `OBJ_SMASK` 固定为6，但SMask实际写入xref第2个位置（对应obj 2）。PDF阅读器查找obj 6时，会找到Catalog的偏移量，读取到错误的对象内容。
2. **内容流编号未偏移**: 内容流使用 `OBJ_CONTENT + smask_extra` 计算 `obj_n`，但 `PdfStream` 构造时仍传入 `obj_n`，导致对象编号为2（与SMask冲突）。
3. **所有引用链断裂**: XRef表的6个条目对应obj 1-6，但实际写入的对象编号为 1, 6, 2, 3, 4, 5，全部错位。

**原代码** (对象编号分配):
```python
OBJ_IMG = 1
OBJ_CONTENT = 2
OBJ_PAGE = 3
OBJ_PAGES = 4
OBJ_CATALOG = 5
OBJ_SMASK = 6          # 错误: 应为2
OBJ_COUNT = 7 if smask_data else 6
```

**修复后**:
```python
# SMask存在时插入为obj 2, 后续对象顺延
OBJ_IMG = 1
OBJ_SMASK = 2 if smask_data else None
OBJ_CONTENT = 3 if smask_data else 2
OBJ_PAGE = 4 if smask_data else 3
OBJ_PAGES = 5 if smask_data else 4
OBJ_CATALOG = 6 if smask_data else 5
```

**修复要点**:
- 对象编号根据SMask是否存在动态计算，确保编号与写入顺序一致
- 移除了容易出错的 `smask_extra` 偏移量机制，改为直接赋值
- 移除了未使用的 `OBJ_COUNT` 常量
- 同步更新了所有对象写入和引用代码，使用新的OBJ_*常量

---

## BUG-003: XRef表格条目格式不符合PDF规范

**严重性**: 次要 — 多数PDF阅读器能容忍此问题，但严格校验器会报告错误

**文件**: `src/pdf/xref.py` — `XRefTable.serialize()` 方法

**现象**:
生成的PDF在严格PDF校验器中被标记为xref格式错误。

**根因**:
PDF规范（ISO 32000-1:2008 §7.5.4）要求每个xref条目恰好20字节（含行结束符）：
```
nnnnnnnnnn ggggg n \n   (10 + 1 + 5 + 1 + 1 + 1 + 1 = 20 bytes)
```

原代码使用 `'\n'.join()` 拼接，每条实际只有19字节（18字符 + 1个`\n`），缺少flag字符后的空格。

**原代码**:
```python
def serialize(self) -> str:
    lines = ['xref', f'0 {self.size}']
    lines.append(f'{"0":0>10} {"65535":5} f')
    for offset in self.entries[1:]:
        lines.append(f'{offset:0>10} {"00000":5} n')
    return '\n'.join(lines)
```

**修复后**:
```python
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
```

**修复要点**:
- 返回类型从 `str` 改为 `bytes`，避免编码歧义
- 每个条目格式为 `{offset:010d} {gen:05d} {flag} \n`，恰好20字节
- 同步更新 `builder.py` 中调用处，移除 `.encode('latin-1')` 调用

---

## BUG-004: params.smask 直接访问缺少安全保护

**严重性**: 次要 — 部分EncodeParams实例可能缺少smask属性，导致AttributeError

**文件**: `src/pdf/builder.py` — `_build_manual()` 方法

**现象**:
当传入的 `EncodeParams` 对象未显式设置 `smask` 属性时，直接访问 `params.smask` 会抛出 `AttributeError`。

**根因**:
`EncodeParams` 的 `smask` 字段默认值为 `None`，但通过 `params.smask` 直接访问时，如果dataclass字段未被正确初始化或使用了非标准构造方式，可能引发异常。相比之下，`_build_pikepdf()` 方法已使用了安全的 `params.__dict__.get('smask')` 访问方式，两处不一致。

**原代码**:
```python
smask_data = params.smask
```

**修复后**:
```python
smask_data = params.__dict__.get('smask')
```

**修复要点**:
- 与 `_build_pikepdf()` 保持一致的安全访问方式
- `dict.get()` 在键不存在时返回 `None`，不会抛出异常

---

## BUG-005: Windows终端GBK编码导致emoji输出崩溃

**严重性**: 次要 — 仅影响Windows中文系统的控制台输出

**文件**: `src/main.py` — `main()` 函数

**现象**:
在Windows中文系统上运行时，程序在完成所有PDF生成后，打印结果摘要时崩溃：
```
UnicodeEncodeError: 'gbk' codec can't encode character '\u26a0' in position 6: illegal multibyte sequence
```

**根因**:
Windows中文系统默认终端编码为GBK，无法编码程序中使用的emoji字符（✅ ❌ ⚠️）。Python的 `print()` 函数通过 `sys.stdout` 输出，而 `sys.stdout.encoding` 在Windows上默认为 `'gbk'`。

**修复后**:
```python
def main():
    # Windows 终端 GBK 编码无法输出 emoji，强制 UTF-8
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
```

**修复要点**:
- 仅在Windows平台 (`sys.platform == 'win32'`) 上修改编码
- 使用 `errors='replace'` 确保即使终端不完全支持UTF-8也不会崩溃
- 同时配置 `stdout` 和 `stderr`
