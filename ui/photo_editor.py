import hashlib
from io import BytesIO

import streamlit as st

from services.image_transforms import transform_photo


def _reset_crop(key):
    st.session_state[f'{key}_crop_enabled'] = False
    st.session_state[f'{key}_crop_x'] = (0, 100)
    st.session_state[f'{key}_crop_y'] = (0, 100)


def photo_is_modified(key):
    state = st.session_state.get(f'{key}_orientation', {})
    cropped = (st.session_state.get(f'{key}_crop_enabled', False)
               and (st.session_state.get(f'{key}_crop_x', (0, 100)) != (0, 100)
                    or st.session_state.get(f'{key}_crop_y', (0, 100)) != (0, 100)))
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
        st.caption('拖動左右、上下範圍滑桿，保留需要的色板區域；預覽會即時更新。')
        left, right = st.slider('左右保留範圍（%）', 0, 100, (0, 100), key=f'{key}_crop_x')
        top, bottom = st.slider('上下保留範圍（%）', 0, 100, (0, 100), key=f'{key}_crop_y')
        crop = (left / 100, top / 100, right / 100, bottom / 100)
    try:
        edited = transform_photo(content, state['turns'], state['mirror'], crop)
    except (OSError, ValueError) as error:
        st.error(f'照片無法處理：{error}')
        return None

    st.image(BytesIO(edited), caption='照片預覽：儲存時會使用此畫面', use_container_width=True)
    return edited
