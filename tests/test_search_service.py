import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np


class SearchServiceTests(unittest.TestCase):
    def setUp(self):
        database = ModuleType('services.turso_db')
        self.boards = [
            {'ID': 'ABS_1', 'Material': 'ABS', 'ImageBase64': 'abs',
             'FormulaID': '1', 'SampleImage1Base64': 'sample-one',
             'SampleDescription': '正面為標準面'},
            {'ID': 'PP_2', 'Material': 'PP', 'ImageBase64': 'pp', 'FormulaID': '2'},
        ]
        database.get_all_color_match_boards = lambda: self.boards
        spec = importlib.util.spec_from_file_location(
            '_search_service_test', Path(__file__).resolve().parents[1] / 'services/search_service.py')
        self.search = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'services.turso_db': database}):
            spec.loader.exec_module(self.search)
        def profile(lightness):
            return SimpleNamespace(lab=np.array([lightness, 0, 0]), rgb=(100,100,100),
                                   preview_base64='preview')
        self.search.profile_from_path = lambda path, roi=None: profile(90)
        self.loaded = []
        def load_photo(encoded, roi=None):
            self.loaded.append(encoded)
            return profile(88 if encoded == 'abs' else 80)
        self.search.profile_from_base64 = load_photo

    def test_unrestricted_search_compares_both_materials_and_keeps_archive(self):
        results = self.search.search_top_k('ALL', 'query.jpg')
        self.assertEqual(self.loaded, ['abs', 'pp'])
        self.assertEqual([item['id'] for item in results], ['ABS_1', 'PP_2'])
        self.assertEqual(results[0]['sample_image_1_base64'], 'sample-one')
        self.assertEqual(results[0]['sample_description'], '正面為標準面')
        self.assertEqual(results[0]['delta_e'], 2)

    def test_material_filter_is_case_insensitive(self):
        results = self.search.search_top_k(' pp ', 'query.jpg')
        self.assertEqual([item['id'] for item in results], ['PP_2'])
        self.assertEqual(self.loaded, ['pp'])

    def test_threshold_does_not_force_dissimilar_first_result(self):
        report = {}
        self.assertEqual(self.search.search_top_k('ALL', 'query.jpg', max_delta_e=1,
                                                  diagnostics=report), [])
        self.assertEqual(report['outside_threshold'], 2)

    def test_top_k_limits_sorted_results(self):
        self.assertEqual(len(self.search.search_top_k('ALL', 'query.jpg', top_k=1)), 1)


if __name__ == '__main__':
    unittest.main()
