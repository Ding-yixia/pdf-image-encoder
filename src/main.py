"""
PDF Image Encoder — 主入口

用法:
    python -m src.main --help
    python -m src.main                         # 默认处理 D:\wallpapers
    python -m src.main --input ./images
    python -m src.main --encoders LZW,DCT,Flate --count 3 --size 300
"""
import argparse
import sys
from pathlib import Path

from src.pipeline import ProcessingPipeline
from src.encoders import list_encoders


def main():
    parser = argparse.ArgumentParser(
        description='PDF Image Encoder: 将图像转为多种PDF编码格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            '示例:\n'
            '  %(prog)s\n'
            '  %(prog)s --input D:\\photos --output ./out\n'
            '  %(prog)s --encoders LZW,DCT,Flate --count 5 --size 400\n'
            '  %(prog)s --encoders all\n'
        ),
    )
    parser.add_argument('--input', '-i', default=r'D:\wallpapers',
                        help='源图像目录')
    parser.add_argument('--output', '-o', default='output',
                        help='输出目录')
    parser.add_argument('--encoders', '-e', default='all',
                        help=f'编码器列表(逗号分隔)或all, 可选: {",".join(list_encoders())}')
    parser.add_argument('--count', '-n', type=int, default=3,
                        help='处理的图像数量 (默认3)')
    parser.add_argument('--size', '-s', type=int, default=300,
                        help='图像最大尺寸px (默认300, 0=不缩放)')
    parser.add_argument('--quality', '-q', type=int, default=85,
                        help='JPEG质量 (默认85)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细日志')

    args = parser.parse_args()

    # 解析编码器列表
    if args.encoders == 'all':
        encoders = list_encoders()
    else:
        encoders = [e.strip() for e in args.encoders.split(',')]
        for e in encoders:
            if e not in list_encoders():
                parser.error(f'未知编码器: {e}, 可选: {list_encoders()}')

    # 运行流程
    pipeline = ProcessingPipeline(
        input_dir=Path(args.input),
        output_dir=Path(args.output),
        encoders=encoders,
        image_count=args.count,
        max_size=args.size if args.size > 0 else None,
        jpeg_quality=args.quality,
        verbose=args.verbose,
    )
    result = pipeline.run()

    # 输出摘要
    print(f'\n{"="*60}')
    print(f'处理完成: {result.summary}')
    print(f'{"="*60}')
    print(f'PDF总数:     {result.total_pdfs}')
    print(f'成功:        {result.success_count}')
    print(f'失败:        {result.fail_count}')
    print(f'总大小(原始): {result.total_original_bytes:,} bytes')
    print(f'总大小(PDF): {result.total_pdf_bytes:,} bytes')
    print(f'输出目录:    {result.output_dir}')
    print(f'详细报告:    {result.report_path}')
    print(f'{"="*60}')
    print('编码效率详情:')
    print(f'  {"编码器":<8s} {"原始RGB":>10s} {"PDF大小":>10s} {"压缩率":>8s} {"状态"}')
    print(f'  {"-"*44}')
    for r in result.encoder_results:
        ratio = r.pdf_size / r.raw_size * 100 if r.raw_size > 0 else 0
        status = '✅' if r.success else '❌'
        print(f'  {r.encoder_name:<8s} {r.raw_size:>10,d} {r.pdf_size:>10,d} '
              f'{ratio:>7.1f}% {status}')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
