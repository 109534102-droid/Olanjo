"""藥品照片 OCR 服務。

優先使用本機 Tesseract（繁體中文 + 英文）。若環境沒有可用的 OCR 引擎，
回傳清楚標記的模擬資料，讓首頁流程仍可示範；模擬文字不代表照片內容。
"""

from io import BytesIO
import re


def clean_ocr_text(text):
    """整理 OCR 文字格式，不推測或補上辨識不到的內容。"""
    if not text:
        return ""

    # 將不同作業系統的換行格式統一，之後逐行整理文字。
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned_lines = []

    for line in normalized_text.split("\n"):
        # 把每行內連續的空白字元（例如空格、Tab、全形空白）縮成一格。
        line = re.sub(r"[^\S\n]+", " ", line).strip()

        # 將 MG、Mg、mG 等大小寫寫法統一為 mg，不改變數值或其他文字。
        line = re.sub(r"(?<![A-Za-z])mg(?![A-Za-z])", "mg", line, flags=re.IGNORECASE)

        # 不保留空白行；相鄰有效行最後只會以一個換行符號分隔。
        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def extract_medication_info(cleaned_text):
    """只從清理後 OCR 文字擷取可直接找到的藥品資訊，不自行推測。"""
    fields = {
        "藥品名稱": "未辨識到",
        "劑量": "未辨識到",
        "每次用量": "未辨識到",
        "每日次數": "未辨識到",
        "服用時間": "未辨識到",
        "注意事項": "未辨識到",
        "有效期限": "未辨識到",
    }
    if not cleaned_text:
        return fields

    lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]
    text = "\n".join(lines)

    # 優先讀取明確標示的藥名；若 OCR 只辨識到「英文藥名 + 劑量」，則取劑量前的名稱。
    name_label = re.search(
        r"(?:藥品名稱|药品名称|藥名|药名|品名)\s*[:：]?\s*([^\n]+)",
        text,
        flags=re.IGNORECASE,
    )
    if name_label:
        fields["藥品名稱"] = name_label.group(1).strip()
    else:
        name_with_strength = re.search(
            r"^([A-Za-z][A-Za-z-]*(?:\s+[A-Za-z][A-Za-z-]*)*)\s+"
            r"\d+(?:\.\d+)?\s*(?:mcg|μg|ug|mg|g|ml|l|iu)\b",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if name_with_strength:
            fields["藥品名稱"] = name_with_strength.group(1).title()

    # 擷取明確出現的數值與單位，僅將單位格式整理成一致寫法。
    strength = re.search(
        r"(?<![A-Za-z0-9])([0-9]+(?:\.[0-9]+)?)\s*(mcg|μg|ug|mg|g|ml|l|iu)\b",
        text,
        flags=re.IGNORECASE,
    )
    if strength:
        unit = strength.group(2).lower()
        unit = {"μg": "mcg", "ug": "mcg", "ml": "mL", "l": "L", "iu": "IU"}.get(
            unit, unit
        )
        fields["劑量"] = f"{strength.group(1)} {unit}"

    # 每次用量只接受文字中明確標出的數量與藥品單位。
    per_dose = re.search(
        r"(?:每次(?:用量|服用)?|單次用量)\s*[:：]?\s*"
        r"([0-9]+(?:\.[0-9]+)?\s*(?:顆|粒|錠|片|包|毫升|mL|ml|滴|噴))",
        text,
        flags=re.IGNORECASE,
    )
    if per_dose:
        fields["每次用量"] = re.sub(r"\s+", "", per_dose.group(1))

    # 每日次數保留 OCR 原本辨識到的數字或中文數字，不自行換算。
    daily_frequency = re.search(
        r"(?:每日|每天|一天)\s*([0-9一二三四五六七八九十兩两]+)\s*次",
        text,
    )
    if daily_frequency:
        fields["每日次數"] = f"{daily_frequency.group(1)}次"

    # 服用時間只從常見的明確時段詞彙中擷取，不依照藥品名稱推斷。
    time_terms = (
        "早餐前", "早餐後", "午餐前", "午餐後", "晚餐前", "晚餐後",
        "飯前", "飯後", "餐前", "餐後", "睡前", "空腹", "早上", "中午", "晚上",
    )
    for term in time_terms:
        if term in text:
            fields["服用時間"] = term
            break

    # 注意事項需有明確標籤，才擷取標籤後的文字。
    precaution = re.search(
        r"(?:注意事項|注意事项|注意|備註|备注|警語|警告)\s*[:：]\s*([^\n]+)",
        text,
    )
    if precaution:
        fields["注意事項"] = precaution.group(1).strip()

    # 有效期限需有明確效期標籤，並且後面出現可辨識的年月日格式。
    expiration = re.search(
        r"(?:有效期限|有效期|效期|EXP(?:IRY)?\.?\s*[:：]?)\s*[:：]?\s*"
        r"((?:20\d{2}[年/.-]\d{1,2}(?:[月/.-]\d{1,2}日?)?|"
        r"\d{1,2}[/-]20\d{2}))",
        text,
        flags=re.IGNORECASE,
    )
    if expiration:
        fields["有效期限"] = expiration.group(1)

    return fields


def preprocess_image(image_bytes):
    """使用 OpenCV 預處理圖片，回傳 PNG 格式的處理結果。"""
    import cv2
    import numpy as np

    # 從上傳的二進位資料解碼原始圖片，OpenCV 會以 BGR 色彩順序讀取。
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    original_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if original_image is None:
        raise ValueError("無法讀取圖片，請重新上傳 JPG、JPEG 或 PNG 檔案。")

    # 將圖片最長邊縮小至 1600 像素以加快處理，並維持原始長寬比例。
    height, width = original_image.shape[:2]
    longest_side = max(height, width)
    if longest_side > 1600:
        scale = 1600 / longest_side
        new_width = int(width * scale)
        new_height = int(height * scale)
        original_image = cv2.resize(
            original_image,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA,
        )

    # 轉成灰階，減少顏色資訊對藥品文字辨識的干擾。
    grayscale_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

    # 使用非局部平均降噪，降低拍攝時常見的細小雜訊。
    denoised_image = cv2.fastNlMeansDenoising(
        grayscale_image,
        None,
        h=10,
        templateWindowSize=7,
        searchWindowSize=21,
    )

    # 使用 CLAHE 局部對比增強，讓光線不均時的文字更清楚。
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_image = clahe.apply(denoised_image)

    # 使用 Otsu 自動門檻將圖片轉為黑白，凸顯文字與背景差異。
    _, threshold_image = cv2.threshold(
        enhanced_image,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    # 編碼成 PNG 位元組，供網頁預覽及後續 OCR 使用。
    success, encoded_image = cv2.imencode(".png", threshold_image)
    if not success:
        raise ValueError("無法產生處理後圖片。")
    return encoded_image.tobytes()


MOCK_TEXT = (
    "[模擬流程資料]\n"
    "這是 OCR 流程展示用文字，並非從上傳圖片辨識而來。"
)


def _mock_result(reason):
    return {
        "text": MOCK_TEXT,
        "is_mock": True,
        "message": reason,
    }


def recognize_image(image_bytes):
    """辨識圖片中的繁體中文、英文與數字，回傳文字和執行狀態。"""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return _mock_result(
            "目前環境尚未安裝 OCR 套件，以下為模擬資料，並非照片辨識結果。"
        )

    try:
        available_languages = pytesseract.get_languages(config="")
        required_languages = {"chi_tra", "eng"}
        if not required_languages.issubset(available_languages):
            return _mock_result(
                "找不到 Tesseract 繁體中文或英文語言資料，以下為模擬資料，並非照片辨識結果。"
            )

        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        text = pytesseract.image_to_string(
            image,
            lang="chi_tra+eng",
            config="--psm 6",
        ).strip()
        return {"text": text, "is_mock": False, "message": ""}
    except pytesseract.TesseractNotFoundError:
        return _mock_result(
            "目前環境找不到 Tesseract OCR 引擎，以下為模擬資料，並非照片辨識結果。"
        )
    except pytesseract.TesseractError as error:
        return {
            "text": "",
            "is_mock": False,
            "message": f"Tesseract OCR 執行失敗：{error}",
        }
    except Exception as error:
        return {
            "text": "",
            "is_mock": False,
            "message": f"圖片處理失敗：{error}",
        }
