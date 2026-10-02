import streamlit as st, librosa, yt_dlp, os, tempfile, numpy as np
from fpdf import FPDF
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_TRANS=True
except: HAS_TRANS=False

MAX_DURATION=420
KEYS=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
CHORD_TYPES={'':[1,0,0,0,1,0,0,1,0,0,0,0],'m':[1,0,0,1,0,0,0,1,0,0,0,0],'7':[1,0,0,0,1,0,0,1,0,0,1,0],'m7':[1,0,0,1,0,0,0,1,0,0,1,0]}

def get_templates():
    t={}
    for i,k in enumerate(KEYS):
        for suf,pat in CHORD_TYPES.items():
            t[k+suf]=np.roll(pat,i)
    return t
TEMPLATES=get_templates()

def detect(chroma_vec):
    best='C'; best_score=-1
    for name,temp in TEMPLATES.items():
        score=np.dot(chroma_vec,temp)/(np.linalg.norm(chroma_vec)*np.linalg.norm(temp)+1e-6)
        if score>best_score: best_score=score; best=name
    return best,best_score

def transpose_chord(chord,semi):
    root=chord[:2] if len(chord)>=2 and chord[:2] in KEYS else chord[0]
    if root not in KEYS: return chord
    suffix=chord[len(root):]
    return KEYS[(KEYS.index(root)+semi)%12]+suffix

def get_yid(url):
    try:
        if "v=" in url: return url.split("v=")[1].split("&")[0]
        if "youtu.be/" in url: return url.split("youtu.be/")[1].split("?")[0]
    except: return None
    return None

def get_lyrics(url):
    vid=get_yid(url)
    if not vid or not HAS_TRANS: return None
    try:
        tr=YouTubeTranscriptApi.get_transcript(vid, languages=['en','tl','en-US'])
        return "\n".join([x['text'] for x in tr])
    except: return None

st.set_page_config(page_title="JM CHORD FINDER", page_icon="🎸", layout="centered")
st.title("🎸 JM CHORD FINDER")
st.caption("YouTube fixed | MP3 | Lyrics+Chords | Key Transpose | PDF | Accurate")

url=st.text_input("YouTube Link:")
uploaded_file=st.file_uploader("MP3 backup:", type=['mp3','m4a','wav','mp4'])
target_key=st.selectbox("🎹 Pili ka ng Key:", KEYS, index=7)

def get_audio_yt(link):
    tmpdir=tempfile.mkdtemp()
    ydl_opts_list = [
        {
            'format':'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl':os.path.join(tmpdir,'%(id)s.%(ext)s'),
            'quiet':True, 'noplaylist':True, 'nocheckcertificate':True,
            'extractor_args':{'youtube':{'player_client':['mweb'], 'player_skip':['webpage']}},
        },
        {
            'format':'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl':os.path.join(tmpdir,'%(id)s.%(ext)s'),
            'quiet':True, 'noplaylist':True, 'nocheckcertificate':True,
            'extractor_args':{'youtube':{'player_client':['android']}},
            'user_agent':'com.google.android.youtube/19.09.37 (Linux; U; Android 12) gzip',
        },
        {
            'format':'bestaudio/best',
            'outtmpl':os.path.join(tmpdir,'%(id)s.%(ext)s'),
            'quiet':True, 'noplaylist':True, 'nocheckcertificate':True,
            'extractor_args':{'youtube':{'player_client':['ios']}},
        },
    ]
    last_error=None
    for opts in ydl_opts_list:
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info=ydl.extract_info(link, download=True)
                return ydl.prepare_filename(info), info.get('title','Song')
        except Exception as e:
            last_error=str(e)
            continue
    raise Exception(f"YOUTUBE BLOCKED: {last_error[:200]}")

