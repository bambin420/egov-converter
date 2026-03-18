import streamlit as st
import zipfile
import tempfile
import os
import re

# 最小限のライブラリ
try:
    from fpdf import FPDF
except ImportError:
    st.error("fpdf2 が必要です。requirements.txt を確認してください。")

st.set_page_config(page_title="e-Gov公文書変換ツール", layout="centered")
st.title("e-Gov公文書変換ツール (緊急回避モード)")

def extract_all_zips(target_dir):
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith('.zip'):
                zip_path = os.path.join(root, file)
                extract_dir = os.path.join(root, file.replace('.zip', ''))
                if not os.path.exists(extract_dir):
                    try:
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)
                        extract_all_zips(extract_dir)
                    except:
                        continue

def force_read_text(path):
    """
    どんなに文字コードが狂っていても、絶対にエラーを出さずに文字列を返す関数
    """
    try:
        # まずはバイナリで読み込む
        with open(path, 'rb') as f:
            raw = f.read()
        
        # Shift_JIS(CP932)を最優先で試す
        for enc in ['cp932', 'utf-8', 'shift_jis']:
            try:
                return raw.decode(enc)
            except:
                continue
        
        # 全て失敗した場合は、UTF-8で読み込みつつ、読めない文字を「?」に置き換える（これでエラーは100%出ない）
        return raw.decode('utf-8', errors='replace')
    except Exception as e:
        return f"File Read Error: {str(e)}"

uploaded_file = st.file_uploader("ZIPファイルをアップロードしてください")

if uploaded_file is not None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        # アップロードされたファイルを保存
        zip_path = os.path.join(tmp_dir, "input.zip")
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 解凍
        extract_all_zips(tmp_dir)
        
        # XMLファイルを探す
        xml_files = []
        for root, _, files in os.walk(tmp_dir):
            for file in files:
                if file.lower().endswith('.xml'):
                    xml_files.append(os.path.join(root, file))
        
        if xml_files:
            st.info(f"{len(xml_files)} 個のファイルを処理します。")
            
            for xml_path in xml_files:
                filename = os.path.basename(xml_path)
                try:
                    # テキストを強制取得
                    raw_content = force_read_text(xml_path)
                    
                    # XMLタグを正規表現で完全に消し去る (lxmlは使いません)
                    clean_text = re.sub(r'<[^>]+?>', ' ', raw_content)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

                    # PDF作成
                    pdf = FPDF()
                    pdf.add_page()
                    
                    # IPAフォントの確認
                    font_path = "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf"
                    if os.path.exists(font_path):
                        pdf.add_font('JP', '', font_path)
                        pdf.set_font('JP', size=10)
                        pdf.multi_cell(0, 8, txt=clean_text)
                    else:
                        st.warning("日本語フォントがシステムに見つかりません。")
                        pdf.set_font('Courier', size=10)
                        # 日本語が含まれるとエラーになるので、ASCIIのみに絞る
                        safe_ascii = clean_text.encode('ascii', 'ignore').decode('ascii')
                        pdf.multi_cell(0, 8, txt=safe_ascii)
                    
                    pdf_bytes = pdf.output()
                    
                    st.success(f"処理完了: {filename}")
                    st.download_button(
                        label=f"PDFを保存: {filename.replace('.xml', '.pdf')}",
                        data=pdf_bytes,
                        file_name=filename.replace('.xml', '.pdf'),
                        mime="application/pdf",
                        key=f"dl_{filename}"
                    )
                except Exception as e:
                    st.error(f"変換エラー ({filename}): {str(e)}")
        else:
            st.warning("XMLファイルが見つかりません。")
