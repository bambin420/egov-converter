import streamlit as st
import zipfile
import tempfile
import os
import io
import requests  # 追加

# ライブラリの読み込み
try:
    from lxml import etree
    from fpdf import FPDF
except ImportError:
    st.error("必要なライブラリが不足しています。requirements.txtを確認してください。")

st.set_page_config(page_title="e-Gov公文書変換ツール", layout="centered")
st.title("e-Gov公文書変換ツール")

# フォントをダウンロードする関数
@st.cache_data
def download_font():
    url = "https://github.com/google/fonts/raw/main/ofl/ipaexgothic/IPAexGothic.ttf"
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    return None

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
        # フォントの準備
        font_data = download_font()
        
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
                
                # 一時的にフォントファイルを保存
                font_path = os.path.join(tmp_dir, "ipaexg.ttf")
                if font_data:
                    with open(font_path, "wb") as f:
                        f.write(font_data)

                for xml_path in xml_list:
                    xml_dir = os.path.dirname(xml_path)
                    xsl_files = [f for f in os.listdir(xml_dir) if f.endswith('.xsl')]
                    
                    if xsl_files:
                        try:
                            def read_file_safely(path):
                                try:
                                    with open(path, 'r', encoding='shift_jis') as f:
                                        return f.read().encode('utf-8')
                                except:
                                    with open(path, 'r', encoding='utf-8') as f:
                                        return f.read().encode('utf-8')

                            xml_data = read_file_safely(xml_path)
                            xsl_data = read_file_safely(os.path.join(xml_dir, xsl_files[0]))

                            parser = etree.XMLParser(recover=True)
                            xml_dom = etree.fromstring(xml_data, parser)
                            xsl_dom = etree.fromstring(xsl_data, parser)
                            
                            transform = etree.XSLT(xsl_dom)
                            result_html = transform(xml_dom)
                            
                            html_str = str(result_html)
                            import re
                            clean_text = re.sub('<[^<]+?>', '', html_str)

                            # PDF生成
                            pdf = FPDF()
                            pdf.add_page()
                            
                            if font_data:
                                pdf.add_font('IPAexGothic', '', font_path)
                                pdf.set_font('IPAexGothic', size=10)
                            else:
                                pdf.set_font('Arial', size=10)
                            
                            pdf.multi_cell(0, 8, txt=clean_text)
                            pdf_bytes = pdf.output()
                            
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
