import streamlit as st
import librosa, numpy as np, os, re, yt_dlp
from fpdf import FPDF
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_YT_TRANS = True
except: HAS_YT_TRANS=False

# WHISPER FOR ALL MP3
@st.cache_resource
def load_whisper():
    try:
        import whisper
        # tiny = mabilis, base = mas accurate pero mabigat
        # sa Render free, tiny muna para di ma-OOM
        return whisper.load_model("tiny")
    except:
        return None

st.set_page_config(page_title="JM CHORD FINDER PRO", page_icon="🎸")
st.title("🎸 JM CHORD FINDER - PRO MAX")
st.caption("ANY MP3 = Auto Lyrics + Chords + Key + PDF | YouTube Bypass")

NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
MAJOR = [6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88]
MINOR = [6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17]

def detect_key(chroma_mean):
    best, score_best = "C Major", -1
    for i in range(12):
        s = np.corrcoef(chroma_mean, np.roll(MAJOR,i))[0,1]
        if s > score_best: score_best, best = s, f"{NOTES[i]} Major"
        s = np.corrcoef(chroma_mean, np.roll(MINOR,i))[0,1]
        if s > score_best: score_best, best = s, f"{NOTES[i]} Minor"
    return best

def get_yt_id(url):
    m = re.search(r"(?:v=|youtu\.be/)([^&?/]+)", url or "")
    return m.group(1) if m else None

def get_yt_lyrics(url):
    if not HAS_YT_TRANS: return None
    try:
        vid = get_yt_id(url)
        tr = YouTubeTranscriptApi.get_transcript(vid, languages=['en','tl','en-US'])
        return " ".join([x['text'] for x in tr])
    except: return None

def transcribe_mp3_whisper(file_path):
    model = load_whisper()
    if model is None:
        return None
    try:
        result = model.transcribe(file_path, language='en', fp16=False)
        return result['text']
    except Exception as e:
        st.warning(f"Whisper error: {e}")
        return None

def download_yt(url):
    for f in os.listdir('.'):
        if f.startswith('temp_audio'):
            try: os.remove(f)
            except: pass
    opts = {
        'format':'bestaudio/best',
        'outtmpl':'temp_audio.%(ext)s',
        'quiet':True, 'noplaylist':True,
        'extractor_args':{'youtube':{'player_client':['android','ios','web'],'skip':['hls','dash']}},
        'http_headers':{'User-Agent':'Mozilla/5.0 (Linux; Android 12;)'},
        'postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}],
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    for f in os.listdir('.'):
        if f.startswith('temp_audio') and f.endswith('.mp3'): return f
    return None

def analyze(file_path):
    y, sr = librosa.load(file_path, duration=90)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    key = detect_key(chroma_mean)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    beat_chroma = librosa.util.sync(chroma, beats, aggregate=np.median)
    chords = [NOTES[np.argmax(beat_chroma[:,i])] for i in range(beat_chroma.shape[1])]
    return key, chords, tempo

# --- UI ---
youtube_url = st.text_input("YouTube Link (optional):")
mp3_file = st.file_uploader("MP3 backup - KAHIT ANONG KANTA:", type=["mp3","wav","m4a"])
target_key = st.text_input("🎹 Target Key (Transpose to):", value="G")

if st.button("🔍 ANALYZE ALL MP3", type="primary", use_container_width=True):
    audio_path = None
    lyrics_text = None
    title = "JM Chords"

    if mp3_file is not None:
        with open("temp_upload.mp3","wb") as out:
            out.write(mp3_file.getbuffer())
        audio_path = "temp_upload.mp3"
        title = mp3_file.name
    elif youtube_url.strip()!="":
        with st.spinner("Downloading YouTube with bypass..."):
            audio_path = download_yt(youtube_url)
            lyrics_text = get_yt_lyrics(youtube_url)
            title = youtube_url
    else:
        st.warning("Upload MP3 or lagay YouTube link!")
        st.stop()

    if audio_path and os.path.exists(audio_path):
        st.audio(audio_path)

        # KEY + CHORDS
        with st.spinner("1/2 Detecting Key + Chords..."):
            key, chords, tempo = analyze(audio_path)

        # TRANSPOSE
        try:
            orig = key.split()[0]
            steps = (NOTES.index(target_key.upper()) - NOTES.index(orig)) % 12
            transposed = [NOTES[(NOTES.index(c)+steps)%12] for c in chords]
        except:
            transposed = chords
            steps = 0

        st.success(f"ORIGINAL: {key} | TARGET: {target_key} | BPM: {int(tempo)}")
        st.code(" - ".join(transposed[:80]))

        # LYRICS - OPTION B LOGIC
        with st.spinner("2/2 Transcribing Lyrics for ANY MP3 (Whisper AI - 20-40s)..."):
            if lyrics_text is None and mp3_file is not None:
                # ANY MP3 -> Whisper
                lyrics_text = transcribe_mp3_whisper(audio_path)
            elif lyrics_text is None:
                lyrics_text = "No transcript found"

        if lyrics_text:
            st.subheader(f"🎤 Lyrics + Chords (Applicable sa LAHAT ng kanta):")
            words = lyrics_text.split()
            # Display na may chords sa taas
            html_out = ""
            for i, w in enumerate(words[:150]):
                c = transposed[i % len(transposed)] if i < len(transposed) else target_key
                if i % 8 == 0 and i!=0:
                    html_out += "<br><br>"
                html_out += f"<span style='color:red; font-weight:bold;'>[{c}]</span>{w} "
            st.markdown(html_out, unsafe_allow_html=True)

            # PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial",'B',14)
            pdf.cell(0,10,f"Key {key} -> {target_key} | {title}", ln=True, align='C')
            pdf.ln(5)
            for i in range(0, min(len(words),150), 8):
                ch_line = " ".join(transposed[i:i+8])
                w_line = " ".join(words[i:i+8])
                pdf.set_font("Arial",'B',9)
                pdf.cell(0,6,ch_line, ln=True)
                pdf.set_font("Arial",'',10)
                pdf.cell(0,6,w_line, ln=True)
                pdf.ln(2)
            pdf.output("JM_Chords.pdf")
            with open("JM_Chords.pdf","rb") as f:
                st.download_button("📄 DOWNLOAD PDF (Lyrics+Chords)", f, file_name="JM_Chords_Lyrics.pdf", use_container_width=True)
        else:
            st.info("No lyrics na-detect, pero may chords pa rin.")
    else:
        st.error("Audio file not found!")

st.markdown("---")
st.caption("Option B: ANY MP3 = Whisper AI Transcription + Auto Chords. Mas mabagal ng 30s pero lahat ng kanta may lyrics!")
