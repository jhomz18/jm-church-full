import streamlit as st, librosa, numpy as np
from fpdf import FPDF

st.title("🎸 JM CHORD FINDER")
NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
TEMPLATE = {
 '': [1,0,0,0,1,0,0,1,0,0,0,0],
 'm': [1,0,0,1,0,0,0,0],
 '7': [1,0,0,0,1,0,0,1,0,0,1,0],
 'maj7': [1,0,0,0,1,0,0,1,0,0,0,1]
}
def get_chord(v):
    v = v/np.linalg.norm(v)
    best, sc = "C", -1
    for r in range(12):
        for s,t in TEMPLATE.items():
            tp = np.roll(t,r)/np.linalg.norm(np.roll(t,r))
            dot = np.dot(v,tp)
            if dot>sc: sc, best = dot, f"{NOTES[r]}{s}"
    return best

file = st.file_uploader("Upload MP3/MP4:", type=["mp3","mp4","wav","m4a"])
target = st.selectbox("Transpose to:", NOTES, index=7)

if file:
    open("s.mp3","wb").write(file.getbuffer())
    st.audio("s.mp3")
    if st.button("ANALYZE", type="primary", use_container_width=True):
        y,sr = librosa.load("s.mp3", duration=90)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        key = NOTES[np.argmax(np.mean(chroma, axis=1))]
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        bc = librosa.util.sync(chroma, beats, aggregate=np.median)
        chords = [get_chord(bc[:,i]) for i in range(bc.shape[1])]
        clean = []
        for c in chords:
            if not clean or clean[-1]!=c: clean.append(c)
        steps = (NOTES.index(target)-NOTES.index(key))%12
        trans = [NOTES[(NOTES.index(c[0] if len(c)==1 else c[:2] if c[1]=='#' else c[0])+steps)%12] + c[len(c[0] if len(c)==1 else c[:2] if c[1]=='#' else c[0]):] if c[0] in ''.join(NOTES) else c for c in clean]
        # Fix transpose simple
        def tr(ch, st):
            r = ch[:2] if len(ch)>1 and ch[1]=='#' else ch[0]
            suf = ch[len(r):]
            return NOTES[(NOTES.index(r)+st)%12]+suf if r in NOTES else ch
        trans = [tr(c,steps) for c in clean]

        st.success(f"Original Key: {key} | Target: {target} | BPM: {int(tempo)}")
        st.code(" - ".join(trans[:100]))

        pdf=FPDF()
        pdf.add_page()
        pdf.set_font("Arial",'B',12)
        pdf.cell(0,10,f"Key {key} -> {target} | {file.name}", ln=True, align='C')
        pdf.set_font("Arial",'',10)
        for i in range(0,len(trans),10):
            pdf.cell(0,6," - ".join(trans[i:i+10]), ln=True)
        pdf.output("out.pdf")
        with open("out.pdf","rb") as f:
            st.download_button("DOWNLOAD PDF", f, file_name="chords.pdf", use_container_width=True)
