"""Local edit-page integration fixture, with no production writes."""
import base64
from contextlib import contextmanager
import importlib.util
from io import BytesIO
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
from PIL import Image

if 'test_edit_storage' not in st.session_state:
    st.session_state.test_edit_storage = tempfile.mkdtemp(prefix='edit-test-', dir=Path(__file__).parent)
storage = Path(st.session_state.test_edit_storage)
image = Image.new('RGB', (100, 60), 'red')
image.paste('blue', (60, 0, 100, 60))
stream = BytesIO()
image.save(stream, format='PNG')
if 'test_edit_initialized' not in st.session_state:
    st.session_state.test_edit_initialized = True
    st.session_state.edit_target = {
        'ID': 'PP_TEST', 'Material': 'PP', 'FormulaID': '', 'RecipeStatus': 'OFFICIAL',
        'ImagePath': 'PP/PP_TEST.jpg', 'ImageBase64': base64.b64encode(stream.getvalue()).decode(),
        'Customer': 'Original customer',
        'SampleImage1Path': 'PP/PP_TEST_sample1.jpg',
        'SampleImage1Base64': base64.b64encode(stream.getvalue()).decode(),
        'SampleImage2Base64': '', 'SampleDescription': 'Original sample description',
    }
    st.session_state.test_updates = []

drive = ModuleType('services.google_drive')
drive.resolve_local_image_path = lambda path: storage / path
def write_photo(content, path):
    st.session_state.test_photo_writes = st.session_state.get('test_photo_writes', 0) + 1
    target = storage / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return path, base64.b64encode(content).decode()
drive.write_uploaded_bytes_get_base64 = write_photo
database = ModuleType('services.turso_db')
database.get_color_match_board_by_id = lambda *args: None
database.get_color_match_boards_by_formula_id = lambda *args: []
database.search_color_match_boards = lambda *args: []
def update(board_id, updates):
    st.session_state.test_updates.append(dict(updates))
database.update_color_match_board = update
embedding = ModuleType('services.embedding_service')
def embed(path):
    st.session_state.test_edit_embedding = Path(path).read_bytes()
    return [1, 0]
embedding.embed_image = embed
embedding.upsert_embedding = lambda *args: None
formula = ModuleType('services.formula_repository')
formula.lookup_formula_by_id = lambda *args: []
sheet = ModuleType('services.google_sheet')
sheet.append_formula_row = lambda *args: None
design = ModuleType('ui.design')
design.render_page_header = lambda *args: st.title(args[1])
spec = importlib.util.spec_from_file_location('_edit_fixture_page',
                                            Path(__file__).resolve().parents[1] / 'ui/edit_page.py')
page = importlib.util.module_from_spec(spec)
modules = {'services.google_drive': drive, 'services.turso_db': database,
           'services.embedding_service': embedding, 'services.formula_repository': formula,
           'services.google_sheet': sheet, 'ui.design': design}
@contextmanager
def installed_adapters():
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in modules}
    sys.modules.update(modules)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value

def uploaded(*args, **kwargs):
    upload_key = kwargs.get('key', '')
    for index, content in st.session_state.get('test_sample_uploads', {}).items():
        if upload_key == f'edit_sample_upload_PP_TEST_{index}':
            result = BytesIO(content)
            result.name = 'sample.png'
            return result
    return None

with installed_adapters(), patch.object(st, 'file_uploader', uploaded):
    spec.loader.exec_module(page)
    page.render_edit_page()
