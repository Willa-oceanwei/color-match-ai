import hashlib
from io import BytesIO

import streamlit as st

from services.image_transforms import transform_photo


def _adjust_photo(state_key, action):
    state = dict(st.session_state[state_key])
    if action == 'reset':
        state.update(turns=0, mirror=False)
    elif action == 'mirror':
        state['mirror'] = not state['mirror']
    else:
        # Keep left/right relative to the displayed image after a mirror, too.
        delta = 1 if action == 'right' else -1
        state['turns'] = (state['turns'] + (-delta if state['mirror'] else delta)) % 4
    st.session_state[state_key] = state


def render_photo_editor(uploaded, *, key):
    """Return the exact PNG bytes displayed here, or None for no/invalid photo."""
    state_key = f'{key}_orientation'
    if uploaded is None:
        st.session_state.pop(state_key, None)
        return None
    content = uploaded.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    state = st.session_state.get(state_key)
    if not state or state['source'] != digest:
        state = {'source': digest, 'turns': 0, 'mirror': False}
        st.session_state[state_key] = state
    try:
        edited = transform_photo(content, state['turns'], state['mirror'])
    except (OSError, ValueError) as error:
        st.error(f'照片無法讀取，請重新選擇：{error}')
        return None

    first, second = st.columns(2)
    for column, label, action in (
        (first, '左轉 90°', 'left'), (second, '右轉 90°', 'right'),
        (first, '水平翻轉', 'mirror'), (second, '還原', 'reset'),
    ):
        with column:
            st.button(label, key=f'{key}_{action}', use_container_width=True,
                      on_click=_adjust_photo, args=(state_key, action))
    st.image(BytesIO(edited), caption='照片預覽：儲存時會使用此方向', use_container_width=True)
    return edited
