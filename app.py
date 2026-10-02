import streamlit as st, librosa, numpy as np
from fpdf import FPDF

st.title("🎸 JM CHORD FINDER")
NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
TEMPLATES = {'':[1,0,0,0,1,0,0,1,0,0,0,0],'m':[1,0,0,1,0,0,0,0],'7':[1,0,0,0,1,0,0,1,0,0,1,0]}

def get_chord(v):
    v=v/np.linalg.norm(v)
    best,s="C",-1
    for r in range(12):
        for suf,t in TEMPLATES.items():
            tt=np.roll(t,r)
            if len(tt)<12:
                f=np.zeros(12);f[:len(tt)]=tt;tt=f
            tt=tt/np.linalg.norm(tt)
            d=np.dot(v,tt)
            if d>s: s=d;best=f"{NOTES[r]}{suf}"
    return best

up = st.file_uploader("Upload MP3/MP4:", type=["mp3","mp4","wav","m4a"])
to = st.selectbox("Transpose to:", NOTES, index=4)

if st.button("🔍 ANALYZE CHORDS NOW", type="primary", use_container_width=True):
    if up is None:
        st.error("WALANG FILE - Upload muna sa taas!")
    else:
        open("t.mp3","wb").write(up.getbuffer())
        st.audio("t.mp3")
        with st.spinner("Analyzing..."):
            y,sr=librosa.load("t.mp3",duration=90)
            ch=librosa.feature.chroma_cqt(y=y,sr=sr)
            key=NOTES[np.argmax(np.mean(ch,axis=1))]
            tempo,beats=librosa.beat.beat_track(y=y,sr=sr)
            bc=librosa.util.sync(ch,beats,aggregate=np.median)
            chords=[get_chord(bc[:,i]) for i in range(bc.shape[1])]
            clean=[chords[0]]
            for c in chords[1:]:
                if c!=clean[-1]: clean.append(c)
            steps=(NOTES.index(to)-NOTES.index(key))%12
            trans=[NOTES[(NOTES.index((c[:2] if len(c)>1 and c[1]=='#' else c[0]))+steps)%12]+c[len((c[:2] if len(c)>1 and c[1]=='#' else c[0])):] if (c[:2] if len(c)>1 and c[1]=='#' else c[0]) in NOTES else c for c in clean]
            st.success(f"Key: {key} -> {to} | BPM {int(tempo)}")
            st.code(" - ".join(trans[:100]))
