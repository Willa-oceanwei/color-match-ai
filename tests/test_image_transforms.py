from io import BytesIO
from pathlib import Path
import sys
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.image_transforms import transform_photo


COLORS = [(255,0,0), (0,255,0), (0,0,255), (0,255,255), (255,0,255), (255,255,0)]


def source_bytes(orientation=None):
    image = Image.new('RGB', (3, 2))
    image.putdata(COLORS)
    stream = BytesIO()
    options = {}
    if orientation:
        exif = Image.Exif()
        exif[274] = orientation
        options['exif'] = exif
    image.save(stream, format='PNG', **options)
    return stream.getvalue()


class ImageTransformsTests(unittest.TestCase):
    def assert_pixels(self, content, indices, size):
        image = Image.open(BytesIO(content))
        self.assertEqual(image.format, 'PNG')
        self.assertEqual(image.size, size)
        self.assertEqual(list(image.getdata()), [COLORS[i] for i in indices])
        self.assertNotIn(image.getexif().get(274), [2,3,4,5,6,7,8])

    def test_right_rotation_preserves_every_pixel(self):
        self.assert_pixels(transform_photo(source_bytes(), 1), [3,0,4,1,5,2], (2,3))

    def test_left_rotation(self):
        self.assert_pixels(transform_photo(source_bytes(), -1), [2,5,1,4,0,3], (2,3))

    def test_half_turn(self):
        self.assert_pixels(transform_photo(source_bytes(), 2), [5,4,3,2,1,0], (3,2))

    def test_four_rotations_restore_original(self):
        self.assert_pixels(transform_photo(source_bytes(), 4), list(range(6)), (3,2))

    def test_horizontal_mirror(self):
        self.assert_pixels(transform_photo(source_bytes(), mirror=True), [2,1,0,5,4,3], (3,2))

    def test_mirror_after_rotation(self):
        self.assert_pixels(transform_photo(source_bytes(), 1, True), [0,3,1,4,2,5], (2,3))

    def test_phone_exif_orientation_is_applied_once(self):
        edited = transform_photo(source_bytes(6))
        self.assert_pixels(edited, [3,0,4,1,5,2], (2,3))
        self.assert_pixels(transform_photo(edited), [3,0,4,1,5,2], (2,3))

    def test_invalid_photo_is_rejected(self):
        with self.assertRaises(OSError):
            transform_photo(b'not a photo')

    def test_crop_keeps_only_selected_pixels(self):
        self.assert_pixels(transform_photo(source_bytes(), crop=(1/3, 0, 1, 1)),
                           [1,2,4,5], (2,2))

    def test_crop_uses_rotated_dimensions(self):
        self.assert_pixels(transform_photo(source_bytes(), 1, crop=(0, 0, 0.5, 1)),
                           [3,4,5], (1,3))

    def test_empty_and_out_of_bounds_crops_are_rejected(self):
        for crop in [(0.5,0,0.5,1), (-0.1,0,1,1), (0,0,1.1,1), (0,0,0.01,0.01)]:
            with self.subTest(crop=crop), self.assertRaises(ValueError):
                transform_photo(source_bytes(), crop=crop)


if __name__ == '__main__':
    unittest.main()
