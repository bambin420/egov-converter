import streamlit as st
import zipfile
import tempfile
import os
import io
import re

# ライブラリの読み込み
try:
    from lxml import etree
    from fpdf import FPDF
except ImportError:
    st.error("必要なライブラリが不足しています。")

st.set_page_config(page_title="e-Gov公文書変換ツール", layout="centered")
st.title("e-Gov公文書変換ツール")

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

# 【新・解決策】XMLを解析せず、正規表現で強引にテキストを抽出する
def get_clean_text_from_xml(path):
    encodings = ['cp932', 'utf-8', 'shift_jis', 'utf-16']
    raw_text = ""
    
    # 1. まずファイルを安全にデコードして「ただの文字列」にする
    with open(path, 'rb') as f:
        data = f.read()
        for enc in encodings:
            try:
                raw_text = data.decode(enc)
                break
            except:
                continue
    
    if not raw_text:
        raw_text = data.decode('utf-8', errors='ignore')

    # 2. XMLタグ (<...>) をすべて除去して、中身の文字だけにする
    # e-GovのXSL変換を通さず、直接テキストを抽出することでエラーを回避
    clean_text = re.sub(r'<[^>]+?>', ' ', raw_text)
    # 余計な空白や改行を整理
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

uploaded_file = st.file_uploader("ZIPファイルをアップロードしてください")

if uploaded_file is not None:
    if not uploaded_file.name.lower().endswith('.zip'):
        st.error("ZIPファイルをアップロードしてください。")
    else:
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, "initial.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            extract_all_zips(tmp_dir)
            
            all_files = []
            for root, dirs, files in os.walk(tmp_dir):
                for file in files:
                    all_files.append(os.path.join(root, file))
            
            xml_list = [f for f in all_files if f.endswith('.xml')]
            
            if xml_list:
                st.info(f"{len(xml_list)} 個のファイルを検出しました。")
                
                for xml_path in xml_list:
                    try:
                        # 解析ライブラリを使わず、直接テキストを取り出す
                        content = get_clean_text_from_xml(xml_path)

                        if not content:
                            st.warning(f"内容が空です: {os.path.basename(xml_path)}")
                            continue

                        # PDF生成
                        pdf = FPDF()
                        pdf.add_page()
                        
                        font_path = "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf"
                        
                        if os.path.exists(font_path):
                            pdf.add_font('Japanese', '', font_path)
                            pdf.set_font('Japanese', size=10)
                            pdf.multi_cell(0, 8, txt=content)
                        else:
                            pdf.set_font('Helvetica', size=10)
                            pdf.multi_cell(0, 8, txt=content.encode('ascii', 'ignore').decode('ascii'))
                        
                        pdf_bytes = pdf.output()
                        
                        st.success(f"変換完了: {os.path.basename(xml_path)}")
                        st.download_button(
                            label=f"📥 PDFダウンロード: {os.path.basename(xml_path).replace('.xml', '.pdf')}",
                            data=pdf_bytes,
                            file_name=f"{os.path.basename(xml_path).replace('.xml', '.pdf')}",
                            mime="application/pdf",
                            key="btn_" + os.path.basename(xml_path)
                        )
                    except Exception as e:
                        st.error(f"エラー ({os.path.basename(xml_path)}): {str(e)}")
            else:
                st.warning("XMLファイルが見つかりませんでした。")
