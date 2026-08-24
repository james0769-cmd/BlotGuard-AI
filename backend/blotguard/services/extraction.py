"""Secure image extraction from supported uploads."""

from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
import zipfile

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError
from pypdf import PdfReader

from backend.blotguard.core.config import RuntimeConfig
from backend.blotguard.core.errors import AppError
from backend.blotguard.domain.contracts import ExtractedImage
from .storage import LocalStorage


class ExtractionService:
    IMAGE_EXTENSIONS = {"jpg", "jpeg", "jfif", "png", "tif", "tiff"}
    PDF_MAX_MEAN_SATURATION = 0.08
    PDF_MAX_EDGE_DENSITY = 0.08
    PDF_MIN_CANDIDATE_PIXELS = 128 * 128

    def __init__(self, config: RuntimeConfig, storage: LocalStorage):
        self.config = config
        self.storage = storage
        Image.MAX_IMAGE_PIXELS = config.max_image_pixels

    def validate_extension(self, filename: str) -> str:
        extension = Path(filename).suffix.lower().lstrip(".")
        if not extension:
            raise AppError(
                "MISSING_EXTENSION", "Uploaded file has no extension", 400
            )
        if extension not in self.config.allowed_extensions:
            raise AppError(
                "UNSUPPORTED_FILE_TYPE",
                f"File type '.{extension}' is not supported",
                415,
                {"allowed_extensions": list(self.config.allowed_extensions)},
            )
        return extension

    def validate_signature(self, path: Path, extension: str) -> None:
        with path.open("rb") as stream:
            header = stream.read(8)
        valid = (
            extension in {"jpg", "jpeg", "jfif"}
            and header.startswith(b"\xff\xd8\xff")
        ) or (
            extension == "png" and header.startswith(b"\x89PNG\r\n\x1a\n")
        ) or (
            extension in {"tif", "tiff"}
            and (
                header.startswith(b"II*\x00")
                or header.startswith(b"MM\x00*")
            )
        ) or (
            extension == "pdf" and header.startswith(b"%PDF-")
        ) or (
            extension == "docx" and header.startswith(b"PK")
        )
        if not valid:
            raise AppError(
                "FILE_SIGNATURE_MISMATCH",
                "File contents do not match the filename extension",
                415,
            )

    def extract(
        self,
        task_id: str,
        source_relative: str,
        extension: str,
        original_filename: str,
    ) -> list[ExtractedImage]:
        source = self.storage.absolute(source_relative)
        self.validate_signature(source, extension)
        output_dir = self.storage.task_dir(task_id) / "images"
        if extension in self.IMAGE_EXTENSIONS:
            images = [
                self._canonicalize_path(
                    source,
                    output_dir / "0001.png",
                    original_filename,
                    1,
                    None,
                )
            ]
        elif extension == "pdf":
            images = self._extract_pdf(source, output_dir)
        elif extension == "docx":
            images = self._extract_docx(source, output_dir)
        else:
            raise AppError(
                "UNSUPPORTED_FILE_TYPE",
                f"File type '.{extension}' is not supported",
                415,
            )

        if not images:
            if extension == "pdf":
                raise AppError(
                    "NO_WESTERN_BLOT_CANDIDATES",
                    "PDF 中未找到可可靠分析的 Western Blot 候选图像。"
                    "请裁剪目标条带区域后以 PNG/JPG 上传。",
                    422,
                )
            raise AppError(
                "NO_ANALYZABLE_IMAGES",
                "No analyzable raster images were found in the file",
                422,
            )
        if len(images) > self.config.max_images_per_file:
            raise AppError(
                "TOO_MANY_IMAGES",
                "The file contains too many images",
                422,
                {"max_images": self.config.max_images_per_file},
            )
        return images

    def _extract_pdf(
        self, source: Path, output_dir: Path
    ) -> list[ExtractedImage]:
        try:
            reader = PdfReader(str(source))
        except Exception as exc:
            raise AppError("INVALID_PDF", "Unable to parse PDF file", 422) from exc
        if reader.is_encrypted:
            raise AppError(
                "ENCRYPTED_PDF", "Encrypted PDF files are not supported", 422
            )

        results: list[ExtractedImage] = []
        index = 0
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                page_images = list(page.images)
            except Exception:
                page_images = []
            for embedded in page_images:
                index += 1
                if index > self.config.max_images_per_file:
                    raise AppError(
                        "TOO_MANY_IMAGES",
                        "The PDF contains too many images",
                        422,
                        {"max_images": self.config.max_images_per_file},
                    )
                try:
                    result = self._canonicalize_bytes(
                        embedded.data,
                        output_dir / f"{index:04d}.png",
                        f"page-{page_number}-{embedded.name}",
                        index,
                        page_number,
                    )
                except AppError as exc:
                    if exc.code in {"INVALID_IMAGE", "IMAGE_TOO_SMALL"}:
                        continue
                    raise
                image_path = self.storage.absolute(result.path)
                if not self._is_pdf_candidate(image_path):
                    image_path.unlink(missing_ok=True)
                    continue
                results.append(result)
        return results

    def _is_pdf_candidate(self, image_path: Path) -> bool:
        """Reject common PDF decorations before running the blot detector.

        The detector is trained on mostly grayscale Western Blot crops. PDF
        backgrounds, icons, logos, and line-art charts otherwise produce
        meaningless high scores because they are outside that input domain.
        This is deliberately a conservative candidate filter, not a claim
        that the remaining image is a Western Blot.
        """
        with Image.open(image_path) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            if width * height < self.PDF_MIN_CANDIDATE_PIXELS:
                return False

            saturation = ImageStat.Stat(
                rgb.convert("HSV").getchannel("S")
            ).mean[0] / 255
            if saturation > self.PDF_MAX_MEAN_SATURATION:
                return False

            gray = ImageOps.grayscale(rgb)
            edge_histogram = gray.filter(ImageFilter.FIND_EDGES).histogram()
            edge_density = sum(edge_histogram[60:]) / (width * height)
            return edge_density <= self.PDF_MAX_EDGE_DENSITY

    def _extract_docx(
        self, source: Path, output_dir: Path
    ) -> list[ExtractedImage]:
        try:
            archive = zipfile.ZipFile(source)
        except zipfile.BadZipFile as exc:
            raise AppError("INVALID_DOCX", "Unable to parse DOCX file", 422) from exc

        with archive:
            names = archive.namelist()
            if "[Content_Types].xml" not in names:
                raise AppError(
                    "INVALID_DOCX", "File is not a valid DOCX document", 422
                )
            media = [
                info
                for info in archive.infolist()
                if info.filename.startswith("word/media/")
                and not info.is_dir()
            ]
            total_size = sum(info.file_size for info in media)
            if total_size > self.config.max_upload_bytes * 5:
                raise AppError(
                    "DOCX_EXPANSION_LIMIT",
                    "Expanded DOCX media exceeds the safety limit",
                    422,
                )

            results: list[ExtractedImage] = []
            for index, info in enumerate(media, start=1):
                if index > self.config.max_images_per_file:
                    raise AppError(
                        "TOO_MANY_IMAGES",
                        "The DOCX contains too many images",
                        422,
                        {"max_images": self.config.max_images_per_file},
                    )
                try:
                    data = archive.read(info)
                    result = self._canonicalize_bytes(
                        data,
                        output_dir / f"{index:04d}.png",
                        Path(info.filename).name,
                        index,
                        None,
                    )
                except AppError as exc:
                    if exc.code in {"INVALID_IMAGE", "IMAGE_TOO_SMALL"}:
                        continue
                    raise
                results.append(result)
        return results

    def _canonicalize_path(
        self,
        source: Path,
        destination: Path,
        source_name: str,
        index: int,
        page_number: int | None,
    ) -> ExtractedImage:
        try:
            with Image.open(source) as image:
                image.load()
                return self._save_image(
                    image, destination, source_name, index, page_number
                )
        except (UnidentifiedImageError, OSError) as exc:
            raise AppError("INVALID_IMAGE", "Unable to decode image", 422) from exc

    def _canonicalize_bytes(
        self,
        data: bytes,
        destination: Path,
        source_name: str,
        index: int,
        page_number: int | None,
    ) -> ExtractedImage:
        try:
            with Image.open(BytesIO(data)) as image:
                image.load()
                return self._save_image(
                    image, destination, source_name, index, page_number
                )
        except (UnidentifiedImageError, OSError) as exc:
            raise AppError("INVALID_IMAGE", "Unable to decode image", 422) from exc

    def _save_image(
        self,
        image: Image.Image,
        destination: Path,
        source_name: str,
        index: int,
        page_number: int | None,
    ) -> ExtractedImage:
        image = ImageOps.exif_transpose(image)
        width, height = image.size
        if width * height > self.config.max_image_pixels:
            raise AppError(
                "IMAGE_TOO_LARGE",
                "Image pixel count exceeds the safety limit",
                422,
                {"max_pixels": self.config.max_image_pixels},
            )
        if min(width, height) < self.config.min_image_side:
            raise AppError(
                "IMAGE_TOO_SMALL",
                "Image is too small to analyze",
                422,
                {"min_side": self.config.min_image_side},
            )
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, "white")
            background.paste(image, mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, format="PNG", optimize=True)
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        return ExtractedImage(
            path=self.storage.relative(destination),
            source_name=source_name,
            source_index=index,
            page_number=page_number,
            width=width,
            height=height,
            sha256=digest,
        )
