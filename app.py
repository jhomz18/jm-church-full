import streamlit as st, librosa, yt_dlp, os, tempfile, numpy as np
from fpdf import FPDF
MAX_DURATION=600
KEYS=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def transpose_chord(chord, semi):
    root=chord.replace('m','').replace('7','').replace('sus4','').replace('sus','').replace('maj','')[:2].strip()
    if root not in KEYS: root=root[0]
    if root not in KEYS: return chord
    new_root=KEYS[(KEYS.index(root)+semi)%12]
    return chord.replace(root,new_root,1)
st.set_page_config(page_title="JM Church Full",page_icon="🎸",layout="centered")
st.title("🎸 JM CHURCH - COMPLETE")
st.caption("10 Mins | Transpose | PDF | Lyrics + Chords | 512MB Ready")
url=st.text_input("YouTube Link:")
semi=st.slider("Transpose semitones",-6,6,0)
lyrics_input=st.text_area("Paste Lyrics (optional):",height=120,placeholder="Pupurihin Ka sa awit...")
def get_audio(youtube_url):
    tmpdir=tempfile.mkdtemp()
    opts={'format':'bestaudio[ext=m4a]/bestaudio','outtmpl':os.path.join(tmpdir,'%(id)s.%(ext)s'),'quiet':True,'noplaylist':True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info=ydl.extract_info(youtube_url,download=True)
        return ydl.prepare_filename(info),info.get('title','Worship Song')
if st.button("🔍 ANALYZE COMPLETE",type="primary",use_container_width=True):
    if not url: st.warning("Paste link muna sir!")
    else:
        try:
            with st.status("Analyzing 10 mins...",expanded=True) as s:
                s.write("⬇️ Downloading...")
                path,title=get_audio(url)
                s.write("🎵 Detecting...")
                y,sr=librosa.load(path,sr=22050,mono=True,duration=MAX_DURATION)
                dur=librosa.get_duration(y=y,sr=sr)
                tempo,_=librosa.beat.beat_track(y=y,sr=sr)
                chroma=librosa.feature.chroma_cqt(y=y,sr=sr)
                orig_key=KEYS[int(np.argmax(np.sum(chroma,axis=1)))]
                new_key=KEYS[(KEYS.index(orig_key)+semi)%12]
                chords=[]
                for i in range(0,chroma.shape[1],86):
                    c=KEYS[int(np.argmax(np.mean(chroma[:,i:i+86],axis=1)))]
                    chords.append(transpose_chord(c,semi))
                s.update(label=f"Done: {title}",state="complete")
            st.success(f"{title} | {orig_key} -> {new_key} | {float(tempo):.0f} BPM | {dur/60:.1f}m")
            st.subheader(f"Lyrics + Chords - Key {new_key}")
            report=[]
            if lyrics_input:
                lines=lyrics_input.split('\n'); idx=0
                for line in lines:
                    if line.strip()=="": st.write(""); report.append(("", "")); continue
                    c1=chords[idx%len(chords)] if chords else new_key
                    c2=chords[(idx+1)%len(chords)] if len(chords)>1 else new_key
                    idx+=2
                    st.markdown(f"<pre style='color:#FF6B35;font-weight:bold;margin:0'>{c1} {c2}</pre>",unsafe_allow_html=True)
                    st.markdown(f"<pre style='margin-top:0'>{line}</pre>",unsafe_allow_html=True)
                    report.append((f"{c1} {c2}",line))
            else:
                st.code(" - ".join(chords[:30])); report=[("Chords"," - ".join(chords[:30]))]
            if st.button("📄 Generate PDF"):
                pdf=FPDF(); pdf.add_page(); pdf.set_font("Arial","B",16)
                pdf.cell(0,10,f"JM CHURCH - {title}",ln=True,align='C')
                pdf.set_font("Arial","",11); pdf.cell(0,8,f"Key {orig_key}->{new_key} ({semi:+d}) BPM {float(tempo):.0f} {dur/60:.1f}m",ln=True); pdf.ln(5)
                pdf.set_font("Courier","",11)
                for ch, lyr in report:
                    if ch=="": pdf.ln(4); continue
                    pdf.cell(0,6,ch,ln=True); pdf.cell(0,6,lyr,ln=True); pdf.ln(2)
                out=os.path.join(tempfile.gettempdir(),"jm.pdf"); pdf.output(out)
                with open(out,"rb") as f: st.download_button("⬇️ DOWNLOAD PDF",f,file_name=f"{title}_{new_key}.pdf",use_container_width=True)
            try: os.remove(path)
            except: pass
        except Exception as e: st.error(f"Error: {e}")
