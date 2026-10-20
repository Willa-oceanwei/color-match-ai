from pathlib import Path

from services.color_service import (
    ColorRegionError, delta_e76, profile_from_base64, profile_from_path,
)
from services.turso_db import get_all_color_match_boards


def search_top_k(material: str | None, image_path, top_k: int = 5, *,
                 query_roi=None, board_roi=None, max_delta_e=20.0, diagnostics=None):
    """Compare current photos using the same extraction for query and boards.

    Old embeddings are deliberately unused: they still contain background.
    No remote photo URLs are fetched. Missing/ambiguous photos are reported.
    """
    if top_k <= 0:
        return []
    query = profile_from_path(image_path, query_roi)
    selected_material = (material or '').strip().upper()
    all_items = get_all_color_match_boards()
    if selected_material not in ('', 'ALL'):
        all_items = [item for item in all_items
                     if str(item.get('Material', '')).strip().upper() == selected_material]
    report = diagnostics if diagnostics is not None else {}
    report.update(skipped=[], compared=0, outside_threshold=0)
    results = []
    for item in all_items:
        try:
            encoded = item.get('ImageBase64', '') or ''
            if encoded:
                board = profile_from_base64(encoded, board_roi)
            else:
                path = Path(item.get('ImagePath', '') or '')
                if not path.is_file():
                    raise ColorRegionError('缺少可讀取的歷史色板照片')
                board = profile_from_path(path, board_roi)
        except (ValueError, OSError) as error:
            report['skipped'].append({'id': item.get('ID', ''), 'reason': str(error)})
            continue
        report['compared'] += 1
        distance = delta_e76(query.lab, board.lab)
        if distance > max_delta_e:
            report['outside_threshold'] += 1
            continue
        results.append({
            'id': item['ID'],
            'delta_e': distance,
            'query_preview_base64': query.preview_base64,
            'board_preview_base64': board.preview_base64,
            'query_rgb': query.rgb,
            'board_rgb': board.rgb,
            'image_path': item.get('ImagePath', ''),
            'image_base64': item.get('ImageBase64', ''),
            'sample_image_1_base64': item.get('SampleImage1Base64', ''),
            'sample_image_2_base64': item.get('SampleImage2Base64', ''),
            'sample_description': item.get('SampleDescription', ''),
            'formula_id': item.get('FormulaID', ''),
            'recipe_status': item.get('RecipeStatus', 'UNKNOWN'),
            'material': item.get('Material', ''),
        })
    return sorted(results, key=lambda item: item['delta_e'])[:top_k]
