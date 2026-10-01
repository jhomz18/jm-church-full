import streamlit as st
import librosa
import yt_dlp
import os
import tempfile
import numpy as np

# --- CONFIG ---
MAX_DURATION = 600 # 10 MINS NA SIR!
st.set_page_config(page_title="JM Church - Full Song", page_icon="🎸", layout="centered")

st.title("🎸 JM CHURCH - FULL SONG ANALYSIS")
st.caption(f"Full analysis up to {MAX_DURATION//60} mins | 512MB Optimized")
st.divider()

url = st.text_input("Paste YouTube worship song link here:", placeholder="https://www.youtube.com/watch?v=...")

def get_audio_path(youtube_url):
    tmpdir = tempfile.mkdtemp()
    # M4A lang para tipid sa RAM at mabilis
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio',
        'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
        'quiet': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        filepath = ydl.prepare_filename(info)
        return filepath, info.get('title', 'Worship Song')

if st.button("🔍 Analyze Full Song", type="primary"):
    if not url:
        st.warning("Paste ka muna ng YouTube link sir!")
    else:
        try:
            with st.status("Downloading & Analyzing... baka 30-40 sec", expanded=True) as status:
                st.write("⬇️ Downloading audio...")
                audio_path, title = get_audio_path(url)

                st.write(f"🎵 Loading up to {MAX_DURATION//60} mins (sr=22k mono for 512MB)...")
                # TIPID SA RAM: 22k + mono + max 10 mins
                y, sr = librosa.load(audio_path, sr=22050, mono=True, duration=MAX_DURATION)

                duration_sec = librosa.get_duration(y=y, sr=sr)

                st.write("🥁 Analyzing tempo, key, energy...")
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
                # Simple key guess from chroma
                key_idx = np.argmax(np.sum(chroma, axis=1))
                keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                est_key = keys[key_idx]

                # Energy / sections for Verse-Chorus guess
                rms = librosa.feature.rms(y=y)[0]

                status.update(label=f"Done! {title}", state="complete")

            st.success(f"✅ **{title}**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Duration Analyzed", f"{duration_sec/60:.1f} min")
            c2.metric("Tempo", f"{float(tempo):.0f} BPM")
            c3.metric("Est. Key", est_key)

            st.subheader("📊 Full Song Structure (Auto)")
            st.write(f"Total length na na-analyze: **{duration_sec:.1f} sec**. Kung lagpas 10 mins yung original, hanggang 10 mins lang kinuha natin para kumasya sa Free 512MB RAM.")

            # Simple timeline
            sections = int(duration_sec // 30) # every 30 sec isang section
            for i in range(sections):
                start = i*30
                energy = np.mean(rms[int(i*len(rms)/sections):int((i+1)*len(rms)/sections)])
                label = "Chorus (High Energy)" if energy > np.mean(rms) else "Verse / Bridge"
                st.progress(min(1.0, energy*3), text=f"{start//60}:{start%60:02d} - {label}")

            st.divider()
            st.info("💡 TIP: Naka 10 mins na to sir! Kaya na mga live worship. Pag 2 users sabay, baka mag-restart si Render kasi sagad 512MB - okay lang, libre naman.")

            # Cleanup
            try:
                os.remove(audio_path)
            except:
                pass

        except Exception as e:
            st.error(f"Error sir: {e}")
            st.write("Try mo ibang YouTube link o check mo kung private yung video.")
