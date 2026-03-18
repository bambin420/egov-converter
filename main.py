import streamlit as st
import zipfile
import io
import re
from fpdf import FPDF
import os

st.set_page_config(page_title="e-Gov公文書変換ツール", layout="centered")
st.title("e-Gov公文書変換ツール (究極・回避モード)")

# 文字コードを完全に無視して、何が何でも文字列にする関数
def get_string_safely(byte_content):
    for enc in ['cp932', 'utf-8', 'shift_jis', 'utf-16']:
        try:
            return byte_content.decode(enc)
        except:
            continue
    # 最終手段：読めない文字を「?」に置き換えて強制デコード
    return byte_content.decode('utf-8', errors='replace')

uploaded_file = st.file_uploader("ZIPファイルをアップロードしてください")

if uploaded_file is not None:
    # ZIPファイルをメモリ上で直接開く（ディスクへの書き込みを避ける）
    try:
        with zipfile.ZipFile(io.BytesIO(uploaded_file.read())) as z:
            # ZIP内の全ファイルをチェック
            file_names = z.namelist()
            xml_files = [f for f in file_names if f.lower().endswith('.xml')]
            
            if not xml_files:
                st.warning("ZIP内にXMLファイルが見つかりません。")
            else:
                st.info(f"{len(xml_files)} 個のXMLファイルを検出。変換を開始します。")
                
                for xml_name in xml_files:
                    try:
                        # ファイルをバイナリとして直接読み込む（ここが重要）
                        with z.open(xml_name) as f:
                            raw_data = f.read()
                        
                        # 強引にテキスト化
                        raw_text = get_string_safely(raw_data)
                        
                        # XMLタグを除去して中身だけにする
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
                            safe_ascii = clean_text.encode('ascii', 'ignore').decode('ascii')
                            pdf.multi_cell(0, 8, txt=safe_ascii)
                        
                        pdf_output = pdf.output()
                        
                        st.success(f"変換完了: {xml_name}")
                        st.download_button(
                            label=f"📥 PDFを保存: {os.path.basename(xml_name).replace('.xml', '.pdf')}",
                            data=pdf_output,
                            file_name=os.path.basename(xml_name).replace('.xml', '.pdf'),
                            mime="application/pdf",
                            key=f"dl_{xml_name}"
                        )
                    except Exception as e:
                        st.error(f"ファイル処理エラー ({xml_name}): {str(e)}")
    except Exception as e:
        st.error(f"ZIP解析エラー: {str(e)}")
