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

# 【解決策】文字コードをバイナリレベルで制御し、lxmlのエラーを回避する関数
def safe_parse_xml(path):
    encodings = ['cp932', 'utf-8', 'shift_jis', 'utf-16']
    with open(path, 'rb') as f:
        raw_data = f.read()
        
    for enc in encodings:
        try:
            # 1. データを指定のエンコードでデコード
            text = raw_data.decode(enc)
            # 2. XML宣言内のencoding属性が矛盾を起こさないよう、UTF-8バイト列として再変換
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            return etree.fromstring(text.encode('utf-8'), parser)
        except:
            continue
    
    # 最終手段：不明な文字を無視してUTF-8で強制読み込み
    parser = etree.XMLParser(recover=True, encoding='utf-8')
    return etree.fromstring(raw_data.decode('utf-8', errors='ignore').encode('utf-8'), parser)

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
                            # XMLとXSLを安全に解析
                            xml_dom = safe_parse_xml(xml_path)
                            xsl_dom = safe_parse_xml(os.path.join(xml_dir, xsl_files[0]))
                            
                            transform = etree.XSLT(xsl_dom)
                            result_html = transform(xml_dom)
                            
                            # テキスト抽出とクリーニング
                            html_str = str(result_html)
                            clean_text = re.sub('<[^<]+?>', '', html_str)
                            clean_text = clean_text.replace('\xa0', ' ').replace('\u200b', '')

                            # PDF生成
                            pdf = FPDF()
                            pdf.add_page()
                            
                            # LinuxサーバーのIPAexフォントの標準パス
                            font_path = "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf"
                            
                            if os.path.exists(font_path):
                                pdf.add_font('Japanese', '', font_path)
                                pdf.set_font('Japanese', size=10)
                                pdf.multi_cell(0, 8, txt=clean_text)
                            else:
                                st.warning("フォントが見つかりません。標準フォントで代用します。")
                                pdf.set_font('Helvetica', size=10)
                                pdf.multi_cell(0, 8, txt=clean_text.encode('ascii', 'ignore').decode('ascii'))
                            
                            pdf_bytes = pdf.output()
                            
                            st.success(f"変換完了: {os.path.basename(xml_path)}")
                            
                            # 【修正済み】閉じ括弧を確実に追加
                            st.download_button(
                                label=f"📥 PDFダウンロード: {os.path.basename(xml_path).replace('.xml', '.pdf')}",
                                data=pdf_bytes,
                                file_name=f"{os.path.basename(xml_path).replace('.xml', '.pdf')}",
                                mime="application/pdf",
                                key="btn_" + os.path.basename(xml_path)
                            )
                        except Exception as e:
                            st.error(f"変換エラー ({os.path.basename(xml_path)}): {str(e)}")
            else:
                st.warning("XMLファイルが見つかりませんでした。")
