import streamlit as st
import zipfile
import io
import re
from fpdf import FPDF
import os

st.set_page_config(page_title="e-Gov公文書変換ツール", layout="centered")
st.title("e-Gov公文書変換ツール (環境依存エラー回避版)")

def get_string_safely(byte_content):
    """
    バイトデータを、エラーを無視して文字列に変換する
    """
    if not byte_content:
        return ""
    
    # 候補となるエンコードを順に試す
    for enc in ['cp932', 'utf-8', 'shift_jis', 'utf-16']:
        try:
            return byte_content.decode(enc)
        except:
            continue
    
    # 全て失敗した場合は、エラー文字を「?」に置換して強制デコード（これでエラーは100%出ない）
    return byte_content.decode('utf-8', errors='replace')

def process_zip_recursive(zip_bytes, all_xml_contents):
    """
    ZIPをバイナリとして扱い、ファイル名による自爆を避けて中身を抽出する
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            # infolist() を使い、名前の自動デコードが走る前にポインタを掴む
            for info in z.infolist():
                try:
                    # ファイル名をバイナリのまま取得し、安全に文字列化する
                    # ZIP内のファイル名はCP437で記録されていることが多いため一度戻す
                    try:
                        raw_filename = info.filename.encode('cp437')
                    except:
                        raw_filename = info.filename.encode('utf-8', errors='replace')
                    
                    display_name = get_string_safely(raw_filename)
                    
                    # 中身をバイナリとして読み出す
                    with z.open(info) as f:
                        content = f.read()
                    
                    if display_name.lower().endswith('.zip'):
                        process_zip_recursive(content, all_xml_contents)
                    elif display_name.lower().endswith('.xml'):
                        all_xml_contents.append((display_name, content))
                except:
                    continue
    except:
        pass

uploaded_file = st.file_uploader("ZIPファイルをアップロードしてください")

if uploaded_file is not None:
    # アップロード直後にバイナリとして取得
    input_data = uploaded_file.read()
    all_xml_list = []
    
    process_zip_recursive(input_data, all_xml_list)
    
    if not all_xml_list:
        st.warning("XMLファイルが見かかりませんでした。")
    else:
        st.info(f"{len(all_xml_list)} 個のファイルを検出しました。")
        
        for i, (xml_name, raw_data) in enumerate(all_xml_list):
            try:
                # 中身をテキスト化（OSの設定を無視して手動デコード）
                raw_text = get_string_safely(raw_data)
                
                # XMLタグを除去
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
                
                # 安全な表示名を作成
                safe_label = os.path.basename(xml_name)
                
                st.success(f"変換完了: {safe_label}")
                st.download_button(
                    label=f"📥 PDFを保存: {safe_label.replace('.xml', '.pdf')}",
                    data=pdf_output,
                    file_name=safe_label.replace('.xml', '.pdf'),
                    mime="application/pdf",
                    key=f"dl_{i}_{safe_label}"
                )
            except Exception as e:
                # 万が一エラーが出ても、どのステップで止まったか詳細を出す
                st.error(f"変換エラー ({xml_name}): {str(e)}")
