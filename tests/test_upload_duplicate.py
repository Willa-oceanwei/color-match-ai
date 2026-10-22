from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from services import google_drive
from services.turso_db import DuplicateColorBoardError
from ui import upload_page


@pytest.fixture
def upload_app(monkeypatch, tmp_path):
    upload = SimpleNamespace(name="board.png")
    monkeypatch.setattr(
        upload_page.st, "file_uploader",
        lambda label, **kwargs: upload if label == "色板照片" else None,
    )
    monkeypatch.setattr(
        upload_page, "render_photo_editor",
        lambda image, **kwargs: b"image" if image is upload else None,
    )
    monkeypatch.setattr(
        upload_page, "SETTINGS", SimpleNamespace(local_drive_root=tmp_path),
    )
    monkeypatch.setattr(
        upload_page, "resolve_formula_mode",
        lambda formula_id: SimpleNamespace(formula_mode="EXISTING"),
    )

    def write_photo(data, path):
        full_path = tmp_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return path, "base64"

    writer = Mock(side_effect=write_photo)
    monkeypatch.setattr(google_drive, "write_uploaded_bytes_get_base64", writer)
    status = Mock()
    embedding = Mock(return_value=[1.0])
    vector = Mock()
    monkeypatch.setattr(upload_page, "update_color_match_embedding_status", status)
    monkeypatch.setattr(upload_page, "get_cached_embedding", embedding)
    monkeypatch.setattr(upload_page, "resolve_local_image_path", lambda path: tmp_path / path)
    monkeypatch.setattr(upload_page, "upsert_embedding", vector)

    def submit():
        app = AppTest.from_string(
            "from ui.upload_page import render_upload_page\nrender_upload_page()",
            default_timeout=15,
        ).run()
        next(field for field in app.text_input if field.label == "FormulaID").set_value("A1504")
        next(button for button in app.button if button.label == "儲存並建立向量").click().run()
        assert not app.exception
        return app

    return SimpleNamespace(submit=submit, writer=writer, status=status, embedding=embedding, vector=vector)


def test_existing_board_stops_before_image_or_database_writes(monkeypatch, upload_app):
    monkeypatch.setattr(
        upload_page, "get_color_match_board_by_id",
        lambda board_id: {"ID": board_id, "EmbeddingStatus": "Y"},
    )
    insert = Mock()
    monkeypatch.setattr(upload_page, "append_color_match_board", insert)

    app = upload_app.submit()

    assert any("PP_A1504" in warning.value and "編輯色板" in warning.value for warning in app.warning)
    assert not app.error
    upload_app.writer.assert_not_called()
    upload_app.status.assert_not_called()
    upload_app.embedding.assert_not_called()
    insert.assert_not_called()


def test_concurrent_duplicate_does_not_mark_existing_board_failed(monkeypatch, upload_app):
    monkeypatch.setattr(upload_page, "get_color_match_board_by_id", lambda board_id: None)
    monkeypatch.setattr(
        upload_page, "append_color_match_board",
        Mock(side_effect=DuplicateColorBoardError("PP_A1504")),
    )

    app = upload_app.submit()

    assert any("已存在" in warning.value for warning in app.warning)
    assert not app.error
    upload_app.status.assert_not_called()
    upload_app.embedding.assert_not_called()


def test_new_board_still_saves_and_builds_embedding(monkeypatch, upload_app):
    monkeypatch.setattr(
        upload_page, "get_color_match_board_by_id",
        Mock(side_effect=[None, {"ID": "PP_A1504"}]),
    )
    insert = Mock()
    monkeypatch.setattr(upload_page, "append_color_match_board", insert)

    app = upload_app.submit()

    assert app.success
    assert not app.error
    assert insert.call_args.args[0]["ID"] == "PP_A1504"
    upload_app.vector.assert_called_once()
    assert upload_app.status.call_args.args[1] == "Y"


def test_lookup_failure_does_not_write_or_mark_existing_board_failed(monkeypatch, upload_app):
    monkeypatch.setattr(
        upload_page, "get_color_match_board_by_id",
        Mock(side_effect=RuntimeError("database unavailable")),
    )

    app = upload_app.submit()

    assert app.error
    upload_app.writer.assert_not_called()
    upload_app.status.assert_not_called()
