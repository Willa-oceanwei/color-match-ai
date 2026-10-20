import base64
import importlib.util
from io import BytesIO
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.color_service import (
    ColorRegionError, analyze_image, delta_e76, rgb_to_lab,
)


def photo(color, background=(215, 215, 215)):
    image = Image.new('RGB', (240, 180), background)
    ImageDraw.Draw(image).rectangle((65, 40, 175, 150), fill=color)
    return image


def encoded(image):
    stream = BytesIO()
    image.save(stream, format='PNG')
    return base64.b64encode(stream.getvalue()).decode()


class ColorMatchingTests(unittest.TestCase):
    def test_lab_reference_white_black_red(self):
        np.testing.assert_allclose(rgb_to_lab([255, 255, 255]), [100, 0, 0], atol=0.001)
        np.testing.assert_allclose(rgb_to_lab([0, 0, 0]), [0, 0, 0], atol=0.001)
        np.testing.assert_allclose(rgb_to_lab([255, 0, 0]), [53.24, 80.09, 67.20], atol=0.02)

    def test_preserves_white_board_on_gray(self):
        profile = analyze_image(photo((245, 245, 245), (90, 90, 90)))
        self.assertEqual(profile.rgb, (245, 245, 245))

    def test_preserves_gray_board_on_white(self):
        self.assertEqual(analyze_image(photo((120, 120, 120))).rgb, (120, 120, 120))

    def test_blue_not_dominated_by_white_background(self):
        self.assertEqual(analyze_image(photo((20, 45, 80))).rgb, (20, 45, 80))

    def test_unidentifiable_uniform_photo_requires_manual_crop(self):
        image = Image.new('RGB', (180, 180), 'white')
        with self.assertRaises(ColorRegionError):
            analyze_image(image)
        self.assertEqual(analyze_image(image, (0.2, 0.2, 0.8, 0.8)).rgb, (255, 255, 255))

    def test_invalid_roi_is_reported(self):
        with self.assertRaises(ColorRegionError):
            analyze_image(photo('blue'), (0.5, 0.2, 0.5, 0.8))

    def test_weak_background_contrast_requires_manual_region(self):
        with self.assertRaises(ColorRegionError):
            analyze_image(photo((245, 245, 245), (215, 215, 215)))

    def test_manual_crop_and_auto_agree(self):
        image = photo((120, 130, 140))
        automatic = analyze_image(image)
        manual = analyze_image(image, (0.35, 0.35, 0.65, 0.65))
        self.assertAlmostEqual(delta_e76(automatic.lab, manual.lab), 0.0)

    def test_mask_preview_marks_background(self):
        profile = analyze_image(photo((245, 245, 245), (90, 90, 90)))
        preview = Image.open(BytesIO(base64.b64decode(profile.preview_base64)))
        self.assertEqual(preview.getpixel((0, 0)), (255, 0, 180))
        self.assertEqual(preview.getpixel((80, 60)), (245, 245, 245))

    def test_search_filters_colors_and_material_and_reports_bad_photos(self):
        fake_db = types.ModuleType('services.turso_db')
        rows = [
            {'ID': 'white', 'Material': 'PP', 'ImageBase64': encoded(photo((245,245,245), (90,90,90)))},
            {'ID': 'blue', 'Material': 'PP', 'ImageBase64': encoded(photo((20,45,80)))},
            {'ID': 'other', 'Material': 'ABS', 'ImageBase64': encoded(photo((245,245,245), (90,90,90)))},
            {'ID': 'bad', 'Material': 'PP', 'ImageBase64': 'corrupt!'},
        ]
        fake_db.get_all_color_match_boards = lambda: rows
        with patch.dict(sys.modules, {'services.turso_db': fake_db}):
            spec = importlib.util.spec_from_file_location(
                '_isolated_search', Path(__file__).resolve().parents[1] / 'services/search_service.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            search_top_k = module.search_top_k
        query = BytesIO(base64.b64decode(encoded(photo((245,245,245), (90,90,90)))))
        diagnostics = {}
        results = search_top_k('PP', query, diagnostics=diagnostics)
        self.assertEqual([r['id'] for r in results], ['white'])
        self.assertEqual(diagnostics['compared'], 2)
        self.assertEqual(diagnostics['outside_threshold'], 1)
        self.assertEqual(diagnostics['skipped'][0]['id'], 'bad')
        self.assertNotIn('score', results[0])
        self.assertEqual(search_top_k('ALL', query, top_k=0), [])


if __name__ == '__main__':
    unittest.main()
