import streamlit as st
import librosa
import numpy as np
from fpdf import FPDF

st.set_page_config(page_title="JM CHORD FINDER", layout="centered")
st.title("🎸 JM CHORD FINDER")

NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

TEMPLATES = {
    '': [1,0,0,0,1,0,0,1,0,0,0,0],
    'm': [1,0,0,1,0,0,0,0],
    '7': [1,0,0,0,1,0,0,1,0,0,1,0],
    'maj7': [1,0,0,0,1,0,0,1,0,0,0,1],
}

def get_chord(vec):
    vec = vec / (np.linalg.norm(vec) + 1e-10)
    best, score = "C", -1
    for r in range(12):
        for suf, t in TEMPLATES.items():
            tt = np.roll(t, r)
            if len(tt) < 12:
                full = np.zeros(12); full[:len(tt)] = tt; tt = full
            tt = tt / (np.linalg.norm(tt) + 1e-10)
            s = np.dot(vec, tt)
            if s > score:
                score = s; best = f"{NOTES[r]}{suf}"
    return best

# UPLOAD
uploaded = st.file_uploader("Upload MP3/MP4:", type=["mp3","mp4","wav","m4a"])
transpose_to = st.selectbox("Transpose to:", NOTES, index=4)

# BUTTON
if st.button("🔍 ANALYZE CHORDS NOW", type="primary", use_container_width=True):
    if uploaded is None:
        st.error("Upload ka muna ng MP3 sa taas!")
    else:
        # SAVE DIRETSO YUNG INUPLOAD MO - HINDI NA SESSION
        with open("temp.mp3", "wb") as f:
            f.write(uploaded.getbuffer())

        st.audio("temp.mp3")
        st.info(f"Analyzing {uploaded.name}...")

        with st.spinner("Analyzing 10-15 secs..."):
            y, sr = librosa.load("temp.mp3", duration=90)
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            key = NOTES[np.argmax(np.mean(chroma, axis=1))]
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            beat_chroma = librosa.util.sync(chroma, beats, aggregate=np.median)

            chords = [get_chord(beat_chroma[:, i]) for i in range(beat_chroma.shape[1])]
            clean = [chords[0]]
            for c in chords[1:]:
                if c!= clean[-1]:
                    clean.append(c)

            # Transpose
            steps = (NOTES.index(transpose_to) - NOTES.index(key)) % 12
            def tr(ch):
                r = ch[:2] if len(ch)>1 and ch[1]=='#' else ch[0]
                suf = ch[len(r):]
                return NOTES[(NOTES.index(r)+steps)%12] + suf if r in NOTES else ch
            transposed = [tr(c) for c in clean]

            st.balloons()
            st.success(f"Original Key: {key} | Target: {transpose_to} | BPM: {int(tempo)}")
            st.subheader("🎸 Chords:")
            st.code(" - ".join(transposed[:100]))

            # PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0,10, f"JM CHORD FINDER | {uploaded.name}", ln=True, align='C')
            pdf.cell(0,10, f"Key {key} -> {transpose_to} | BPM {int(tempo)}", ln=True, align='C')
            pdf.ln(5)
            pdf.set_font("Arial", '', 10)
            for i in range(0, len(transposed), 10):
                pdf.cell(0,7, " - ".join(transposed[i:i+10]), ln=True)
            pdf.output("chords.pdf")
            with open("chords.pdf", "rb") as f:
                st.download_button("📄 DOWNLOAD PDF", f, file_name=f"Chords_{uploaded.name}.pdf", use_container_width=True, type="primary")
