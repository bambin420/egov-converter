import streamlit as st
import zipfile
import tempfile
import os
from lxml import etree
import pdfkit
import shutil  # ← これが必要

# サーバー(Linux)と自分のPC(Windows)の両方で動くための設定
path_wkhtmltopdf = shutil.which("wkhtmltopdf")
if not path_wkhtmltopdf:
    # 自分のPCで動かす時の予備パス
    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'

config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

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
                            # --- 超強力な文字化け対策 ---
                            # 1. XMLとXSLをテキストとして強制的に読み込む（矛盾を無視）
                            def read_file_safely(path):
                                try:
                                    with open(path, 'r', encoding='shift_jis') as f:
                                        return f.read().encode('utf-8')
                                except:
                                    with open(path, 'r', encoding='utf-8') as f:
                                        return f.read().encode('utf-8')

                            xml_data = read_file_safely(xml_path)
                            xsl_data = read_file_safely(os.path.join(xml_dir, xsl_files[0]))

                            # 2. 解析
                            parser = etree.XMLParser(recover=True)
                            xml_dom = etree.fromstring(xml_data, parser)
                            xsl_dom = etree.fromstring(xsl_data, parser)
                            
                            transform = etree.XSLT(xsl_dom)
                            result_html = transform(xml_dom)
                            
                            # 3. HTML内の文字コード宣言をPDF用に調整
                            html_str = str(result_html).replace('Shift_JIS', 'UTF-8').replace('shift_jis', 'UTF-8')
                            
                            options = {
                                'encoding': "UTF-8",
                                'quiet': ''
                            }
                            
                            pdf_bytes = pdfkit.from_string(html_str, False, configuration=config, options=options)
                            
                            st.success(f"変換完了: {os.path.basename(xml_path)}")
                            st.download_button(
                                label=f"📥 PDFダウンロード: {os.path.basename(xml_path).replace('.xml', '.pdf')}",
                                data=pdf_bytes,
                                file_name=f"{os.path.basename(xml_path).replace('.xml', '.pdf')}",
                                mime="application/pdf"
                            )
                        except Exception as e:
                            st.error(f"変換エラー ({os.path.basename(xml_path)}): {str(e)}")
            else:
                st.warning("XMLファイルが見つかりませんでした。")