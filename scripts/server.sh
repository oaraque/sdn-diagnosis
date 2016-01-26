vlc  /tmp/video.mkv :sout='#transcode{vcodec=h264,scale=Auto,acodec=mpga,ab=128,channels=2,samplerate=44100}:http{mux=ffmpeg{mux=flv},dst=:80/test}' :sout-keep & 
