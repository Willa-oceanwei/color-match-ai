"""Lossless photo orientation changes applied to the pixels before storage."""
from io import BytesIO

from PIL import Image, ImageOps


def transform_photo(content: bytes, clockwise_turns: int = 0, mirror: bool = False) -> bytes:
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
        output = BytesIO()
        image.save(output, format='PNG', icc_profile=image.info.get('icc_profile'))
        return output.getvalue()
