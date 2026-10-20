"""Photo color estimates; background is identified by edge connectivity, not hue."""
import base64
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO

import numpy as np
from PIL import Image, ImageFilter, ImageOps


class ColorRegionError(ValueError):
    pass


@dataclass
class ColorProfile:
    lab: np.ndarray
    rgb: tuple
    preview_base64: str


def rgb_to_lab(rgb):
    rgb = np.asarray(rgb, dtype=float) / 255.0
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    xyz = linear @ np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ]).T
    xyz /= np.array([0.95047, 1.0, 1.08883])
    delta = 6 / 29
    f = np.where(xyz > delta ** 3, np.cbrt(xyz), xyz / (3 * delta ** 2) + 4 / 29)
    return np.stack((116 * f[..., 1] - 16,
                     500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])), axis=-1)


def _flood(candidate, seeds):
    height, width = candidate.shape
    visited = np.zeros_like(candidate, dtype=bool)
    queue = deque()
    for y, x in seeds:
        if candidate[y, x] and not visited[y, x]:
            visited[y, x] = True
            queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        for yy, xx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
            if 0 <= yy < height and 0 <= xx < width:
                if candidate[yy, xx] and not visited[yy, xx]:
                    visited[yy, xx] = True
                    queue.append((yy, xx))
    return visited


def _foreground(lab):
    height, width = lab.shape[:2]
    # Several edge references tolerate gradients and mixed table/wall colors.
    edges = [lab[0], lab[-1], lab[:, 0], lab[:, -1]]
    references = [np.median(part, axis=0) for edge in edges
                  for part in np.array_split(edge, 4) if len(part)]
    candidate = np.zeros((height, width), dtype=bool)
    for reference in references:
        candidate |= np.linalg.norm(lab - reference, axis=-1) <= 10.0
    seeds = ([(0, x) for x in range(width)] + [(height-1, x) for x in range(width)]
             + [(y, 0) for y in range(height)] + [(y, width-1) for y in range(height)])
    foreground = ~_flood(candidate, seeds)
    # Retain the largest connected object intersecting the central area.
    remaining = foreground.copy()
    best = np.zeros_like(foreground)
    central = (slice(height//4, 3*height//4), slice(width//4, 3*width//4))
    while remaining.any():
        y, x = np.argwhere(remaining)[0]
        component = _flood(remaining, [(int(y), int(x))])
        remaining[component] = False
        if component[central].any() and component.sum() > best.sum():
            best = component
    # Avoid uncertain boundaries, text near the rim, and background spill.
    best = np.asarray(Image.fromarray(best.astype('uint8') * 255).filter(
        ImageFilter.MinFilter(3))) > 0
    fraction = float(best.mean())
    if fraction < 0.03 or fraction > 0.95:
        raise ColorRegionError("無法可靠區分色板與背景，請改用手動取色範圍。")
    selected_color = np.median(lab[best], axis=0)
    if min(np.linalg.norm(selected_color - ref) for ref in references) < 15.0:
        raise ColorRegionError("色板與照片邊緣顏色太接近，請手動選擇色板內部取色。")
    return best


def analyze_image(image, roi=None):
    """roi is an explicit normalized (left, top, right, bottom) color-only crop."""
    image = ImageOps.exif_transpose(image).convert('RGB')
    if roi is not None:
        left, top, right, bottom = roi
        if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
            raise ColorRegionError("取色範圍必須有寬度和高度。")
        w, h = image.size
        box = (round(left*w), round(top*h), round(right*w), round(bottom*h))
        if box[2] <= box[0] or box[3] <= box[1]:
            raise ColorRegionError("取色範圍太小。")
        image = image.crop(box)
    image.thumbnail((160, 160))
    if min(image.size) < 5:
        raise ColorRegionError("圖片太小，無法取色。")
    rgb = np.asarray(image)
    lab = rgb_to_lab(rgb)
    mask = _foreground(lab) if roi is None else np.ones(rgb.shape[:2], dtype=bool)
    pixels = lab[mask]
    # Trim only luminance extremes within the selected object, never all whites/grays.
    low, high = np.percentile(pixels[:, 0], [10, 90])
    mask &= (lab[:, :, 0] >= low) & (lab[:, :, 0] <= high)
    if not mask.any():
        raise ColorRegionError("取色範圍內沒有可用像素。")
    preview = rgb.copy()
    preview[~mask] = (255, 0, 180)  # Explicit excluded-region overlay.
    buffer = BytesIO()
    Image.fromarray(preview).save(buffer, format='PNG')
    return ColorProfile(
        lab=np.median(lab[mask], axis=0),
        rgb=tuple(int(v) for v in np.median(rgb[mask], axis=0)),
        preview_base64=base64.b64encode(buffer.getvalue()).decode('ascii'),
    )


@lru_cache(maxsize=64)
def profile_from_base64(encoded, roi=None):
    with Image.open(BytesIO(base64.b64decode(encoded, validate=True))) as image:
        return analyze_image(image, roi)


def profile_from_path(path, roi=None):
    with Image.open(path) as image:
        return analyze_image(image, roi)


def delta_e76(first, second):
    return float(np.linalg.norm(np.asarray(first) - np.asarray(second)))
