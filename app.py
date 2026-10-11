import hashlib
import html

import streamlit as st
from ocr_service import (
    clean_ocr_text,
    extract_medication_info,
    preprocess_image,
    recognize_image,
)


def clear_previous_result():
    """換照片時清除前一次的辨識狀態。"""
    st.session_state.pop("recognition_result", None)


st.set_page_config(
    page_title="AI看得懂藥",
    page_icon="💊",
    layout="centered",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f5faf8;
    }

    .main .block-container {
        max-width: 760px;
        padding: 2rem 1.25rem 3rem;
    }

    h1, h2, h3, p, label, .stMarkdown {
        color: #183b36;
    }

    h1 {
        font-size: clamp(2.2rem, 7vw, 3rem) !important;
        font-weight: 750 !important;
        margin-bottom: 0.5rem !important;
    }

    .subtitle {
        font-size: clamp(1.2rem, 4vw, 1.5rem);
        line-height: 1.7;
        margin: 0.5rem 0 1.5rem;
    }

    [data-testid="stFileUploader"] {
        background: #ffffff;
        border: 2px dashed #8cb9ab;
        border-radius: 18px;
        padding: 1rem;
    }

    [data-testid="stFileUploader"] * {
        font-size: 1.1rem;
    }

    [data-testid="stImage"] {
        display: flex;
        justify-content: center;
        width: 100%;
    }

    [data-testid="stImage"] img {
        max-width: 100%;
        height: auto;
        object-fit: contain;
    }

    .stButton > button {
        min-height: 3.8rem;
        width: 100%;
        border-radius: 14px;
        border: 0;
        background: #197b68;
        color: #ffffff;
        font-size: 1.35rem;
        font-weight: 700;
    }

    .stButton > button:hover {
        background: #126352;
        color: #ffffff;
        border: 0;
    }

    .result-box {
        background: #ffffff;
        border: 1px solid #d5e8e1;
        border-radius: 16px;
        padding: 1.25rem;
        min-height: 100px;
        font-size: 1.1rem;
        line-height: 1.7;
    }

    .medication-card {
        background: #ffffff;
        border: 1px solid #d5e8e1;
        border-radius: 20px;
        padding: clamp(1rem, 4vw, 1.5rem);
        margin: 0.75rem 0 1.5rem;
        box-shadow: 0 4px 16px rgba(24, 59, 54, 0.06);
    }

    .medication-card-title {
        color: #183b36;
        font-size: 1.65rem;
        font-weight: 750;
        margin: 0 0 1rem;
    }

    .medication-name {
        background: #eaf5f1;
        border-left: 6px solid #197b68;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        margin-bottom: 1rem;
    }

    .medication-name .medication-value {
        font-size: clamp(1.5rem, 5vw, 2rem);
        font-weight: 750;
    }

    .medication-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.75rem;
    }

    .medication-field {
        background: #f7fbf9;
        border: 1px solid #e1eee9;
        border-radius: 12px;
        padding: 0.9rem 1rem;
        min-height: 88px;
    }

    .medication-label {
        color: #42675f;
        font-size: 1rem;
        font-weight: 650;
        margin-bottom: 0.35rem;
    }

    .medication-value {
        color: #183b36;
        font-size: 1.2rem;
        line-height: 1.5;
        overflow-wrap: anywhere;
    }

    @media (max-width: 600px) {
        .main .block-container {
            padding: 1.5rem 1rem 2rem;
        }

        .medication-grid {
            grid-template-columns: 1fr;
        }

        .medication-field {
            min-height: 0;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("💊 AI看得懂藥")
st.markdown(
    "<p class='subtitle'>拍攝或上傳藥袋、藥盒或藥瓶照片，<br>協助辨識與整理藥品標示資訊。</p>",
    unsafe_allow_html=True,
)

st.subheader("上傳藥品照片")
selected_image = st.file_uploader(
    "從相簿或檔案選擇照片",
    type=["jpg", "jpeg", "png"],
    help="支援 JPG、JPEG 和 PNG。手機可從相簿選擇照片。",
    label_visibility="collapsed",
    key="photo_upload",
    on_change=clear_previous_result,
)

camera_image = st.camera_input(
    "或使用相機拍攝",
    help="手機瀏覽器可開啟相機拍攝藥品照片。",
    key="camera_capture",
    on_change=clear_previous_result,
)

# 相機照片優先；沒有相機照片時，使用者選取的檔案仍可正常預覽。
uploaded_image = camera_image if camera_image is not None else selected_image
processed_image_bytes = None

if uploaded_image is not None:
    original_image_bytes = uploaded_image.getvalue()
    image_signature = hashlib.sha256(original_image_bytes).hexdigest()
    if st.session_state.get("image_signature") != image_signature:
        st.session_state.pop("recognition_result", None)
        st.session_state["image_signature"] = image_signature
        st.session_state["processed_image_bytes"] = preprocess_image(
            original_image_bytes
        )

    processed_image_bytes = st.session_state["processed_image_bytes"]
    image_version = st.radio(
        "圖片版本",
        options=["原圖", "處理後"],
        horizontal=True,
        label_visibility="collapsed",
        key="image_preview_version",
    )
    st.markdown(f"#### {image_version}")
    if image_version == "原圖":
        st.image(original_image_bytes, use_container_width=True)
    else:
        st.image(processed_image_bytes, use_container_width=True)

if st.button(
    "開始辨識",
    type="primary",
    use_container_width=True,
    disabled=(
        uploaded_image is None
        or st.session_state.get("recognition_in_progress", False)
    ),
):
    # 執行期間設定鎖定狀態，避免同一張圖片被重複送入 OCR。
    st.session_state["recognition_in_progress"] = True
    try:
        with st.spinner("辨識中..."):
            recognition_result = recognize_image(processed_image_bytes)

        # OCR 服務回報處理錯誤時，統一顯示使用者可理解的錯誤訊息。
        recognition_result["failed"] = bool(
            not recognition_result["is_mock"]
            and recognition_result["message"]
        )
        st.session_state["recognition_result"] = recognition_result
    except Exception:
        st.session_state["recognition_result"] = {
            "text": "",
            "is_mock": False,
            "message": "",
            "failed": True,
        }
    finally:
        st.session_state["recognition_in_progress"] = False

st.subheader("OCR原始文字")
recognition_result = st.session_state.get("recognition_result")
if recognition_result is None:
    st.markdown(
        "<div class='result-box'>上傳照片並點擊「開始辨識」後，原始與清理後文字會顯示在這裡。</div>",
        unsafe_allow_html=True,
    )
else:
    if recognition_result.get("failed", False):
        st.error("辨識失敗，請重新嘗試。")
    elif recognition_result["message"]:
        st.warning(recognition_result["message"])

    raw_text = recognition_result["text"]
    if not raw_text and not recognition_result.get("failed", False):
        st.info("目前無法清楚辨識文字，請重新拍攝或上傳更清楚的照片。")

    st.code(raw_text or "（沒有原始辨識文字）", language=None)

    st.subheader("清理後文字")
    cleaned_text = clean_ocr_text(raw_text)
    st.code(cleaned_text or "（沒有可顯示的清理後文字）", language=None)

    medication_info = extract_medication_info(cleaned_text)
    medication_name = html.escape(medication_info["藥品名稱"])
    detail_fields = [
        (field_name, html.escape(value))
        for field_name, value in medication_info.items()
        if field_name != "藥品名稱"
    ]
    detail_cards = "".join(
        "<div class='medication-field'>"
        f"<div class='medication-label'>{field_name}</div>"
        f"<div class='medication-value'>{value}</div>"
        "</div>"
        for field_name, value in detail_fields
    )
    st.markdown(
        "<section class='medication-card'>"
        "<h2 class='medication-card-title'>💊 藥品資訊</h2>"
        "<div class='medication-name'>"
        "<div class='medication-label'>藥品名稱</div>"
        f"<div class='medication-value'>{medication_name}</div>"
        "</div>"
        f"<div class='medication-grid'>{detail_cards}</div>"
        "</section>",
        unsafe_allow_html=True,
    )

st.caption("用藥請依照醫師或藥師指示；本工具目前不提供診斷或用藥建議。")
