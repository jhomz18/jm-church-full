import streamlit as st
import librosa
import numpy as np
import os
from fpdf import FPDF

st.set_page_config(page_title="JM CHORD FINDER - MP3 ONLY", page_icon="🎸", layout="centered")
st.title("🎸 JM CHORD FINDER")
st.caption("MP3 / MP4 / WAV / M4A - Kahit anong kanta | Key + Chords + Transpose + PDF")

# --- CONFIG ---
NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
MAJOR_PROFILE = [6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88]
MINOR_PROFILE = [6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17]

def detect_key(chroma_mean):
    best_key = "C Major"
    best_score = -100
    for i in range(12):
        score = np.corrcoef(chroma_mean, np.roll(MAJOR_PROFILE, i))[0,1]
        if score > best_score:
            best_score = score
            best_key = f"{NOTES[i]} Major"
        score = np.corrcoef(chroma_mean, np.roll(MINOR_PROFILE, i))[0,1]
        if score > best_score:
            best_score = score
            best_key = f"{NOTES[i]} Minor"
    return best_key

def analyze_song(file_path):
    # Load 90 seconds para mabilis pero accurate
    y, sr = librosa.load(file_path, duration=90)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)

    key = detect_key(chroma_mean)

    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    beat_chroma = librosa.util.sync(chroma, beats, aggregate=np.median)

    chords = []
    for i in range(beat_chroma.shape[1]):
        root = np.argmax(beat_chroma[:, i])
        chords.append(NOTES[root])

    return key, chords, int(tempo), chroma

def transpose_chords(chords, original_root, target_root):
    try:
        steps = (NOTES.index(target_root) - NOTES.index(original_root)) % 12
        transposed = [NOTES[(NOTES.index(c) + steps) % 12] for c in chords]
        return transposed, steps
    except:
        return chords, 0

def create_pdf(original_key, target_key, chords, tempo, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"JM CHORD FINDER", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"File: {filename}", ln=True, align='C')
    pdf.cell(0, 8, f"Original Key: {original_key} | Target Key: {target_key} | BPM: {tempo}", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "CHORDS:", ln=True)
    pdf.set_font("Arial", '', 10)

    # Gawin 10 chords per line para maganda sa PDF
    for i in range(0, len(chords), 10):
        line = " - ".join(chords[i:i+10])
        pdf.cell(0, 7, line, ln=True)

    pdf.output("JM_Chords.pdf")
    return "JM_Chords.pdf"

# --- UI ---
uploaded = st.file_uploader("📁 Upload MP3 / MP4 / WAV / M4A - Kahit anong kanta:", type=["mp3","mp4","wav","m4a","flac","ogg"])

if uploaded is not None:
    # Save file
    ext = uploaded.name.split('.')[-1]
    save_path = f"song.{ext}"
    with open(save_path, "wb") as f:
        f.write(uploaded.getbuffer())

    st.success(f"Loaded: {uploaded.name} ({uploaded.size/1024/1024:.2f} MB)")
    st.audio(save_path)

    # Transpose Option
    col1, col2 = st.columns(2)
    with col1:
        target_key = st.selectbox("🎹 Transpose to Key:", NOTES, index=NOTES.index('G'))
    with col2:
        st.write("")
        st.write("")
        analyze_btn = st.button("🔍 ANALYZE NOW", type="primary", use_container_width=True)

    if analyze_btn:
        with st.spinner("Analyzing Key + Chords... 5-10 seconds"):
            try:
                original_key, chords, tempo, _ = analyze_song(save_path)
                orig_root = original_key.split()[0]

                transposed_chords, steps = transpose_chords(chords, orig_root, target_key)

                # SAVE TO SESSION FOR PDF
                st.session_state['orig_key'] = original_key
                st.session_state['target_key'] = f"{target_key} Major"
                st.session_state['chords'] = transposed_chords
                st.session_state['tempo'] = tempo
                st.session_state['filename'] = uploaded.name
                st.session_state['analyzed'] = True

            except Exception as e:
                st.error(f"Error analyzing: {e}")
                st.info("Try mo ibang file, baka corrupted o walang audio")

    # DISPLAY RESULT KUNG NA-ANALYZE NA
    if 'analyzed' in st.session_state and st.session_state['analyzed']:
        st.divider()
        st.balloons()
        st.subheader(f"✅ Original Key: {st.session_state['orig_key']}")
        st.subheader(f"🎯 Transposed to: {st.session_state['target_key']} ( +{ (NOTES.index(target_key) - NOTES.index(st.session_state['orig_key'].split()[0])) % 12 } semitones )")
        st.write(f"**BPM:** {st.session_state['tempo']}")

        st.subheader("🎸 Chords:")
        st.code(" | ".join(st.session_state['chords'][:100]), language="text")

        # List view
        with st.expander("View Chords List (Numbered)"):
            for i, c in enumerate(st.session_state['chords'][:100]):
                st.write(f"{i+1}. {c}")

        # PDF EXPORT
        pdf_path = create_pdf(
            st.session_state['orig_key'],
            st.session_state['target_key'],
            st.session_state['chords'],
            st.session_state['tempo'],
            st.session_state['filename']
        )
        with open(pdf_path, "rb") as f:
            st.download_button(
                "📄 DOWNLOAD PDF (Chords + Key)",
                f,
                file_name=f"Chords_{st.session_state['filename']}.pdf",
                use_container_width=True,
                type="primary"
            )

else:
    st.info("👆 Upload ka muna ng MP3 o MP4 sa taas. Kahit anong kanta, gagawan ng chords!")

st.divider()
st.caption("Pure MP3/MP4 Version | No YouTube = No Block | Works for all songs")
