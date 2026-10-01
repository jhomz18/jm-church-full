import streamlit as st, librosa, yt_dlp, os, tempfile, numpy as np
from fpdf import FPDF
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_TRANSCRIPT=True
except:
    HAS_TRANSCRIPT=False

MAX_DURATION=420 # 7 MINS MAX - MABILIS!
KEYS=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

def transpose_chord(chord, semi):
    root=chord[:2] if len(chord)>=2 and chord[:2] in KEYS else chord[0]
    if root not in KEYS: return chord
    new_root=KEYS[(KEYS.index(root)+semi)%12]
    return chord.replace(root,new_root,1)

def get_youtube_id(url):
    try:
        if "v=" in url: return url.split("v=")[1].split("&")[0]
        if "youtu.be/" in url: return url.split("youtu.be/")[1].split("?")[0]
    except: return None
    return None

def get_auto_lyrics(youtube_url):
    vid=get_youtube_id(youtube_url)
    if not vid or not HAS_TRANSCRIPT: return None
    try:
        trans=YouTubeTranscriptApi.get_transcript(vid, languages=['en','tl','en-US'])
        return "\n".join([x['text'] for x in trans])
    except:
        return None

st.set_page_config(page_title="JM Church Chord Finder", page_icon="🎸", layout="centered")
st.title("🎸 JM CHURCH CHORD FINDER")
st.caption("Link lang | Pili Key C D E G A | 7 mins max")

url=st.text_input("YouTube Link lang:")
uploaded_file=st.file_uploader("Or Upload MP3 backup:", type=['mp3','m4a','wav','mp4'])

# KEY SELECTION TALAGA - HINDI SEMITONES
target_key=st.selectbox("🎹 Pili ka ng Key na gusto mo:", KEYS, index=7)
st.caption(f"Target Key mo: {target_key} - Auto detect original key after analyze")

def get_audio_youtube(youtube_url):
    tmpdir=tempfile.mkdtemp()
    opts={'format':'bestaudio[ext=m4a]/bestaudio','outtmpl':os.path.join(tmpdir,'%(id)s.%(ext)s'),'quiet':True,'noplaylist':True,'extractor_args':{'youtube':{'player_client':['android','web']}},'user_agent':'Mozilla/5.0','nocheckcertificate':True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info=ydl.extract_info(youtube_url,download=True)
        return ydl.prepare_filename(info),info.get('title','Song')

if st.button("🔍 AUTO ANALYZE", type="primary", use_container_width=True):
    path=None; title=""; auto_lyrics=None
    try:
        if uploaded_file:
            tmp_path=os.path.join(tempfile.gettempdir(), uploaded_file.name)
            with open(tmp_path,"wb") as f: f.write(uploaded_file.getbuffer())
            path,title=tmp_path,uploaded_file.name
        elif url:
            auto_lyrics=get_auto_lyrics(url)
            path,title=get_audio_youtube(url)
        else:
            st.warning("Lagay mo YouTube link sir!"); st.stop()

        with st.status(f"Analyzing {title}...", expanded=True) as s:
            y,sr=librosa.load(path,sr=22050,mono=True,duration=MAX_DURATION)
            dur=librosa.get_duration(y=y,sr=sr)
            tempo,_=librosa.beat.beat_track(y=y,sr=sr)
            chroma=librosa.feature.chroma_cqt(y=y,sr=sr)
            orig_key=KEYS[int(np.argmax(np.sum(chroma,axis=1)))]
            semi=(KEYS.index(target_key)-KEYS.index(orig_key))%12
            if semi>6: semi-=12
            chords=[]
            for i in range(0,chroma.shape[1],86):
                c=KEYS[int(np.argmax(np.mean(chroma[:,i:i+86],axis=1)))]
                chords.append(transpose_chord(c,semi))
            s.update(label=f"Done: {orig_key} -> {target_key}", state="complete")

        st.success(f"✅ {title}")
        st.metric(label="KEY", value=f"{orig_key} → {target_key}", delta=f"{semi:+d}")
        st.write(f"BPM: {float(tempo):.0f} | Duration: {dur/60:.1f} min / 7 min max")

        st.divider()
        st.subheader(f"🎤 Lyrics with Chords - Key of {target_key}")
        report=[]
        if auto_lyrics:
            st.success("Auto lyrics galing YouTube!")
            lines=auto_lyrics.split("\n"); idx=0
            for line in lines[:60]:
                if line.strip()=="": continue
                c1=chords[idx%len(chords)] if chords else target_key
                c2=chords[(idx+1)%len(chords)] if len(chords)>1 else target_key
                idx+=2
                st.markdown(f"<pre style='color:#FF6B35;font-weight:bold;margin:0'>{c1} {c2}</pre>", unsafe_allow_html=True)
                st.markdown(f"<pre style='margin-top:0;margin-bottom:12px'>{line}</pre>", unsafe_allow_html=True)
                report.append((f"{c1} {c2}", line))
        else:
            seq=" - ".join(chords[:40]); st.code(seq); report=[("Chords",seq)]
            st.info("Walang captions sa YouTube pero eto chords sa Key na gusto mo!")

        if st.button("📄 PDF - Key "+target_key):
            pdf=FPDF(); pdf.add_page(); pdf.set_font("Arial","B",16)
            pdf.cell(0,10,f"JM CHURCH CHORD FINDER- {title} - Key {target_key}",ln=True,align='C')
            pdf.set_font("Arial","",11); pdf.cell(0,8,f"Orig {orig_key} -> {target_key} BPM {float(tempo):.0f} {dur/60:.1f}min",ln=True); pdf.ln(5)
            pdf.set_font("Courier","",11)
            for ch,lyr in report:
                pdf.set_font("Courier","B",11); pdf.cell(0,6,ch,ln=True)
                pdf.set_font("Courier","",11); pdf.cell(0,6,lyr,ln=True); pdf.ln(2)
            out=os.path.join(tempfile.gettempdir(),"jm_final.pdf"); pdf.output(out)
            with open(out,"rb") as f: st.download_button("⬇️ DOWNLOAD PDF",f,file_name=f"{title}_KEY_{target_key}.pdf",use_container_width=True)
        try: os.remove(path)
        except: pass
    except Exception as e:
        st.error(f"Error: {e}")
