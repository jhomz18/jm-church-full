import streamlit as st
import librosa
import numpy as np
from fpdf import FPDF

st.set_page_config(page_title="JM Chord Finder", layout="centered")
st.title("🎸 JM Chord Finder")

NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def detect_chord(vec):
    major = np.array([1,0,0,0,1,0,0,1,0,0,0,0])
    minor = np.array([1,0,0,1,0,0,0,0])
    vec = vec / (np.linalg.norm(vec)+1e-6)
    best = "C"; best_s = -1
    for r in range(12):
        for suf, t in [("", major), ("m", minor)]:
            tt = np.roll(t, r)
            tt = tt / (np.linalg.norm(tt)+1e-6)
            s = np.dot(vec, tt)
            if s > best_s:
                best_s = s; best = NOTES[r]+suf
    return best

# Para hindi mawala
if 'chords' not in st.session_state:
    st.session_state.chords = None

uploaded = st.file_uploader("Upload MP3/WAV:", type=["mp3","wav","m4a","mp4"])
key = st.selectbox("Transpose to Key:", NOTES, index=4)

if uploaded:
    st.audio(uploaded)
    if st.button("🔍 ANALYZE CHORDS NOW", type="primary", use_container_width=True):
        with open(f"temp_{uploaded.name}", "wb") as f:
            f.write(uploaded.getbuffer())

        with st.spinner("Analyzing, wag mo i-close... 15 secs..."):
            try:
                y, sr = librosa.load(f"temp_{uploaded.name}", duration=60)
                chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
                step = max(1, chroma.shape[1] // 30)
                chords = []
                for i in range(0, chroma.shape[1], step):
                    avg = np.mean(chroma[:, i:i+step], axis=1)
                    chords.append(detect_chord(avg))

                final = [chords[0]]
                for c in chords[1:]:
                    if c!= final[-1]:
                        final.append(c)

                st.session_state.chords = final
                st.session_state.filename = uploaded.name
            except Exception as e:
                st.error(f"Error: {e}")

# DISPLAY - nasa labas ng button para hindi mawala
if st.session_state.chords:
    st.balloons()
    st.success(f"✅ {len(st.session_state.chords)} chords found!")
    st.subheader("Chords Result:")
    st.code(" - ".join(st.session_state.chords), language="text")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",14)
    pdf.cell(0,10,f"Chords - {st.session_state.filename} - Key {key}", ln=True, align="C")
    pdf.set_font("Arial","",12)
    pdf.ln(5)
    for i in range(0, len(st.session_state.chords), 8):
        pdf.cell(0,10," - ".join(st.session_state.chords[i:i+8]), ln=True)
    pdf.output("chords.pdf")
    with open("chords.pdf","rb") as f:
        st.download_button("📄 DOWNLOAD PDF", f, file_name=f"{st.session_state.filename}_chords.pdf", mime="application/pdf", use_container_width=True)

    if st.button("Clear Result"):
        st.session_state.chords = None
        st.rerun()
