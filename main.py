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
    st.error("必要なライブラリが不足しています。requirements.txtを確認してください。")

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
                    xml_dir = os.path.dirname(xml_path)
                    xsl_files = [f for f in os.listdir(xml_dir) if f.endswith('.xsl')]
                    
                    if xsl_files:
                        try:
                            # 文字コードを自動判別して読み込む関数
                            def read_file_safely(path):
                                # e-Govで使われやすい順に試行
                                encodings = ['cp932', 'utf-8', 'shift_jis', 'utf-16']
                                for enc in encodings:
                                    try:
                                        with open(path, 'rb') as f:
                                            raw_data = f.read()
                                            return raw_data.decode(enc).encode('utf-8')
                                    except:
                                        continue
                                raise ValueError("ファイルの文字コードを判別できませんでした。")

                            xml_data = read_file_safely(xml_path)
                            xsl_data = read_file_safely(os.path.join(xml_dir, xsl_files[0]))

                            # 解析
                            parser = etree.XMLParser(recover=True, encoding='utf-8')
                            xml_dom = etree.fromstring(xml_data, parser)
                            xsl_dom = etree.fromstring(xsl_data, parser)
                            
                            transform = etree.XSLT(xsl_dom)
                            result_html = transform(xml_dom)
                            
                            # テキストのクリーニング
                            html_str = str(result_html)
                            clean_text = re.sub('<[^<]+?>', '', html_str)
                            clean_text = clean_text.replace('\xa0', ' ').replace('\u200b', '')

                            # PDF生成
                            pdf = FPDF()
                            pdf.add_page()
                            
                            # LinuxサーバーのIPAexフォントのパス（packages.txtで入れたもの）
                            font_path = "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf"
                            
                            if os.path.exists
