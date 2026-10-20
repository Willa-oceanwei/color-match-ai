"""Lossless photo orientation changes applied to the pixels before storage."""
from io import BytesIO

from PIL import Image, ImageOps


def transform_photo(content: bytes, clockwise_turns: int = 0, mirror: bool = False,
                    crop=None) -> bytes:
    with Image.open(BytesIO(content)) as source:
        image = ImageOps.exif_transpose(source)
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGBA' if 'transparency' in image.info else 'RGB')
        turns = clockwise_turns % 4
        operations = {1: Image.Transpose.ROTATE_270, 2: Image.Transpose.ROTATE_180,
                      3: Image.Transpose.ROTATE_90}
        if turns:
            image = image.transpose(operations[turns])
        if mirror:
            image = ImageOps.mirror(image)
        if crop is not None:
            left, top, right, bottom = crop
            if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
                raise ValueError('裁切範圍必須保留寬度和高度。')
            width, height = image.size
            box = (round(left * width), round(top * height),
                   round(right * width), round(bottom * height))
            if box[2] <= box[0] or box[3] <= box[1]:
                raise ValueError('裁切範圍太小，請擴大範圍。')
            image = image.crop(box)
        output = BytesIO()
        image.save(output, format='PNG', icc_profile=image.info.get('icc_profile'))
        return output.getvalue()
