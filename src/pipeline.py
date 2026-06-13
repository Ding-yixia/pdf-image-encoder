"""流程编排模块: 串联图像加载→预处理→编码→PDF生成→验证"""
import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.image_loader import scan_images
from src.image_preprocessor import ImagePreprocessor
from src.encoders import get_encoder
from src.pdf.builder import PdfBuilder, PdfBuildResult

log = logging.getLogger(__name__)


@dataclass
class EncoderResult:
    """单个编码结果"""
    image_name: str
    encoder_name: str
    raw_size: int
    pdf_size: int
    pdf_path: Path
    build_method: str
    success: bool
    error: str = ''


@dataclass
class PipelineResult:
    """流程执行结果"""
    summary: str
    total_pdfs: int
    success_count: int
    fail_count: int
    total_original_bytes: int
    total_pdf_bytes: int
    output_dir: Path
    report_path: Path
    encoder_results: list[EncoderResult] = field(default_factory=list)


class ProcessingPipeline:
    """处理流程编排"""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        encoders: list[str],
        image_count: int = 3,
        max_size: int = 300,
        jpeg_quality: int = 85,
        verbose: bool = False,
    ):
        self.input_dir = input_dir
        self.output_dir = Path(output_dir)
        self.encoders = encoders
        self.image_count = image_count
        self.max_size = max_size
        self.jpeg_quality = jpeg_quality
        self.verbose = verbose

        # 设置日志级别
        log.setLevel(logging.DEBUG if verbose else logging.INFO)

        # 子模块
        self.preprocessor = ImagePreprocessor(max_size, jpeg_quality)
        self.pdf_builder = PdfBuilder(self.output_dir / 'pdfs')

    def run(self) -> PipelineResult:
        """执行完整的处理流程"""
        log.info(f'{"="*60}')
        log.info(f'PDF Image Encoder — 处理流程')
        log.info(f'{"="*60}')
        log.info(f'输入:     {self.input_dir}')
        log.info(f'输出:     {self.output_dir}')
        log.info(f'编码器:   {", ".join(self.encoders)}')
        log.info(f'图像数:   {self.image_count}')
        log.info(f'最大尺寸: {self.max_size}px')
        log.info(f'JPEG质量: {self.jpeg_quality}')

        # Step 1: 扫描图像
        log.info(f'\n--- Step 1: 扫描图像 ---')
        images = scan_images(self.input_dir, self.image_count)
        if not images:
            return PipelineResult(
                summary='❌ 无输入图像',
                total_pdfs=0, success_count=0, fail_count=0,
                total_original_bytes=0, total_pdf_bytes=0,
                output_dir=self.output_dir,
                report_path=self.output_dir / 'report.txt',
            )

        # Step 2-4: 预处理 → 编码 → PDF生成
        log.info(f'\n--- Step 2-4: 编码+PDF生成 ---')
        results: list[EncoderResult] = []
        total_orig = 0
        total_pdf = 0

        for img_path in images:
            log.info(f'\n图像: {img_path.name}')

            try:
                # 预处理
                img = self.preprocessor.process(img_path)
                raw_rgb = img.tobytes()
                total_orig += len(raw_rgb)

                # 对每种编码器
                for enc_name in self.encoders:
                    log.info(f'  ├─ 编码: {enc_name}')

                    try:
                        # 编码
                        encoder = get_encoder(enc_name)
                        encoded_data, params = encoder.encode(img)

                        # 验证
                        if hasattr(encoder, 'verify') and encoder.verify:
                            pass  # LZW自带验证

                        # PDF生成
                        build_result = self.pdf_builder.build(
                            image_data=encoded_data,
                            params=params,
                            image_name=img_path.stem[:25],
                            encoder_name=enc_name,
                        )

                        total_pdf += build_result.size_bytes
                        results.append(EncoderResult(
                            image_name=img_path.name,
                            encoder_name=enc_name,
                            raw_size=len(raw_rgb),
                            pdf_size=build_result.size_bytes,
                            pdf_path=build_result.path,
                            build_method=build_result.method,
                            success=True,
                        ))
                        ratio = build_result.size_bytes / len(raw_rgb) * 100
                        log.info(f'    ✅ PDF: {build_result.path.name} '
                                 f'({build_result.size_bytes:,} bytes, {ratio:.1f}%) '
                                 f'[{build_result.method}]')

                    except Exception as e:
                        log.error(f'    ❌ 编码{enc_name}失败: {e}')
                        results.append(EncoderResult(
                            image_name=img_path.name,
                            encoder_name=enc_name,
                            raw_size=len(raw_rgb),
                            pdf_size=0,
                            pdf_path=Path(),
                            build_method='',
                            success=False,
                            error=str(e),
                        ))

            except Exception as e:
                log.error(f'  ❌ 预处理失败: {e}')

        # Step 5: 报告
        log.info(f'\n--- Step 5: 生成报告 ---')
        report_path = self._generate_report(results, total_orig, total_pdf)

        success = sum(1 for r in results if r.success)
        fail = sum(1 for r in results if not r.success)

        return PipelineResult(
            summary='✅ 全部成功' if fail == 0 else f'⚠️ {fail}个失败',
            total_pdfs=len(results),
            success_count=success,
            fail_count=fail,
            total_original_bytes=total_orig,
            total_pdf_bytes=total_pdf,
            output_dir=self.output_dir.absolute(),
            report_path=report_path,
            encoder_results=results,
        )

    def _generate_report(
        self, results: list[EncoderResult], total_orig: int, total_pdf: int
    ) -> Path:
        """生成处理报告"""
        from datetime import datetime

        lines = []
        lines.append('=' * 70)
        lines.append('PDF Image Encoder — 处理报告')
        lines.append('=' * 70)
        lines.append(f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        lines.append(f'输入目录: {self.input_dir}')
        lines.append(f'输出目录: {self.output_dir.absolute()}')
        lines.append(f'编码器:   {", ".join(self.encoders)}')
        lines.append('')
        lines.append(f'{"文件":<30s} {"编码器":<8s} {"原始RGB":>10s} {"PDF大小":>10s} '
                     f'{"压缩率":>8s} {"方式":<10s} {"状态"}')
        lines.append('-' * 85)
        for r in results:
            ratio = r.pdf_size / r.raw_size * 100 if r.raw_size > 0 else 0
            status = '✅' if r.success else '❌'
            lines.append(
                f'{r.image_name:<30s} {r.encoder_name:<8s} '
                f'{r.raw_size:>10,d} {r.pdf_size:>10,d} '
                f'{ratio:>7.1f}% {r.build_method:<10s} {status}'
            )
        lines.append('-' * 85)
        lines.append(f'{"总计":<40s} {total_orig:>10,d} {total_pdf:>10,d} '
                     f'{total_pdf/total_orig*100 if total_orig>0 else 0:>7.1f}%')
        lines.append('')
        lines.append('生成的文件:')
        for r in results:
            if r.success:
                lines.append(f'  {r.pdf_path.name} ({r.pdf_path.stat().st_size:,} bytes)')
        lines.append('')
        lines.append(f'成功/总数: {sum(1 for r in results if r.success)}/{len(results)}')
        lines.append('=' * 70)

        report_path = self.output_dir / 'report.txt'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text('\n'.join(lines), encoding='utf-8')
        log.info(f'报告已保存: {report_path}')
        return report_path
