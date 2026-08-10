"""PDF report generation from persisted analysis results."""

from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.blotguard.core.config import RuntimeConfig
from backend.blotguard.domain.risk import RISK_LEVEL_LABELS, risk_level_for_score
from .storage import LocalStorage


class ReportService:
    def __init__(self, config: RuntimeConfig, storage: LocalStorage):
        self.config = config
        self.storage = storage
        self.font_name = "BlotGuardCJK"
        if self.font_name not in pdfmetrics.getRegisteredFontNames():
            font_path = self._find_cjk_font()
            pdfmetrics.registerFont(
                TTFont(self.font_name, str(font_path), subfontIndex=0)
            )

    def generate(self, task: dict) -> str:
        task_id = task["task_id"]
        destination = self.storage.task_dir(task_id) / "reports" / "report.pdf"
        styles = getSampleStyleSheet()
        body = ParagraphStyle(
            "ChineseBody",
            parent=styles["BodyText"],
            fontName=self.font_name,
            fontSize=9,
            leading=14,
        )
        title = ParagraphStyle(
            "ChineseTitle",
            parent=styles["Title"],
            fontName=self.font_name,
            fontSize=18,
            leading=24,
            alignment=TA_CENTER,
        )
        heading = ParagraphStyle(
            "ChineseHeading",
            parent=styles["Heading2"],
            fontName=self.font_name,
            fontSize=12,
            leading=18,
        )

        document = SimpleDocTemplate(
            str(destination),
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=self.config.report_title,
        )
        story = [
            Paragraph(self.config.report_title, title),
            Spacer(1, 6 * mm),
            Paragraph("检测任务信息", heading),
            self._task_table(task, body),
            Spacer(1, 5 * mm),
            Paragraph(
                "说明：本报告输出为模型风险判断，仅供科研诚信审查和人工复核参考，"
                "不能单独作为认定学术不端的依据。",
                body,
            ),
            Spacer(1, 3 * mm),
            Paragraph(
                "五级风险为实验性结果；当前模型对 DDPM/Pix2Pix 的区分能力仍待改进。",
                body,
            ),
        ]
        if (task.get("model") or {}).get("is_mock"):
            story.extend(
                [
                    Spacer(1, 3 * mm),
                    Paragraph(
                        "警告：本报告使用开发 mock 推理生成，不具备任何检测效力。",
                        body,
                    ),
                ]
            )
        story.extend(
            [
                Spacer(1, 5 * mm),
                Paragraph("检测结果汇总", heading),
                self._summary_table(task, body),
            ]
        )

        for position, item in enumerate(task["items"], start=1):
            story.extend(
                [
                    PageBreak(),
                    Paragraph(f"图像 {position}", heading),
                    self._item_table(item, body),
                    Spacer(1, 4 * mm),
                ]
            )
            image_path = self.storage.absolute(item["image_path"])
            story.append(self._scaled_image(image_path))

        document.build(
            story,
            onFirstPage=self._footer,
            onLaterPages=self._footer,
        )
        return self.storage.relative(destination)

    def _task_table(self, task: dict, style: ParagraphStyle) -> Table:
        model = task.get("model") or {}
        rows = [
            ["任务编号", task["task_id"]],
            ["原始文件", task["input"]["filename"]],
            ["文件 SHA-256", task["input"]["sha256"]],
            ["模型版本", model.get("version", "未记录")],
            ["权重 SHA-256", model.get("weight_sha256", "未记录")],
            ["判定阈值", str(model.get("threshold", "未记录"))],
            ["生成时间", task.get("completed_at") or task.get("updated_at")],
        ]
        return self._table(rows, style, [34 * mm, 125 * mm])

    def _summary_table(self, task: dict, style: ParagraphStyle) -> Table:
        summary = task["summary"]
        score = summary.get("score_generated")
        risk_level = summary.get("risk_level")
        rows = [
            ["图片总数", "疑似 AI 生成", "疑似真实", "分析失败"],
            [
                str(summary["total"]),
                str(summary["generated"]),
                str(summary["original"]),
                str(summary["failed"]),
            ],
            [
                "文件级判断",
                (
                    "疑似 AI 生成"
                    if summary.get("prediction") == "generated"
                    else "疑似真实"
                    if summary.get("prediction") == "original"
                    else "无有效结果"
                ),
                "最高风险分数",
                f"{score:.4f}" if score is not None else "-",
            ],
            [
                "五级风险（实验性）",
                RISK_LEVEL_LABELS.get(risk_level, "-"),
                "风险分层版本",
                summary.get("risk_level_version", "-"),
            ],
        ]
        return self._table(rows, style, [40 * mm] * 4, header=True)

    def _item_table(self, item: dict, style: ParagraphStyle) -> Table:
        score = item.get("score_generated")
        risk_level = risk_level_for_score(score)
        rows = [
            ["来源", item["source_name"]],
            ["页码", str(item.get("page_number") or "-")],
            ["尺寸", f'{item["width"]} x {item["height"]}'],
            ["图片 SHA-256", item["sha256"]],
            [
                "判定",
                (
                    "疑似 AI 生成"
                    if item.get("prediction") == "generated"
                    else "疑似真实"
                    if item.get("prediction") == "original"
                    else "分析失败"
                ),
            ],
            [
                "AI 生成风险分数",
                f"{score:.4f}" if score is not None else "-",
            ],
            [
                "五级风险（实验性）",
                RISK_LEVEL_LABELS.get(risk_level, "-"),
            ],
        ]
        return self._table(rows, style, [42 * mm, 117 * mm])

    @staticmethod
    def _table(
        rows: list[list[str]],
        style: ParagraphStyle,
        widths: list[float],
        header: bool = False,
    ) -> Table:
        wrapped = [
            [Paragraph(str(cell), style) for cell in row] for row in rows
        ]
        table = Table(wrapped, colWidths=widths, repeatRows=1 if header else 0)
        commands = [
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C0C8")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2F5")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        if header:
            commands.extend(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE6EC")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ]
            )
        table.setStyle(TableStyle(commands))
        return table

    @staticmethod
    def _scaled_image(path: Path) -> Image:
        image = Image(str(path))
        max_width = 159 * mm
        max_height = 175 * mm
        scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
        image.drawWidth = image.imageWidth * scale
        image.drawHeight = image.imageHeight * scale
        return image

    def _footer(self, canvas, document) -> None:
        canvas.saveState()
        canvas.setFont(self.font_name, 8)
        canvas.setFillColor(colors.HexColor("#66727D"))
        canvas.drawCentredString(
            A4[0] / 2,
            9 * mm,
            f"BlotGuard-AI  |  第 {document.page} 页",
        )
        canvas.restoreState()

    def _find_cjk_font(self) -> Path:
        configured = os.environ.get("BLOTGUARD_REPORT_FONT")
        candidates = [
            configured,
            self.config.project_root
            / "assets"
            / "fonts"
            / "NotoSansSC-Regular.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                return Path(candidate)
        raise RuntimeError(
            "No CJK report font found. Set BLOTGUARD_REPORT_FONT to a "
            "TTF, OTF, or TTC font path."
        )
