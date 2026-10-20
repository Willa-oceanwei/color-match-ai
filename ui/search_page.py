import base64
import hashlib
from io import BytesIO

import streamlit as st
from PIL import Image

from ui.design import render_page_header


def _roi_controls(label, key):
    if not st.checkbox(label, key=f'{key}_enabled'):
        return None
    st.caption('選取色板內部，避開背景、文字與反光。')
    left, right = st.slider('左右範圍（%）', 0, 100, (30, 70), key=f'{key}_x')
    top, bottom = st.slider('上下範圍（%）', 0, 100, (35, 75), key=f'{key}_y')
    return (left / 100, top / 100, right / 100, bottom / 100)


def render_search_page():
    with st.container(key='search_workspace'):
        _render_search_workspace()


def _render_search_workspace():
    from services.color_service import ColorRegionError, analyze_image

    render_page_header('COLOR MATCH', '相似色板搜尋',
                       '排除背景後比較色板顏色，色差越小越接近。')
    material = st.selectbox('原料', ['ALL', 'PP', 'ABS', 'TPR', 'NY', 'PC', 'PE', 'PVC', 'PS'],
                            format_func=lambda v: '全部原料' if v == 'ALL' else v)
    uploaded = st.file_uploader('樣品照片', type=['jpg', 'png', 'jpeg'])
    with st.expander('進階設定', expanded=False):
        show_preview = st.toggle('顯示取色範圍', value=False, key='show_color_preview')
        max_delta_e = st.number_input('色差上限（ΔE76）', min_value=1.0, max_value=100.0,
                                      value=20.0, step=1.0, format='%.0f', key='search_max_delta_e',
                                      help='數值越小，比對越嚴格；超過上限的色板不會顯示。')
        query_roi = _roi_controls('手動選取樣品區域', 'query_roi')
        board_roi = _roi_controls('指定歷史照片取色區域', 'board_roi')
        if board_roi is not None:
            st.caption('此範圍會套用至所有歷史照片，適合構圖一致的照片。')
        st.caption('照片色差受光線影響，僅供比對參考。')
    profile = None
    if uploaded:
        st.image(uploaded, caption='查詢樣品', width=420)
        try:
            with Image.open(BytesIO(uploaded.getvalue())) as image:
                profile = analyze_image(image, query_roi)
            if show_preview:
                st.image(BytesIO(base64.b64decode(profile.preview_base64)),
                         caption='樣品取色預覽：桃紅色區域已排除；其餘區域參與比對', width=320)
        except (ColorRegionError, OSError, ValueError) as error:
            st.warning(str(error))
            st.caption('請展開「進階設定」，手動選取樣品區域。')

    signature = (hashlib.sha256(uploaded.getvalue()).hexdigest(), material,
                 query_roi, board_roi, max_delta_e) if uploaded and profile else None
    saved = st.session_state.get('color_search_results')
    if saved and saved['signature'] != signature:
        st.session_state.pop('color_search_results', None)

    if st.button('開始比對', disabled=profile is None, type='primary', use_container_width=True):
        from services.search_service import search_top_k

        diagnostics = {}
        try:
            # In-memory per-request image avoids sharing tmp/query.jpg across users.
            with st.spinner('正在排除背景並比較色差…'):
                results = search_top_k(material, BytesIO(uploaded.getvalue()), top_k=5,
                                       query_roi=query_roi, board_roi=board_roi,
                                       max_delta_e=max_delta_e, diagnostics=diagnostics)
            st.session_state.color_search_results = {
                'signature': signature, 'results': results, 'diagnostics': diagnostics,
            }
        except Exception as error:
            st.session_state.pop('color_search_results', None)
            st.error(f'搜尋失敗：{error}')

    saved = st.session_state.get('color_search_results')
    if saved:
        from ui.result_components import render_result_card

        results, diagnostics = saved['results'], saved['diagnostics']
        skipped = diagnostics.get('skipped', [])
        if skipped:
            st.warning(f'{len(skipped)} 張歷史照片無法可靠取色，已略過。')
            with st.expander('查看略過原因'):
                st.dataframe(skipped, use_container_width=True)
        st.caption(f"已比較 {diagnostics.get('compared', 0)} 張；"
                   f"{diagnostics.get('outside_threshold', 0)} 張超過色差上限。")
        if not results:
            st.warning('沒有符合色差上限的色板。請確認取色範圍，或調整色差上限。')
        else:
            st.success(f'找到 {len(results)} 筆結果')
            for index, result in enumerate(results, 1):
                render_result_card(index, result, show_color_preview=show_preview,
                                   query_image=BytesIO(uploaded.getvalue()))
