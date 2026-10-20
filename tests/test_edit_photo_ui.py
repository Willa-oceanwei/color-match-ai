import base64
from io import BytesIO
from pathlib import Path
import unittest

from PIL import Image
from streamlit.testing.v1 import AppTest


KEY = 'edit_board_photo_PP_TEST'


class EditPhotoTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(Path(__file__).with_name('edit_fixture.py')),
                                 default_timeout=15).run()

    def save(self, app):
        next(button for button in app.button if button.label == '儲存更新').click().run()

    def test_existing_photo_can_rotate_and_crop_without_reupload(self):
        app = self.app()
        app.button(key=f'{KEY}_right').click().run()
        app.checkbox(key=f'{KEY}_crop_enabled').check().run()
        app.slider(key=f'{KEY}_crop_sides').set_value(10).run()
        app.slider(key=f'{KEY}_crop_top').set_value(20).run()
        self.assertEqual(len(app.exception), 0)
        self.save(app)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        updates = app.session_state['test_updates']
        self.assertEqual(updates[0]['ImagePath'], 'PP/PP_TEST.png')
        photo = base64.b64decode(updates[0]['ImageBase64'])
        self.assertEqual(Image.open(BytesIO(photo)).size, (48,80))
        self.assertEqual(photo, app.session_state['test_edit_embedding'])
        self.assertEqual(updates[-1]['EmbeddingStatus'], 'Y')

    def test_metadata_only_save_does_not_rewrite_image(self):
        app = self.app()
        self.save(app)
        self.assertEqual(len(app.exception), 0)
        self.assertNotIn('ImageBase64', app.session_state['test_updates'][0])
        self.assertNotIn('test_edit_embedding', app.session_state)
        self.assertNotIn('test_photo_writes', app.session_state)

    def test_invalid_crop_blocks_save_and_reset_restores_original(self):
        app = self.app()
        app.checkbox(key=f'{KEY}_crop_enabled').check().run()
        app.checkbox(key=f'{KEY}_crop_advanced').check().run()
        app.slider(key=f'{KEY}_crop_left').set_value(60).run()
        app.slider(key=f'{KEY}_crop_right').set_value(60).run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(next(b for b in app.button if b.label == '儲存更新').disabled)
        app.button(key=f'{KEY}_reset').click().run()
        self.assertFalse(app.checkbox(key=f'{KEY}_crop_enabled').value)
        self.save(app)
        self.assertEqual(len(app.exception), 0)
        self.assertNotIn('ImageBase64', app.session_state['test_updates'][0])

    def test_advanced_crop_starts_from_symmetric_crop_and_saves_independent_edges(self):
        app = self.app()
        app.checkbox(key=f'{KEY}_crop_enabled').check().run()
        app.slider(key=f'{KEY}_crop_sides').set_value(10).run()
        app.checkbox(key=f'{KEY}_crop_advanced').check().run()
        self.assertEqual(app.slider(key=f'{KEY}_crop_left').value, 10)
        self.assertEqual(app.slider(key=f'{KEY}_crop_right').value, 10)
        self.assertTrue(app.slider(key=f'{KEY}_crop_sides').disabled)
        app.slider(key=f'{KEY}_crop_left').set_value(20).run()
        app.slider(key=f'{KEY}_crop_right').set_value(5).run()
        app.slider(key=f'{KEY}_crop_bottom').set_value(10).run()
        self.save(app)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        photo = base64.b64decode(app.session_state['test_updates'][0]['ImageBase64'])
        self.assertEqual(Image.open(BytesIO(photo)).size, (75,54))

    def test_enabling_crop_at_zero_does_not_rewrite_photo(self):
        app = self.app()
        app.checkbox(key=f'{KEY}_crop_enabled').check().run()
        self.save(app)
        self.assertEqual(len(app.exception), 0)
        self.assertNotIn('ImageBase64', app.session_state['test_updates'][0])

    def test_add_second_sample_with_rotation_preserves_first_and_main_photo(self):
        app = self.app()
        stream = BytesIO()
        Image.new('RGB', (80,50), 'green').save(stream, format='PNG')
        app.session_state['test_sample_uploads'] = {2: stream.getvalue()}
        app.run()
        key = 'edit_sample_photo_PP_TEST_2'
        app.button(key=f'{key}_right').click().run()
        app.checkbox(key=f'{key}_crop_enabled').check().run()
        app.slider(key=f'{key}_crop_top').set_value(25).run()
        self.save(app)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        updates = app.session_state['test_updates'][0]
        self.assertEqual(updates['SampleImage2Path'], 'PP/PP_TEST_sample2.png')
        photo = Image.open(BytesIO(base64.b64decode(updates['SampleImage2Base64'])))
        self.assertEqual(photo.size, (50,60))
        self.assertNotIn('SampleImage1Base64', updates)
        self.assertNotIn('ImageBase64', updates)
        self.assertNotIn('EmbeddingStatus', updates)
        self.assertNotIn('test_edit_embedding', app.session_state)

    def test_replace_second_sample_and_change_description(self):
        app = self.app()
        row = dict(app.session_state['edit_target'])
        row['SampleImage2Base64'] = row['SampleImage1Base64']
        app.session_state['edit_target'] = row
        stream = BytesIO()
        Image.new('RGB', (70,40), 'yellow').save(stream, format='PNG')
        app.session_state['test_sample_uploads'] = {2: stream.getvalue()}
        app.run()
        app.text_area(key='edit_sample_description_PP_TEST').set_value('Updated sample').run()
        self.save(app)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        updates = app.session_state['test_updates'][0]
        self.assertNotEqual(updates['SampleImage2Base64'], row['SampleImage2Base64'])
        self.assertEqual(updates['SampleDescription'], 'Updated sample')
        self.assertNotIn('SampleImage1Base64', updates)

    def test_invalid_second_sample_crop_blocks_save(self):
        app = self.app()
        stream = BytesIO()
        Image.new('RGB', (80,50), 'green').save(stream, format='PNG')
        app.session_state['test_sample_uploads'] = {2: stream.getvalue()}
        app.run()
        key = 'edit_sample_photo_PP_TEST_2'
        app.checkbox(key=f'{key}_crop_enabled').check().run()
        app.checkbox(key=f'{key}_crop_advanced').check().run()
        app.slider(key=f'{key}_crop_left').set_value(60).run()
        app.slider(key=f'{key}_crop_right').set_value(60).run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(next(b for b in app.button if b.label == '儲存更新').disabled)


if __name__ == '__main__':
    unittest.main()
