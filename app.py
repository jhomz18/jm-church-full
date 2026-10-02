import streamlit as st
import librosa
import numpy as np
from fpdf import FPDF

st.set_page_config(page_title="JM Chord Finder", layout="centered")
st.title("🎸 JM Chord Finder")

NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def detect_chord(chroma_vec):
    majors = {
        'C': [1,0,0,0,1,0,0,1,0,0,0,0],
        'C#': [1,0,0,1,0,0,0,1,0,0,0,0],
    }
    # simple template: Major and Minor only
    major_t = np.array([1,0,0,0,1,0,0,1,0,0,0,0])
    minor_t = np.array([1,0,0,1,0,0,0,1,0,0,0,0])
    best = "C"
    best_score = -1
    chroma_vec = chroma_vec / (np.linalg.norm(chroma_vec)+1e-6)
    for root in range(12):
        for suf, templ in [("", major_t), ("m", minor_t)]:
            t = np.roll(templ, root)
            t = t / (np.linalg.norm(t)+1e-6)
            score = np.dot(chroma_vec, t)
            if score > best_score:
                best_score = score
                best = NOTES[root] + suf
    return best

uploaded = st.file_uploader("Upload MP3/WAV:", type=["mp3","wav","m4a","mp4"])
key = st.selectbox("Transpose to Key:", NOTES, index=4)

if uploaded and st.button("🔍 ANALYZE CHORDS NOW", type="primary", use_container_width=True):
    temp_path = f"temp_{uploaded.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded.getbuffer())

    st.success(f"File OK: {uploaded.name}")
    st.audio(uploaded)

    try:
        with st.spinner("Analyzing..."):
            y, sr = librosa.load(temp_path, duration=60)
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)

            # every 2 sec = 1 chord para sure
            num_chords = 25
            step = max(1, chroma.shape[1] // num_chords)
            chords = []
            for i in range(0, chroma.shape[1], step):
                avg = np.mean(chroma[:, i:i+step], axis=1)
                chords.append(detect_chord(avg))

            # remove duplicate sunod-sunod
            final = [chords[0]]
            for c in chords[1:]:
                if c!= final[-1]:
                    final.append(c)

            st.balloons()
            st.success(f"✅ {len(final)} chords found!")
            st.code(" - ".join(final), language="text")

            # PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial","B",14)
            pdf.cell(0,10,f"{uploaded.name}", ln=True, align="C")
            pdf.set_font("Arial","",11)
            pdf.ln(5)
            for i in range(0, len(final), 10):
                pdf.cell(0,8," - ".join(final[i:i+10]), ln=True)
            pdf.output("chords.pdf")
            with open("chords.pdf","rb") as f:
                st.download_button("📄 DOWNLOAD PDF", f, file_name="chords.pdf", mime="application/pdf", use_container_width=True)

    except Exception as e:
        st.error(f"Error sa analysis: {e}")
