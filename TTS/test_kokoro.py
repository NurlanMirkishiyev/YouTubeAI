import soundfile as sf, time
from kokoro import KPipeline
t=time.time()
p = KPipeline(lang_code='a')
text = "Welcome to ELI5 Business. Today we explain the difference between a trademark, a copyright, and a patent, in the simplest way possible."
for i,(gs,ps,audio) in enumerate(p(text, voice='am_michael', speed=1.0)):
    sf.write(r'C:\YouTubeAI\Temp\tts_test_am_michael.wav', audio, 24000); break
print('kokoro ok in %.1fs' % (time.time()-t))