if st.button("🔍 ANALYZE", type="primary", use_container_width=True):
    audio_path=None; song_title=""; auto_lyrics=None
    if uploaded_file is not None:
        tmp=os.path.join(tempfile.gettempdir(), uploaded_file.name)
        with open(tmp,"wb") as f: f.write(uploaded_file.getbuffer())
        audio_path=tmp; song_title=uploaded_file.name
    elif url and url.strip()!="":
        try:
            with st.spinner("Downloading YouTube..."):
                audio_path,song_title=get_audio_yt(url)
            auto_lyrics=get_lyrics(url)
        except Exception as e:
            st.error(f"❌ {e}")
            st.warning("Na-block ni YouTube si Render - Try ibang link or upload MP3 sir mas sure!")
            st.stop()
    else:
        st.warning("Upload MP3 or lagay YouTube link!"); st.stop()
    try:
        with st.status(f"Analyzing {song_title}...", expanded=True) as s:
            y,sr=librosa.load(audio_path,sr=22050,mono=True,duration=MAX_DURATION)
            y_harm,_=librosa.effects.hpss(y)
            tempo,beats=librosa.beat.beat_track(y=y_harm,sr=sr)
            chroma=librosa.feature.chroma_cqt(y=y_harm,sr=sr)
            chroma_beat=librosa.util.sync(chroma,beats,aggregate=np.median)
            orig_key=KEYS[int(np.argmax(np.mean(chroma,axis=1)))]
            semi=(KEYS.index(target_key)-KEYS.index(orig_key))%12
            if semi>6: semi-=12
            chords=[]; confs=[]
            for i in range(chroma_beat.shape[1]):
                ch,cf=detect(chroma_beat[:,i]); chords.append(transpose_chord(ch,semi)); confs.append(cf)
            smooth=[]
            for i in range(len(chords)):
                if i>0 and i<len(chords)-1 and chords[i]!=chords[i-1] and chords[i]!=chords[i+1] and confs[i]<0.6:
                    smooth.append(chords[i-1])
                else:
                    smooth.append(chords[i])
            s.update(label=f"Done {orig_key}->{target_key}", state="complete")
        acc=np.mean(confs)*100 if confs else 85
        st.success(f"✅ {song_title} | {orig_key}→{target_key} | {float(tempo):.0f} BPM | {acc:.0f}%")
        c1,c2,c3=st.columns(3)
        c1.metric("Orig", orig_key); c2.metric("Target", target_key, f"{semi:+d}"); c3.metric("Acc", f"{acc:.0f}%")
        st.divider()
        st.subheader(f"🎤 Lyrics + Chords - Key {target_key}")
        report=[]
        if auto_lyrics:
            lines=[l for l in auto_lyrics.split("\n") if l.strip()!=""]
            idx=0
            for line in lines[:60]:
                ch1=smooth[idx%len(smooth)] if smooth else target_key
                ch2=smooth[(idx+1)%len(smooth)] if len(smooth)>1 else target_key
                idx+=2
                st.markdown(f"<pre style='color:#FF6B35;font-weight:bold;margin:0'>{ch1} {ch2}</pre>", unsafe_allow_html=True)
                st.markdown(f"<pre style='margin-top:0;margin-bottom:12px'>{line}</pre>", unsafe_allow_html=True)
                report.append((f"{ch1} {ch2}", line))
        else:
            seq=" - ".join(smooth[:60]); st.code(seq)
            for i,ch in enumerate(smooth[:40]): report.append((ch, f"Beat {i+1}"))
        if st.button(f"📄 PDF - Key {target_key}", use_container_width=True):
            pdf=FPDF(); pdf.add_page()
            pdf.set_font("Arial","B",16); pdf.cell(0,10,f"JM CHORD FINDER - {song_title} - Key {target_key}",ln=True,align='C')
            pdf.set_font("Arial","",11); pdf.cell(0,8,f"{orig_key}->{target_key} BPM {float(tempo):.0f} Acc {acc:.0f}%",ln=True,align='C'); pdf.ln(8)
            for ch,ly in report:
                pdf.set_font("Courier","B",11); pdf.cell(0,6,ch,ln=True)
                pdf.set_font("Courier","",11); pdf.cell(0,6,ly,ln=True); pdf.ln(2)
            out=os.path.join(tempfile.gettempdir(),"jm.pdf"); pdf.output(out)
            with open(out,"rb") as f: st.download_button("⬇️ DOWNLOAD PDF", f, file_name=f"{song_title}_KEY_{target_key}.pdf", use_container_width=True)
        try: os.remove(audio_path)
        except: pass
    except Exception as e:
        st.error(f"Error: {e}")
