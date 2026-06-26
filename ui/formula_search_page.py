import streamlit as st
import base64
import io
from PIL import Image
from services.google_sheet import get_all_colorboards, lookup_formula_by_id


def _base64_to_image(b64: str):
    try:
        img_bytes = base64.b64decode(b64)
        return Image.open(io.BytesIO(img_bytes))
    except Exception:
        return None


def render_formula_search_page():
    st.markdown(
        "<h2 style='font-size: 24px; font-weight: bold;'>搜尋配方色板</h2>",
        unsafe_allow_html=True
    )

    formula_id = st.text_input("輸入配方編號", placeholder="例如：52824")

    if not formula_id.strip():
        st.info("請輸入配方編號")
        return

    # 搜尋 ColorBoard
    all_rows = get_all_colorboards()
    matched = [
        r for r in all_rows
        if str(r.get("FormulaID", "")).strip() == formula_id.strip()
    ]

    if not matched:
        st.warning(f"查無配方編號：{formula_id}")
        return

    st.success(f"找到 {len(matched)} 筆色板")

    # 配方資料
    formulas = lookup_formula_by_id(formula_id.strip())
    if formulas:
        f = formulas[0]
        st.markdown("### 🧪 配方資料")
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("添加比例", f"{f.get('AddRatio', '-')} g/kg")
        with col_b:
            st.metric("淨重", f"{f.get('NetWeight', '-')} g")
        with col_c:
            st.metric("合計類別", f.get("TotalType", "-"))
        with col_d:
            st.metric("Pantone", f.get("Pantone", "-"))

        # 色粉明細
        pigment_data = []
        for i in range(1, 9):
            p = f.get(f"Pigment{i}", "")
            w = f.get(f"Weight{i}", "")
            if p:
                pigment_data.append({
                    "色粉編號": p,
                    "重量 (g)": w
                })
        if pigment_data:
            st.markdown("**色粉明細**")
            st.table(pigment_data)

        if f.get("Remark"):
            st.caption(f"備註：{f.get('Remark')}")

        st.divider()

    # 色板圖片
    st.markdown("### 🎨 相關色板")
    cols = st.columns(3)
    for i, row in enumerate(matched):
        with cols[i % 3]:
            b64 = row.get("ImageBase64", "")
            if b64:
                img = _base64_to_image(b64)
                if img:
                    st.image(img, use_container_width=True)
            st.caption(f"**{row.get('ID', '')}**")
            st.caption(f"Material: {row.get('Material', '')}")
            st.caption(f"Status: {row.get('RecipeStatus', '')}")
            st.caption(f"Customer: {row.get('Customer', '')}")
            st.caption(f"ColorName: {row.get('ColorName', '')}")
