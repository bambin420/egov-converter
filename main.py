import streamlit as st
import zipfile
import io
import re
from fpdf import FPDF
import os

st.set_page_config(page_title="e-Gov公文書変換ツール", layout="centered")
st.title("e-Gov公文書変換ツール (全ZIP探索・回避モード)")

# 文字コードを無視して文字列にする
def get_string_safely(byte_content):
    for enc in ['cp932', 'utf-8', 'shift_jis', 'utf-16']:
        try:
            return byte_content.decode(enc)
        except:
            continue
    return byte_content.decode('utf-8', errors='replace')

# ZIPの中を再帰的に探索してXMLを抜き出す関数
def process_zip_recursive(zip_bytes, all_xml_data):
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for name in z.namelist():
                # ZIPの中にさらにZIPがあったら、再帰的に中身を見る
                if name.lower().endswith('.zip'):
                    with z.open(name) as f:
                        process_zip_recursive(f.read(), all_xml_data)
                # XMLを見つけたら、内容を保存
                elif name.lower().endswith('.xml'):
                    with z.open(name) as f:
                        all_xml_data[name] = f.read()
    except:
        pass

uploaded_file = st.file_uploader("ZIPファイルをアップロードしてください")

if uploaded_file is not None:
    all_xml_data = {}
    # 全てのZIPファイルを掘り下げてXMLを探す
    process_zip_recursive(uploaded_file.read(), all_xml_data)
    
    if not all_xml_data:
        st.warning("ZIPファイル内にXMLファイル（.xml）が見つかりませんでした。")
    else:
        st.info(f"{len(all_xml_data)} 個のXMLファイルを検出しました。変換します。")
        
        for xml_name, raw_data in all_xml_data.items():
            try:
                # 文字コードエラーを完全に無視してテキスト化
                raw_text = get_string_safely(raw_data)
                
                # タグを除去
                clean_text = re.sub(r'<[^>]+?>', ' ', raw_text)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()

                # PDF生成
                pdf = FPDF()
                pdf.add_page()
                
                font_path = "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf"
                if os.path.exists(font_path):
                    pdf.add_font('JP', '', font_path)
                    pdf.set_font('JP', size=10)
                    pdf.multi_cell(0, 8, txt=clean_text)
                else:
                    pdf.set_font('Courier', size=10)
                    safe_ascii = clean_text.encode('ascii', 'ignore').decode('ascii')
                    pdf.multi_cell(0, 8, txt=safe_ascii)
                
                pdf_output = pdf.output()
                
                st.success(f"変換完了: {os.path.basename(xml_name)}")
                st.download_button(
                    label=f"📥 PDFを保存: {os.path.basename(xml_name).replace('.xml', '.pdf')}",
                    data=pdf_output,
                    file_name=os.path.basename(xml_name).replace('.xml', '.pdf'),
                    mime="application/pdf",
                    key=f"dl_{xml_name}"
                )
            except Exception as e:
                st.error(f"ファイル変換中に問題が発生しました ({xml_name}): {str(e)}")
