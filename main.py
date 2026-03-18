import streamlit as st
import zipfile
import io
import re
from fpdf import FPDF
import os

st.set_page_config(page_title="e-Gov公文書変換ツール", layout="centered")
st.title("e-Gov公文書変換ツール (バイナリ直結モード)")

def get_string_safely(byte_content):
    """
    バイトデータを、エラーを無視して文字列に変換する
    """
    for enc in ['cp932', 'utf-8', 'shift_jis', 'utf-16']:
        try:
            return byte_content.decode(enc)
        except:
            continue
    # 最終手段：エラー文字を「?」に置換して強制デコード
    return byte_content.decode('utf-8', errors='replace')

def process_zip_recursive(zip_bytes, all_xml_contents):
    """
    ZIPをバイナリとして扱い、ファイル名のエラーを回避して中身を抽出する
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            # namelist() ではなく infolist() を使い、名前の自動デコードを避ける
            for info in z.infolist():
                try:
                    # 中身をバイナリとして読み出す
                    with z.open(info) as f:
                        content = f.read()
                    
                    # 拡張子チェック（バイナリ比較で判定）
                    fname = info.filename.lower()
                    
                    if fname.endswith('.zip'):
                        process_zip_recursive(content, all_xml_contents)
                    elif fname.endswith('.xml'):
                        # 表示用の名前はエラー無視で作成
                        display_name = get_string_safely(info.filename.encode('cp437', errors='replace'))
                        all_xml_contents.append((display_name, content))
                except:
                    continue
    except:
        pass

uploaded_file = st.file_uploader("ZIPファイルをアップロードしてください")

if uploaded_file is not None:
    # アップロードされた全データをメモリに読み込む
    input_zip_bytes = uploaded_file.read()
    all_xml_list = []
    
    # 全てのZIPを掘り下げてXML（のバイナリ）を探す
    process_zip_recursive(input_zip_bytes, all_xml_list)
    
    if not all_xml_list:
        st.warning("XMLファイルが見つかりませんでした。")
    else:
        st.info(f"{len(all_xml_list)} 個のファイルを検出。PDFに変換します。")
        
        for i, (xml_name, raw_data) in enumerate(all_xml_list):
            try:
                # 中身をテキスト化（エラー無視設定）
                raw_text = get_string_safely(raw_data)
                
                # XMLタグを正規表現で除去
                clean_text = re.sub(r'<[^>]+?>', ' ', raw_text)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()

                # PDF生成
                pdf = FPDF()
                pdf.add_page()
                
                # フォントの確認
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
                
                # 表示用の安全なファイル名
                safe_label = os.path.basename(xml_name)
                
                st.success(f"変換完了: {safe_label}")
                st.download_button(
                    label=f"📥 PDFを保存: {safe_label.replace('.xml', '.pdf')}",
                    data=pdf_output,
                    file_name=safe_label.replace('.xml', '.pdf'),
                    mime="application/pdf",
                    key=f"dl_{i}"
                )
            except Exception as e:
                st.error(f"変換エラーが発生しました: {str(e)}")
