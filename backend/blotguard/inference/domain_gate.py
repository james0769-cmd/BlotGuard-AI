"""Conservative input-domain gate for Western Blot analysis.

The authenticity detector is binary and must never be used as an image-type
classifier.  This inexpensive gate rejects clearly out-of-domain inputs before
they can receive a misleading ``original`` or ``generated`` prediction.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps, ImageStat


@dataclass(frozen=True)
class DomainAssessment:
    accepted: bool
    label: str
    message: str


class WesternBlotDomainGate:
    """Reject obvious photographs, illustrations, screenshots, and blank art.

    Thresholds are intentionally conservative and were checked against the
    repository's real and generated Western Blot regression samples.  This is
    an input-safety gate, not a trained biological image classifier.
    """

    MAX_MEAN_CHANNEL_RANGE = 0.075
    MAX_EDGE_DENSITY = 0.075
    MIN_GRAYSCALE_STDDEV = 0.012

    def assess(self, image_path: str | Path) -> DomainAssessment:
        with Image.open(image_path) as image:
            rgb = image.convert("RGB")
            rgb.thumbnail((512, 512))
            width, height = rgb.size
            pixel_count = max(1, width * height)

            # Mean channel range is stable for dark tinted blot images, unlike
            # HSV saturation, which can become large near black.
            pixels = list(rgb.get_flattened_data())
            colorfulness = sum(
                max(pixel) - min(pixel) for pixel in pixels
            ) / (255 * pixel_count)

            gray = ImageOps.grayscale(rgb)
            grayscale_stddev = ImageStat.Stat(gray).stddev[0] / 255
            edge_histogram = gray.filter(ImageFilter.FIND_EDGES).histogram()
            edge_density = sum(edge_histogram[60:]) / pixel_count

        if colorfulness > self.MAX_MEAN_CHANNEL_RANGE:
            return self._rejected("图像色彩特征明显偏离 Western Blot 图像")
        if edge_density > self.MAX_EDGE_DENSITY:
            return self._rejected("图像包含大量文字或高密度锐利边缘")
        if grayscale_stddev < self.MIN_GRAYSCALE_STDDEV:
            return self._rejected("图像信息量过低，未检测到可分析的条带结构")
        return DomainAssessment(
            accepted=True,
            label="western_blot",
            message="输入通过 Western Blot 图像域预检",
        )

    @staticmethod
    def _rejected(reason: str) -> DomainAssessment:
        return DomainAssessment(
            accepted=False,
            label="non_western_blot",
            message=f"{reason}，因此未执行真伪风险分析。",
        )
