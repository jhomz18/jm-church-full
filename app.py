import streamlit as st
import librosa
import numpy as np
from chord_extractor.extractors import ChordExtractor

st.set_page_config(page_title="JM - Chord Finder", layout="centered")
st.title("🎸 JM - Chord Finder ")

uploaded = st.file_uploader("Upload song:", type=["mp3","wav","m4a"])

if uploaded:
    st.audio(uploaded)
    if st.button("🔍 ANALYZE ", type="primary", use_container_width=True):
        with open("temp.mp3","wb") as f:
            f.write(uploaded.getbuffer())
        with st.spinner("AI analyzing..."):
            y, sr = librosa.load("temp.mp3", sr=22050, duration=60)
            extractor = ChordExtractor()
            chords = extractor.extract(y, sr)
            st.session_state.result = chords

if "result" in st.session_state:
    st.success("✅ Done - Accurate Chords:")
    for c in st.session_state.result:
        st.write(f"{c['timestamp']} - **{c['chord']}**")
