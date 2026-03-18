import streamlit as st
import zipfile
import io
import re
from fpdf import FPDF
import os

st.set_page_config(page_title="e-Gov公文書変換ツール", layout="centered")
st.title("e-Gov公文書変換ツール (究極・回避モード)")

# 【解決の要】バイトデータを直接受け取り、エラーを無視して文字列にする
def get_string_safely(byte_content):
    # e-Govで使われやすいエンコードを順に試す
    for enc in ['cp932', 'utf-8', 'shift_jis', 'utf-16']:
        try:
            return byte_content.decode(enc)
        except:
            continue
    # 最終手段：読めない文字を「?」に置き換えて強制デコード
    # これにより 'utf-8' codec can't decode エラーは 100% 回避されます
    return byte_content.decode('utf-8', errors='replace')

# ZIPの中身を「バイナリ」として再帰的に探索する関数
def process_zip_recursive(zip_bytes, all_xml_data):
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for name in z.namelist():
                # ZIPの中にさらにZIPがあったら、再帰的に中身をバイナリとして読む
                if name.lower().endswith('.zip'):
                    # .read() を使うことで、ファイルとして開かずに「データ」として取得
                    process_zip_recursive(z.read(name), all_xml_data)
                
                # XMLを見つけたら、内容をバイナリデータとして保存
                elif name.lower().endswith('.xml'):
                    all_xml_data[name] = z.read(name)
    except:
        pass

uploaded_file = st.file_uploader("ZIPファイルをアップロードしてください")

if uploaded_file is not None:
    # ユーザーがアップロードした全データをメモリに読み込む
    input_zip_bytes = uploaded_file.read()
    all_xml_data = {}
    
    # 全てのZIPを掘り下げてXML（のバイナリ）を探す
    process_zip_recursive(input_zip_bytes, all_xml_data)
    
    if not all_xml_data:
        st.warning("ZIPファイル内にXMLファイル（.xml）が見つかりませんでした。")
    else:
        st.info(f"{len(all_xml_data)} 個のXMLファイルを検出。PDFに変換します。")
        
        for xml_name, raw_data in all_xml_data.items():
            try:
                # ここで初めて「バイナリ」を「テキスト」に変換（エラー無視設定）
                raw_text = get_string_safely(raw_data)
                
                # XMLタグを正規表現で除去（lxmlなどの厳しいライブラリは使いません）
                clean_text = re.sub(r'<[^>]+?>', ' ', raw_text)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()

                # PDF生成
                pdf = FPDF()
                pdf.add_page()
                
                # IPAフォントの確認（packages.txtで入れたもの）
                font_path = "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf"
                if os.path.exists(font_path):
                    pdf.add_font('JP', '', font_path)
                    pdf.set_font('JP', size=10)
                    pdf.multi_cell(0, 8, txt=clean_text)
                else:
                    st.warning(f"フォント未検出。英数字のみ出力します。")
                    pdf.set_font('Courier', size=10)
                    # ASCII以外を捨てて出力（文字化け回避）
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
