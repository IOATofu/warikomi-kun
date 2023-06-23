import whisper

model = whisper.load_model("medium")
result = model.transcribe("620830778145636358.wav")
print(result["text"])
