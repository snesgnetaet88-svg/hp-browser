# HP Browser — by hypermarket
"""Анализ изображений для HP Browser — без ИИ, только Pillow.

Публичные функции:
    analyze_screenshot(path) -> dict            # базовая информация
    extract_colors(path, n=10) -> list[tuple]  # топ-N доминирующих цветов
    compare_layout(img1, img2) -> dict         # пиксельное сравнение раскладки

Модуль предназначен для быстрого «зрения»: размеры, пропорции, палитра и
разница между двумя снимками (например, эталон vs HP Browser).
"""

from __future__ import annotations

import os
from typing import Any

from PIL import Image, ImageChops, ImageStat


def _open(path: str | os.PathLike[str]) -> Image.Image:
    img = Image.open(path)
    return img.convert("RGB")


def analyze_screenshot(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Возвращает базовую информацию о снимке.

    Ключи: path, size (w, h), width, height, aspect_ratio, mode,
    mean_color (r, g, b), brightness (0..255), dominant_colors.
    """
    with Image.open(path) as raw:
        width, height = raw.size
        img = raw.convert("RGB")

    stat = ImageStat.Stat(img)
    mean = tuple(round(v, 1) for v in stat.mean)
    brightness = round(sum(mean) / 3, 1)

    return {
        "path": str(path),
        "size": (width, height),
        "width": width,
        "height": height,
        "aspect_ratio": round(width / height, 4) if height else None,
        "mode": raw.mode,
        "mean_color": mean,
        "brightness": brightness,
        "dominant_colors": extract_colors(path, n=5),
    }


def extract_colors(
    path: str | os.PathLike[str], n: int = 10
) -> list[tuple[tuple[int, int, int], float]]:
    """Извлекает топ-N доминирующих цветов.

    Возвращает список ``[((R, G, B), доля), ...]``, отсортированный по убыванию
    доли пикселей (0..1). Использует палитровую квантизацию Pillow.
    """
    img = _open(path)
    # Уменьшаем изображение для скорости анализа.
    img.thumbnail((512, 512))
    quant = img.quantize(colors=max(1, min(n, 256)), method=Image.Quantize.MEDIANCUT)
    palette = quant.getpalette() or []
    counts = quant.getcolors() or []
    total = sum(count for count, _ in counts) or 1

    result: list[tuple[tuple[int, int, int], float]] = []
    for count, index in counts:
        r, g, b = palette[index * 3 : index * 3 + 3]
        result.append(((r, g, b), round(count / total, 4)))
    result.sort(key=lambda item: item[1], reverse=True)
    return result[:n]


def compare_layout(
    img1: str | os.PathLike[str], img2: str | os.PathLike[str]
) -> dict[str, Any]:
    """Сравнивает два снимка по расположению элементов (пиксельная разница).

    Оба изображения приводятся к одному размеру (по первому). Возвращает
    общий процент различий, среднюю разницу и ограничивающий прямоугольник
    отличий (bbox), а также похожесть (0..1).
    """
    a = _open(img1)
    b = _open(img2).resize(a.size)
    diff = ImageChops.difference(a, b)
    stat = ImageStat.Stat(diff)
    mean_diff = round(sum(stat.mean) / len(stat.mean), 2)
    diff_percent = round(mean_diff / 255 * 100, 2)

    bbox = diff.convert("L").point(lambda p: 255 if p > 20 else 0).getbbox()
    return {
        "size": a.size,
        "mean_difference": mean_diff,
        "difference_percent": diff_percent,
        "similarity": round(1 - diff_percent / 100, 4),
        "diff_bbox": bbox,
    }


if __name__ == "__main__":  # pragma: no cover - ручная проверка
    import json
    import sys

    if len(sys.argv) >= 3:
        print(json.dumps(compare_layout(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=2))
    elif len(sys.argv) == 2:
        print(json.dumps(analyze_screenshot(sys.argv[1]), ensure_ascii=False, indent=2))
    else:
        print("usage: vision.py <image> [<image2>]")
