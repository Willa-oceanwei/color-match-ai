import hashlib
from io import BytesIO

import streamlit as st

from services.image_transforms import transform_photo


def _reset_crop(key):
    st.session_state[f'{key}_crop_enabled'] = False
    for edge in ('top', 'sides', 'left', 'right', 'bottom'):
        st.session_state[f'{key}_crop_{edge}'] = 0
    st.session_state[f'{key}_crop_advanced'] = False


def _crop_box(key):
    if not st.session_state.get(f'{key}_crop_enabled', False):
        return None
    top = st.session_state.get(f'{key}_crop_top', 0)
    sides = st.session_state.get(f'{key}_crop_sides', 0)
    if st.session_state.get(f'{key}_crop_advanced', False):
        left = st.session_state.get(f'{key}_crop_left', sides)
        right = st.session_state.get(f'{key}_crop_right', sides)
        bottom = st.session_state.get(f'{key}_crop_bottom', 0)
    else:
        left = right = sides
        bottom = 0
    return (left / 100, top / 100, 1 - right / 100, 1 - bottom / 100)


def _enable_advanced_crop(key):
    if st.session_state.get(f'{key}_crop_advanced', False):
        sides = st.session_state.get(f'{key}_crop_sides', 0)
        st.session_state[f'{key}_crop_left'] = sides
        st.session_state[f'{key}_crop_right'] = sides
        st.session_state[f'{key}_crop_bottom'] = 0


def photo_is_modified(key):
    state = st.session_state.get(f'{key}_orientation', {})
    crop = _crop_box(key)
    cropped = crop is not None and crop != (0, 0, 1, 1)
    return bool(state.get('turns', 0) or state.get('mirror', False) or cropped)


def _adjust_photo(state_key, action):
    state = dict(st.session_state[state_key])
    if action == 'reset':
        state.update(turns=0, mirror=False)
        _reset_crop(state_key.removesuffix('_orientation'))
    elif action == 'mirror':
        state['mirror'] = not state['mirror']
    else:
        # Keep left/right relative to the displayed image after a mirror, too.
        delta = 1 if action == 'right' else -1
        state['turns'] = (state['turns'] + (-delta if state['mirror'] else delta)) % 4
    st.session_state[state_key] = state


def render_photo_editor(uploaded, *, key, allow_crop=False):
    """Return the exact PNG bytes displayed here, or None for no/invalid photo."""
    state_key = f'{key}_orientation'
    if uploaded is None:
        st.session_state.pop(state_key, None)
        _reset_crop(key)
        return None
    content = uploaded.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    state = st.session_state.get(state_key)
    if not state or state['source'] != digest:
        state = {'source': digest, 'turns': 0, 'mirror': False}
        st.session_state[state_key] = state
        _reset_crop(key)

    with st.container(key=f'photo_tools_{key}'):
        columns = st.columns(4, gap='small')
        actions = [('左轉 90°', 'left'), ('右轉 90°', 'right'),
                   ('水平翻轉', 'mirror'), ('還原', 'reset')]
        for column, (label, action) in zip(columns, actions):
            with column:
                st.button(label, key=f'{key}_{action}', use_container_width=True,
                          on_click=_adjust_photo, args=(state_key, action))

    crop = None
    if allow_crop and st.checkbox('裁切照片', key=f'{key}_crop_enabled'):
        st.caption('滑桿數字代表要裁掉的比例，0% 表示不裁；預覽會即時更新。')
        st.slider('裁上方（%）', 0, 95, key=f'{key}_crop_top')
        advanced = st.session_state.get(f'{key}_crop_advanced', False)
        st.slider('裁左右（每側 %）', 0, 45, key=f'{key}_crop_sides', disabled=advanced,
                  help='例如 10% 代表左邊、右邊各裁掉照片寬度的 10%。')
        with st.expander('進階設定：左右分開／裁下方'):
            if st.checkbox('左右分開裁切／裁下方', key=f'{key}_crop_advanced',
                           on_change=_enable_advanced_crop, args=(key,)):
                st.slider('裁左方（%）', 0, 95, key=f'{key}_crop_left')
                st.slider('裁右方（%）', 0, 95, key=f'{key}_crop_right')
                st.slider('裁下方（%）', 0, 95, key=f'{key}_crop_bottom')
        crop = _crop_box(key)
    try:
        edited = transform_photo(content, state['turns'], state['mirror'], crop)
    except (OSError, ValueError) as error:
        st.error(f'照片無法處理：{error}')
        return None

    st.image(BytesIO(edited), caption='照片預覽：儲存時會使用此畫面', use_container_width=True)
    return edited
