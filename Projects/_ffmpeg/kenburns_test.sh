# Test: 1 sekil + narration + SRT -> 1080p30 H.264 (Ken Burns yavas zoom-in)
# Qeyd: subtitles filtrinde Windows disk herfi "C\:" kimi escape olunmalidir.
set -e
IMG="C:/YouTubeAI/ComfyUI/output/test01_owl_00001_.png"
AUD="C:/YouTubeAI/Output/voice_samples/am_michael.wav"
SRT_ESC='C\:/YouTubeAI/Temp/sub_test.srt'
OUT="C:/YouTubeAI/Temp/montage_test.mp4"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$AUD")
FRAMES=$(python -c "print(int(float('$DUR')*30)+1)")
# zoompan: 1.0 -> 1.15 zoom, merkeze dogru; once 4K-ya boyudub sonra 1080p-ye endiririk (titreme olmasin)
ffmpeg -y -loglevel error -loop 1 -i "$IMG" -i "$AUD" \
  -filter_complex "[0:v]scale=3840:3840:force_original_aspect_ratio=increase,crop=3840:2160,zoompan=z='min(zoom+0.0007,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=${FRAMES}:s=1920x1080:fps=30,format=yuv420p,subtitles='${SRT_ESC}':force_style='FontName=Arial,FontSize=20,Bold=1,Outline=2,Shadow=0,MarginV=40'[v]" \
  -map "[v]" -map 1:a -c:v libx264 -preset medium -crf 20 -r 30 -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate:format=duration -of default=nw=1 "$OUT"
