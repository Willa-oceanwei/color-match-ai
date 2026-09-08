from PIL import Image

from services.embedding_service import _center_crop


def test_center_crop_removes_outer_background():
    image = Image.new("RGB", (100, 100), "white")
    for x in range(15, 85):
        for y in range(15, 85):
            image.putpixel((x, y), (255, 0, 0))

    cropped = _center_crop(image)

    assert cropped.size == (70, 70)
    assert cropped.getextrema() == ((255, 255), (0, 0), (0, 0))
