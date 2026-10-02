import streamlit as st
import librosa
import numpy as np
import os

# Para sa PDF
try:
    from fpdf import FPDF
except:
    from fpdf2 import FPDF

st.set_page_config(page_title="JM - Chord Finder", layout="centered")
st.title("🎸 JM - Chord Finder")

# NOTES
NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
# Chord templates - Major, Minor, 7
TEMPLATES = {
    '': [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0], # Major
    'm': [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0], # Minor
    '7': [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0], # 7
    'm7': [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0], # m7
}

def get_chord_name(chroma_vector):
    chroma_vector = chroma_vector / (np.linalg.norm(chroma_vector) + 1e-9)
    best_chord = "C"
    max_score = -1
    for root in range(12):
        for suffix, template in TEMPLATES.items():
            template = np.array(template, dtype=float)
            # i-roll para sa root note
            rolled = np.roll(template, root)
            rolled = rolled / (np.linalg.norm(rolled) + 1e-9)
            score = np.dot(chroma_vector, rolled)
            if score > max_score:
                max_score = score
                best_chord = f"{NOTES[root]}{suffix}"
    return best_chord

# UI
uploaded = st.file_uploader("Upload MP3 / WAV / M4A:", type=["mp3","wav","m4a","mp4"])
target_key = st.selectbox("Transpose to Key:", NOTES, index=4) # Default E

if st.button("🔍 ANALYZE CHORDS NOW", type="primary", use_container_width=True):
    if uploaded is None:
        st.error("❌ Mag-upload ka muna ng file sa taas!")
    else:
        # Save temp file
        with open("temp_audio", "wb") as f:
            f.write(uploaded.getbuffer())

        st.success(f"✅ File OK: {uploaded.name}")
        st.audio(uploaded)

        try:
            with st.spinner("Analyzing... mga 15-20 seconds..."):
                # Load 90 sec lang para mabilis
                y, sr = librosa.load("temp_audio", duration=90)

                # Chroma
                chroma = librosa.feature.chroma_cqt(y=y, sr=sr)

                # Key detection - average chroma
                key_index = int(np.argmax(np.mean(chroma, axis=1)))
                original_key = NOTES[key_index]

                # Beat tracking para mas accurate chords
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                # Sync chroma to beats
                beat_chroma = librosa.util.sync(chroma, beats, aggregate=np.median)

                chords = []
                for i in range(beat_chroma.shape[1]):
                    chords.append(get_chord_name(beat_chroma[:, i]))

                # Alisin sunod-sunod na parehas
                clean_chords = [chords[0]] if chords else []
                for c in chords[1:]:
                    if c!= clean_chords[-1]:
                        clean_chords.append(c)

                # Transpose
                steps = (NOTES.index(target_key) - NOTES.index(original_key)) % 12

                def transpose_chord(chord_name):
                    # Kunin root
                    if len(chord_name) > 1 and chord_name[1] == '#':
                        root = chord_name[:2]
                        suffix = chord_name[2:]
                    else:
                        root = chord_name[0]
                        suffix = chord_name[1:]

                    if root in NOTES:
                        new_root = NOTES[(NOTES.index(root) + steps) % 12]
                        return new_root + suffix
                    return chord_name

                transposed = [transpose_chord(c) for c in clean_chords]

                st.balloons()
                st.success(f"🎉 TAPOS! Original Key: {original_key} | Target: {target_key} | BPM: {int(tempo)}")

                # Display
                st.subheader("Chords:")
                st.code(" - ".join(transposed[:100]), language="text")

                # PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, f"JM Church - {uploaded.name}", ln=True, align="C")
                pdf.set_font("Arial", "", 11)
                pdf.cell(0, 8, f"Original Key: {original_key} -> {target_key} | BPM: {int(tempo)}", ln=True, align="C")
                pdf.ln(5)

                # Lagay chords 10 per line
                pdf.set_font("Arial", "", 10)
                for i in range(0, len(transposed), 10):
                    line = " - ".join(transposed[i:i+10])
                    pdf.cell(0, 7, line, ln=True)

                pdf.output("chords.pdf")
                with open("chords.pdf", "rb") as f:
                    st.download_button(
                        "📄 DOWNLOAD PDF NG CHORDS",
                        f,
                        file_name=f"{uploaded.name}_CHORDS_{target_key}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

        except Exception as e:
            st.error(f"Error sa analysis: {e}")
            st.info("Try mo ulit o ibang MP3 file.")
