import streamlit as st
import zipfile
import tempfile
import os
import re

# 最小限のライブラリ
try:
    from fpdf import FPDF
except ImportError:
    st.error("fpdf2 が必要です。requirements.txt を確認してください。")

st.set_page_config(page_title="e-Gov公文書変換ツール", layout="centered")
st.title("e-Gov公文書変換ツール (超・回避モード)")

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

def force_read_text(path):
    """
    どんな文字コードでも絶対にエラーを出さずに読み込む「力技」関数
    """
    # 1. まず「バイナリ(rb)」で開く。これで文字コード問題は一旦スルーされる。
    with open(path, 'rb') as f:
        data = f.read()
    
    # 2. 日本語で多い形式を順に試す
    for enc in ['cp932', 'utf-8', 'shift_jis']:
        try:
            return data.decode(enc)
        except:
            continue
    
    # 3. 全てダメなら「エラー文字を ? に置き換えて」強制的に読み込む
    # これで 'utf-8' codec can't decode エラーは 100% 発生しなくなります。
    return data.decode('utf-8', errors='replace')

uploaded_file = st.file_uploader("ZIPファイルをアップロードしてください")

if uploaded_file is not None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        # アップロードされたファイルを一時保存
        zip_path = os.path.join(tmp_dir, "input.zip")
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 全解凍
        extract_all_zips(tmp_dir)
        
        # XMLファイルを探す
        xml_files = []
        for root, _, files in os.walk(tmp_dir):
            for file in files:
                if file.lower().endswith('.xml'):
                    xml_files.append(os.path.join(root, file))
        
        if xml_files:
            st.info(f"{len(xml_files)} 個のファイルを処理中...")
            
            for xml_path in xml_files:
                filename = os.path.basename(xml_path)
                try:
                    # テキストを「エラー無視」で取得
                    raw_content = force_read_text(xml_path)
                    
                    # XMLタグを消して中身の文字だけにする
                    clean_text = re.sub(r'<[^>]+?>', ' ', raw_content)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

                    # PDF作成
                    pdf = FPDF()
                    pdf.add_page()
                    
                    # IPAフォントの確認
                    font_path = "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf"
                    if os.path.exists(font_path):
                        pdf.add_font('JP', '', font_path)
                        pdf.set_font('JP', size=10)
                        pdf.multi_cell(0, 8, txt=clean_text)
                    else:
                        st.warning("日本語フォントがシステムに見つかりません。")
                        pdf.set_font('Courier', size=10)
                        # ASCII以外を消して出力（文字化け回避）
                        safe_ascii = clean_text.encode('ascii', 'ignore').decode('ascii')
                        pdf.multi_cell(0, 8, txt=safe_ascii)
                    
                    pdf_bytes = pdf.output()
                    
                    st.success(f"変換完了: {filename}")
                    st.download_button(
                        label=f"📥 PDFを保存: {filename.replace('.xml', '.pdf')}",
                        data=pdf_bytes,
                        file_name=filename.replace('.xml', '.pdf'),
                        mime="application/pdf",
                        key=f"dl_{filename}"
                    )
                except Exception as e:
                    st.error(f"エラー ({filename}): {str(e)}")
        else:
            st.warning("XMLファイルが見つかりません。")
