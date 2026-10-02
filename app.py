import streamlit as st
import librosa
import numpy as np
from fpdf import FPDF

st.set_page_config(page_title="JM CHORD FINDER", layout="centered")
st.title("🎸 JM CHORD FINDER")

NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

if 'chords' not in st.session_state:
    st.session_state.chords = None
    st.session_state.key = None
    st.session_state.tempo = None
    st.session_state.file_path = None

def analyze_file(path):
    y, sr = librosa.load(path, duration=90)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    key = NOTES[np.argmax(np.mean(chroma, axis=1))]
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    beat_chroma = librosa.util.sync(chroma, beats, aggregate=np.median)

    major = np.array([1,0,0,0,1,0,0,1,0,0,0,0])
    minor = np.array([1,0,0,1,0,0,0,0])

    chords = []
    for i in range(beat_chroma.shape[1]):
        v = beat_chroma[:, i]
        best_score = -1
        best_chord = "C"
        for root in range(12):
            for suffix, templ in [('', major), ('m', minor)]:
                t = np.roll(templ, root)
                score = np.dot(v, t)
                if score > best_score:
                    best_score = score
                    best_chord = NOTES[root] + suffix
        chords.append(best_chord)

    # Alis duplicate
    clean = [chords[0]]
    for c in chords[1:]:
        if c!= clean[-1]:
            clean.append(c)
    return key, clean, int(tempo)

# --- UPLOAD - SAVE AGAD SA MEMORY ---
uploaded = st.file_uploader("Upload MP3/MP4:", type=["mp3","mp4","wav","m4a"])

if uploaded is not None:
    # SAVE PERMANENT PARA DI MAWALA
    with open("saved_song.mp3", "wb") as f:
        f.write(uploaded.getbuffer())
    st.session_state.file_path = "saved_song.mp3"
    st.session_state.filename = uploaded.name
    st.success(f"Loaded: {uploaded.name}")
    st.audio("saved_song.mp3")

transpose_to = st.selectbox("Transpose to:", NOTES, index=4)

# --- BUTTON LAGING KITA - HINDI NAWAWALA ---
if st.button("🔍 ANALYZE CHORDS NOW", type="primary", use_container_width=True):
    if st.session_state.file_path is None:
        st.error("Upload ka muna ng MP3 sa taas!")
    else:
        with st.spinner("Analyzing... 10 sec..."):
            try:
                key, chords, tempo = analyze_file(st.session_state.file_path)

                # Transpose
                steps = (NOTES.index(transpose_to) - NOTES.index(key)) % 12
                def trans(ch):
                    r = ch[:2] if len(ch)>1 and ch[1]=='#' else ch[0]
                    suf = ch[len(r):]
                    if r not in NOTES: return ch
                    return NOTES[(NOTES.index(r)+steps)%12] + suf

                transposed = [trans(c) for c in chords]

                st.session_state.chords = transposed
                st.session_state.key = key
                st.session_state.tempo = tempo
                st.session_state.target = transpose_to

            except Exception as e:
                st.error(f"Error sa analyze: {e}")

# --- RESULT - LAGING KITA PAG MAY CHORDS NA ---
if st.session_state.chords is not None:
    st.divider()
    st.balloons()
    st.success(f"Original Key: {st.session_state.key} | Target: {st.session_state.target} | BPM: {st.session_state.tempo}")
    st.subheader("🎸 Chords:")
    st.code(" - ".join(st.session_state.chords[:100]), language="text")

    with st.expander("Listahan ng Chords"):
        for i, c in enumerate(st.session_state.chords[:100]):
            st.write(f"{i+1}. {c}")

    # PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0,10, f"JM CHORD FINDER - {st.session_state.filename}", ln=True, align='C')
    pdf.cell(0,10, f"Key {st.session_state.key} -> {st.session_state.target} | BPM {st.session_state.tempo}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", '', 10)
    for i in range(0, len(st.session_state.chords), 10):
        pdf.cell(0,7, " - ".join(st.session_state.chords[i:i+10]), ln=True)
    pdf.output("chords.pdf")

    with open("chords.pdf", "rb") as f:
        st.download_button("📄 DOWNLOAD PDF", f, file_name=f"Chords_{st.session_state.filename}.pdf", use_container_width=True, type="primary")
