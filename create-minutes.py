import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import subprocess
import torchaudio

# Set device and torch dtype
device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

# Model ID
model_id = "openai/whisper-large-v3-turbo"

# Load model and processor from model ID
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True
)
model.to(device)

processor = AutoProcessor.from_pretrained(model_id)

# Define pipeline
pipe = pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    chunk_length_s=30,
    batch_size=16,
    torch_dtype=torch_dtype,
    device=device,
)

# Function to convert M4A to WAV using ffmpeg
def convert_to_wav(input_path, output_path):
    command = [
        "C:/ffmpeg-7.1-essentials_build/bin/ffmpeg", "-y", "-i", input_path,
        "-ar", "16000", output_path
    ]
    subprocess.run(command, check=True)

# Convert the M4A file to WAV
convert_to_wav("Recording2.m4a", "Recording.wav")

# Load and process the audio file
waveform, sample_rate = torchaudio.load("Recording.wav")

# Convert to mono if stereo
if waveform.size(0) == 2:
    waveform = waveform.mean(dim=0, keepdim=True)

input_audio = {"array": waveform.squeeze().numpy(), "sampling_rate": sample_rate}

# Transcribe the audio
result = pipe(input_audio)

# Print the transcription
print(result["text"])

# Save the corrected transcription to a file with UTF-8 encoding
with open("Corrected_Transcription.txt", "w", encoding="utf-8") as f:
    f.write(result["text"])