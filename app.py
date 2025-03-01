from fastapi import FastAPI, UploadFile, File
import shutil
import librosa
import numpy as np
import speech_recognition as sr
import os

from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
import torch
import librosa


app = FastAPI()
# Load pre-trained Wav2Vec2 model
processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-large-960h")
model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-large-960h")



# Step 1: Transcribe Audio
def transcribe_audio(file_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return "Error in API"

# Step 2: Detect Fillers Dynamically
def dynamic_filler_detection(transcription):
    # Define common filler patterns (generalizable)
    filler_words = ["uh", "um", "ah", "eh", "hmm", "like", "you know", "so", "actually"]
    fillers_found = []
    words = transcription.lower().split()
    
    # Detect fillers in transcription
    for word in words:
        if word in filler_words or len(word) <= 2:  # Short, low-info words
            fillers_found.append(word)
    
    return fillers_found

# Step 3: Audio Analysis for Pauses and Filler Sounds
def detect_pauses_and_fillers(audio_path):
    y, sr = librosa.load(audio_path, sr=None)
    durations = librosa.get_duration(y=y, sr=sr)
    silence = librosa.effects.split(y, top_db=30)  # Split by silence thresholds
    
    filler_durations = []
    for start, end in silence:
        duration = (end - start) / sr
        if 0.1 < duration < 0.6:  # Detect short pauses likely to be fillers
            filler_durations.append(duration)
    
    return filler_durations

# Step 4: Main Analysis Function
def analyze_audio_dynamically(audio_path):
    # Transcribe audio
    transcription = transcribe_audio(audio_path)
    if not transcription:
        return {"error": "Unable to transcribe audio"}
    
    # Detect fillers dynamically
    detected_fillers = dynamic_filler_detection(transcription)
    
    # Analyze audio for pauses
    filler_durations = detect_pauses_and_fillers(audio_path)
    
    return {
        "transcription": transcription,
        "detected_fillers": detected_fillers,
        "pause_based_fillers": len(filler_durations),
    }





def detect_phonemes(audio_path):
    # Load and preprocess audio
    y, sr = librosa.load(audio_path, sr=16000)
    input_values = processor(y, sampling_rate=sr, return_tensors="pt", padding=True).input_values

    # Run model inference
    logits = model(input_values).logits
    predicted_ids = torch.argmax(logits, dim=-1)

    # Decode to text or phonemes
    transcription = processor.batch_decode(predicted_ids)
    return transcription

# Example usage
# print(detect_phonemes("example.wav"))


@app.post("/upload-audio/")
async def upload_audio(file: UploadFile = File(...)):
    # Save the uploaded file temporarily
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Analyze the saved audio file
    results = analyze_audio_dynamically(temp_file_path)
    transcription = detect_phonemes(temp_file_path)
    
    # Optionally clean up the file (delete temporary file)
    # import os
    os.remove(temp_file_path)
    print(results)
    print(type(results))  
    print(transcription)  
    
    return {"filename": file.filename, "results": results, "transcription" : transcription}  

@app.get("/")
def read_root():
    return {"message": "Hello, FluenZ- Version 1.1.2+6!"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
