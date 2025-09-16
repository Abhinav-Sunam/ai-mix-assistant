import streamlit as st
from pydub import AudioSegment
import pyloudnorm as pyln
import numpy as np
import io

st.title("🎧 AI Mix Assistant (Prototype)")

uploaded = st.file_uploader("Upload your song (MP3/WAV)", type=["mp3","wav"])

if uploaded:
    # Load audio
    audio = AudioSegment.from_file(uploaded)
    
    # Convert to proper numpy array for pyloudnorm
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    
    # Normalize the samples to [-1, 1] range (this was missing!)
    samples = samples / (2**(audio.sample_width * 8 - 1))
    
    # Handle stereo vs mono properly
    if audio.channels == 2:
        samples = samples.reshape((-1, 2))  # Keep stereo for accurate LUFS
    else:
        samples = samples.reshape((-1, 1))  # Mono format
    
    # Create loudness meter
    meter = pyln.Meter(audio.frame_rate)
    
    # Measure loudness (this will now be accurate!)
    loudness = meter.integrated_loudness(samples)
    
    st.write(f"🎚️ Track loudness: {loudness:.2f} LUFS")
    
    # CORRECTED feedback rules
    if loudness < -18:
        st.write("⚠️ Track is too quiet → Need to boost volume significantly!")
        st.write("🔊 Recommendation: Increase by +4 to +8 dB")
    elif loudness < -14:
        st.write("⚠️ A bit quiet → Could use more volume")
        st.write("🔊 Recommendation: Increase by +2 to +4 dB")
    elif loudness > -10:
        st.write("⚠️ Too loud → Risk of distortion")
        st.write("🔉 Recommendation: Reduce by -2 to -4 dB")
    elif loudness > -12:
        st.write("⚠️ Bit too loud → Slightly reduce volume")
        st.write("🔉 Recommendation: Reduce by -1 to -2 dB")
    else:
        st.write("✅ Loudness is in a good range for streaming!")
    
    # Calculate gain needed to reach -14 LUFS
    target_lufs = -14
    gain_needed = target_lufs - loudness
    
    st.write(f"🎯 Target: {target_lufs} LUFS | Current: {loudness:.1f} LUFS")
    st.write(f"🔧 Applying gain: {gain_needed:+.1f} dB")
    
    # FIXED: Apply gain and ensure audio data is preserved
    try:
        # Apply the calculated gain
        normalized_audio = audio.apply_gain(gain_needed)
        
        # Export to memory buffer (FIXED method)
        output_buffer = io.BytesIO()
        
        # Export with specific parameters to ensure quality
        normalized_audio.export(
            output_buffer, 
            format="wav",
            parameters=["-ac", "2", "-ar", str(audio.frame_rate)]
        )
        
        # Get the audio data
        output_buffer.seek(0)
        audio_data = output_buffer.getvalue()
        
        # Verify the file isn't empty
        if len(audio_data) > 1000:  # Should be much larger than 1KB
            st.success(f"✅ Fixed audio ready! File size: {len(audio_data)} bytes")
            
            # Download button
            st.download_button(
                "⬇️ Download Auto-Fixed Mix", 
                data=audio_data,
                file_name="fixed_mix.wav",
                mime="audio/wav"
            )
        else:
            st.error("❌ Error: Generated audio file is empty!")
            
    except Exception as e:
        st.error(f"❌ Error processing audio: {str(e)}")
        st.write("Try a different audio file or check file format.")

# Add some helpful info
st.markdown("---")
st.markdown("""
### 📊 LUFS Reference:
- **-23 LUFS**: TV/Broadcast standard
- **-16 LUFS**: Apple Music, Tidal  
- **-14 LUFS**: Spotify, YouTube Music (target)
- **-12 LUFS**: Loud but acceptable
- **-10 LUFS and above**: Too loud, will cause distortion

### 💡 Tips:
- Most home recordings are around -18 to -25 LUFS (too quiet)
- This tool normalizes to -14 LUFS for streaming platforms
- The "fixed" version will sound louder and more professional
""")