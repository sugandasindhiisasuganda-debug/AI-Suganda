import os
import streamlit as st
from pypdf import PdfReader
from google import genai
from dotenv import load_dotenv

# Load API Key dari file .env jika ada
load_dotenv()
default_api_key = os.getenv("GEMINI_API_KEY", "").strip()

# Konfigurasi Halaman
st.set_page_config(page_title="TanyaMateri AI", page_icon="📚", layout="centered")
st.title("📚 TanyaMateri AI")
st.caption("Upload file PDF materi kuliah atau jurnal, lalu tanyakan apa saja!")

# Fungsi ekstrak teks dari PDF
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for i, page in enumerate(reader.pages):
        content = page.extract_text()
        if content:
            text += f"\n--- Halaman {i+1} ---\n{content}"
    return text

# Sidebar untuk Pengaturan & Upload File
with st.sidebar:
    st.header("🔑 Pengaturan API")
    api_key = st.text_input(
        "Gemini API Key",
        value=default_api_key,
        type="password",
        placeholder="AIzaSy...",
        help="Dapatkan API key gratis di Google AI Studio"
    )
    
    st.divider()
    
    st.header("📄 Upload Dokumen")
    uploaded_file = st.file_uploader("Pilih file PDF", type=["pdf"])
    
    if uploaded_file:
        # Hanya ekstrak ulang jika file baru di-upload
        if st.session_state.get("current_file") != uploaded_file.name:
            with st.spinner("Membaca isi PDF..."):
                extracted = extract_text_from_pdf(uploaded_file)
                if not extracted.strip():
                    st.error("PDF ini kosong atau berupa gambar/scan yang tidak bisa dibaca teksnya.")
                else:
                    st.session_state["pdf_text"] = extracted
                    st.session_state["current_file"] = uploaded_file.name
                    st.session_state["messages"] = []  # Reset chat saat ganti PDF
                    st.success(f"Berhasil memuat: {uploaded_file.name}")
        else:
            st.success(f"Aktif: {uploaded_file.name}")

    # Tombol bersihkan chat
    if st.session_state.get("messages"):
        if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True):
            st.session_state["messages"] = []
            st.rerun()

# Inisialisasi riwayat chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Tampilkan riwayat chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input pertanyaan user
if prompt := st.chat_input("Tanyakan sesuatu tentang isi PDF..."):
    if not api_key:
        st.error("⚠️ Masukkan Gemini API Key terlebih dahulu di menu sebelah kiri!")
    elif "pdf_text" not in st.session_state:
        st.warning("⚠️ Upload file PDF dulu di menu sebelah kiri ya!")
    else:
        # Tampilkan pesan user
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Proses jawaban dari Gemini dengan Auto-Fallback jika server sibuk
        with st.chat_message("assistant"):
            with st.spinner("Mencari jawaban di dokumen..."):
                client = genai.Client(api_key=api_key.strip())
                full_prompt = f"""
                Kamu adalah asisten akademik yang membantu mahasiswa memahami dokumen.
                Jawab pertanyaan berikut HANYA berdasarkan teks dokumen yang diberikan. 
                Sebutkan nomor halamannya jika relevan. Jika jawaban tidak ada di dokumen, katakan tidak ditemukan.

                Isi Dokumen:
                {st.session_state['pdf_text'][:100000]} 

                Pertanyaan: {prompt}
                """
                
                # Daftar model berurutan dari utama ke cadangan
                models_to_try = ["gemini-3.8-flash", "gemini-3.8-flash-lite", "gemini-3.5-flash"]
                response = None
                last_error = None

                for model_name in models_to_try:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=full_prompt,
                        )
                        break  # Berhasil, keluar dari loop
                    except Exception as e:
                        last_error = e
                        continue  # Coba model cadangan berikutnya

                if response:
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                else:
                    st.error(f"Server AI sedang sibuk, coba kirim ulang beberapa detik lagi.\n\nDetail error: {last_error}")