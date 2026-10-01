import streamlit as st
import librosa
import yt_dlp
import os
import tempfile
import numpy as np
from fpdf import FPDF

MAX_DURATION = 600
KEYS = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

def transpose_chord(chord, semi):
    root = chord[:2] if len(chord)>=2 and chord[:2] in KEYS else chord[0]
    if root not in KEYS:
        return chord
    new_root = KEYS[(KEYS.index(root) + semi) % 12]
    return chord.replace(root, new_root, 1)

st.set_page_config(page_title="JM Church Full", page_icon="🎸", layout="centered")
st.title("🎸 JM CHURCH - COMPLETE FINAL")
st.caption("10 Mins | Transpose | PDF | Lyrics + Chords | YouTube Bypass")

url = st.text_input("YouTube Link:")
uploaded_file = st.file_uploader("OR Upload MP3/M4A dito pag binlock ni YouTube (backup):", type=['mp3','m4a','wav','mp4'])
semi = st.slider("Transpose semitones", -6, 6, 0)
lyrics_input = st.text_area("Paste Lyrics (optional para malagyan ng chords sa taas):", height=130, placeholder="Pupurihin Ka sa awit...\nOh Diyos na makapangyarihan...")

def get_audio_youtube(youtube_url):
    tmpdir = tempfile.mkdtemp()
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio',
        'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
        'quiet': True,
        'noplaylist': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'nocheckcertificate': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        return ydl.prepare_filename(info), info.get('title', 'Worship Song')

if st.button("🔍 ANALYZE COMPLETE", type="primary", use_container_width=True):
    path = None
    title = ""
    try:
        if uploaded_file:
            tmp_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
            with open(tmp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            path, title = tmp_path, uploaded_file.name
        elif url:
            with st.status("Downloading from YouTube (bypass mode)...", expanded=False):
                path, title = get_audio_youtube(url)
        else:
            st.warning("Paste YouTube link OR upload MP3 muna sir!")
            st.stop()

        with st.status(f"Analyzing {title} - 10 mins...", expanded=True) as s:
            s.write("🎵 Loading audio 22k mono...")
            y, sr = librosa.load(path, sr=22050, mono=True, duration=MAX_DURATION)
            dur = librosa.get_duration(y=y, sr=sr)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            orig_key = KEYS[int(np.argmax(np.sum(chroma, axis=1)))]
            new_key = KEYS[(KEYS.index(orig_key) + semi) % 12]
            rms = librosa.feature.rms(y=y)[0]
            chords = []
            for i in range(0, chroma.shape[1], 86): # ~4 sec per chord
                c = KEYS[int(np.argmax(np.mean(chroma[:, i:i+86], axis=1)))]
                chords.append(transpose_chord(c, semi))
            s.update(label=f"Done: {title}", state="complete")

        st.success(f"✅ {title} | Orig: {orig_key} -> New: {new_key} ({semi:+d}) | {float(tempo):.0f} BPM | {dur/60:.1f} min")

        st.divider()
        st.subheader(f"🎤 Lyrics with Chords - Key {new_key}")
        st.caption("Chords nasa ibabaw ng lyrics kung saan papasok")

        report = []
        if lyrics_input:
            lines = lyrics_input.split('\n')
            idx = 0
            for line in lines:
                if line.strip() == "":
                    st.write("")
                    report.append(("", ""))
                    continue
                c1 = chords[idx % len(chords)] if chords else new_key
                c2 = chords[(idx+1) % len(chords)] if len(chords) > 1 else new_key
                idx += 2
                st.markdown(f"<pre style='color:#FF6B35;font-weight:bold;margin:0'>{c1} {c2}</pre>", unsafe_allow_html=True)
                st.markdown(f"<pre style='margin-top:0;margin-bottom:12px'>{line}</pre>", unsafe_allow_html=True)
                report.append((f"{c1} {c2}", line))
        else:
            st.info("Tip: Paste lyrics sa taas para ma-align ko chords sa mismong salita. Eto muna chords sequence:")
            seq = " - ".join(chords[:30])
            st.code(seq)
            report = [("Chords", seq)]

        st.divider()
        if st.button("📄 Generate PDF - Lyrics + Chords"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, f"JM CHURCH - {title}", ln=True, align='C')
            pdf.set_font("Arial", "", 11)
            pdf.cell(0, 8, f"Key {orig_key} -> {new_key} ({semi:+d}) | BPM {float(tempo):.0f} | {dur/60:.1f} min", ln=True)
            pdf.ln(5)
            pdf.set_font("Courier", "", 11)
            for ch, lyr in report:
                if ch == "":
                    pdf.ln(4)
                    continue
                pdf.set_font("Courier", "B", 11)
                pdf.cell(0, 6, ch, ln=True)
                pdf.set_font("Courier", "", 11)
                pdf.cell(0, 6, lyr, ln=True)
                pdf.ln(2)
            out = os.path.join(tempfile.gettempdir(), "jm_final.pdf")
            pdf.output(out)
            with open(out, "rb") as f:
                st.download_button("⬇️ DOWNLOAD PDF", f, file_name=f"{title}_{new_key}_lyrics.pdf", use_container_width=True)

        try:
            os.remove(path)
        except:
            pass

    except Exception as e:
        st.error(f"Error: {e}")
        st.info("Tip sir: Pag YouTube ayaw pa rin (bot error), download mo lang yung song as MP3 tapos upload mo gamit yung Upload box sa taas. Gagana pa rin lahat!")
