import streamlit as st
import zipfile
import tempfile
import os
# 修正前：from fpdf import FPDF
# 修正後：以下のように書き換えてください

try:
    from fpdf import FPDF
except ImportError:
    # もしエラーが出たら別の名前で試みる（保険用）
    import fpdf
    FPDF = fpdf.FPDF
from fpdf import FPDF
import io

st.set_page_config(page_title="e-Gov公文書変換ツール", layout="centered")
st.title("e-Gov公文書変換ツール")

# PDF作成関数 (fpdf2を使用: 最も軽量で安定)
def create_pdf_from_text(html_text):
    pdf = FPDF()
    pdf.add_page()
    # 日本語フォントが必要な場合は別途設定が必要ですが、
    # まずは標準フォントでPDF化が通るか確認します
    pdf.set_font("Helvetica", size=12)
    
    # HTMLタグを除去してテキストのみを抽出
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_text, "html.parser")
    clean_text = soup.get_text()
    
    pdf.multi_cell(0, 10, clean_text)
    return pdf.output()

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

                            # PDF生成 (fpdf2を使用)
                            pdf_output = FPDF()
                            pdf_output.add_page()
                            # e-Govの日本語を表示するためフォント設定（後ほど調整可能）
                            pdf_output.set_font("Arial", size=12)
                            pdf_output.multi_cell(0, 10, txt=html_str[:2000]) # 簡易抽出
                            
                            pdf_bytes = pdf_output.output()
                            
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
                st.warning("XMLファイルが見てかりませんでした。")
