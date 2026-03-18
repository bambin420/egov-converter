import streamlit as st
import zipfile
import io
import re
from fpdf import FPDF
import os

st.set_page_config(page_title="e-Gov公文書変換ツール", layout="centered")
st.title("e-Gov公文書変換ツール (完全物理回避モード)")

def get_string_safely(byte_content):
    # 日本語エンコードを総当たり
    for enc in ['cp932', 'utf-8', 'shift_jis', 'utf-16']:
        try:
            return byte_content.decode(enc)
        except:
            continue
    # 最終手段：エラー文字を置換して強制デコード
    return byte_content.decode('utf-8', errors='replace')

def process_zip_recursive(zip_bytes, all_contents):
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            # 【重要】z.namelist() や z.read(name) を使わず、z.infolist() を使う
            for info in z.infolist():
                try:
                    with z.open(info) as f:
                        content = f.read()
                    
                    # 中身がZIPなら再帰処理
                    if info.filename.lower().endswith('.zip'):
                        process_zip_recursive(content, all_contents)
                    # 中身がXMLなら保存（ファイル名は表示用にデコードを試みるが、失敗しても進む）
                    elif info.filename.lower().endswith('.xml'):
                        display_name = get_string_safely(info.filename.encode('cp437')) # ZIPの標準エンコードからの復元試行
                        all_contents.append((display_name, content))
                except:
                    continue
    except:
        pass

uploaded_file = st.file_uploader("ZIPファイルをアップロードしてください")

if uploaded_file is not None:
    input_data = uploaded_file.read()
    all_xml_list = [] # (ファイル名, バイナリ内容) のリスト
    
    process_zip_recursive(input_data, all_xml_list)
    
    if not all_xml_list:
        st.warning("XMLファイルが見つかりませんでした。")
    else:
        st.info(f"{len(all_xml_list)} 個のファイルを処理します。")
        
        for i, (xml_name, raw_data) in enumerate(all_xml_list):
            try:
                # 文字列化（ここでエラーは絶対に出さない）
                raw_text = get_string_safely(raw_data)
                
                # タグ除去
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
                    pdf.multi_cell(0, 8, txt=clean_text.encode('ascii', 'ignore').decode('ascii'))
                
                pdf_output = pdf.output()
                
                # 表示用の安全なファイル名
                safe_name = os.path.basename(xml_name) if xml_name else f"document_{i}.xml"
                
                st.success(f"変換完了: {safe_name}")
                st.download_button(
                    label=f"📥 PDFを保存 ({safe_name})",
                    data=pdf_output,
                    file_name=safe_name.replace('.xml', '.pdf'),
                    mime="application/pdf",
                    key=f"dl_{i}"
                )
            except Exception as e:
                st.error(f"変換エラーが発生しました: {str(e)}")
