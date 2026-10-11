# AI看得懂藥

以 Python 和 Streamlit 製作的簡易藥品照片上傳 Web App。介面使用繁體中文，可透過電腦或手機瀏覽器使用。

目前版本提供首頁、JPG/JPEG/PNG 圖片上傳、相機拍攝、OpenCV 影像預處理、OCR 文字辨識與規則式藥品資訊整理。預處理包含縮放、灰階、降噪、局部對比增強與 Otsu 二值化。OCR 支援繁體中文與英文（數字由英文模型辨識）。藥品欄位只從 OCR 文字擷取，未出現的資料會標示「未辨識到」，不會自行推測。手機瀏覽器可從相簿選擇照片，也可使用相機拍攝；正式部署時請使用 HTTPS，以符合瀏覽器相機權限要求。

## 環境需求

- Python 3.9 或更新版本
- pip

## 安裝與啟動

在專案資料夾開啟終端機，執行：

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Streamlit 啟動後會顯示本機網址，通常是 `http://localhost:8501`。在同一個 Wi-Fi 網路以手機測試時，可使用啟動訊息顯示的 Network URL 開啟。

## OCR 引擎安裝

除了 Python 套件，真實 OCR 也需要安裝 Tesseract OCR，並準備 `chi_tra`（繁體中文）和 `eng`（英文）語言資料。若執行環境缺少引擎或語言資料，App 會清楚標示並顯示模擬流程資料；該資料不是從使用者照片辨識而來。安裝 Tesseract 後，請確認它已加入系統 PATH。

## 部署到 Streamlit Community Cloud

此專案已提供 `packages.txt`，部署時會安裝 Tesseract 與繁體中文、英文語言資料。

1. 將 `app.py`、`ocr_service.py`、`requirements.txt`、`packages.txt` 和 `README.md` 放進 GitHub 儲存庫。
2. 在 Streamlit Community Cloud 登入並連結 GitHub。
3. 建立 App，選擇該儲存庫與分支，主程式填 `app.py`，再部署。
4. 部署完成後，Community Cloud 會提供一個 `streamlit.app` 網址。

Community Cloud 會從 GitHub 儲存庫安裝 Python 與系統套件；`packages.txt` 是安裝 Tesseract 等 Linux 套件的清單。部署設定方式請參閱 [Streamlit 官方部署文件](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) 與 [套件依賴文件](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)。

要從既有的 ChatGPT Site 連到這個 App，需由該 Site 的擁有者或編輯者在 Sites 編輯器加入部署後的網址。

## 專案檔案

- `app.py`：Streamlit 首頁與照片上傳介面
- `ocr_service.py`：OCR 辨識與無引擎時的模擬流程
- `requirements.txt`：Python 套件清單
- `packages.txt`：Community Cloud 所需的 Tesseract 與 OCR 語言套件

## 使用提醒

OCR 結果可能不完整或有誤，請核對藥品原包裝，並依照醫師或藥師的指示用藥；App 不提供診斷或用藥建議。
