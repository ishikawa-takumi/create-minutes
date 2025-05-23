print("whisper_inference.py")
import sys
import torch
import torchaudio
import subprocess
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import io
from pydub import AudioSegment
import numpy as np
import os
import tempfile
from huggingface_hub import login
from dotenv import load_dotenv

load_dotenv()

# Use environment variable for HF token
access_token = os.environ.get("HF_TOKEN")
if access_token:
    login(token=access_token)
    print("Logged in to the Hugging Face Hub")
else:
    print("Warning: HF_TOKEN environment variable not set. Some features may not work correctly.")

# Set the encoding for stdout to UTF-8
# print("CUDA_LAUNCH_BLOCKING set to 1")
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
# print("CUDA_LAUNCH_BLOCKING set to 1")

# Set CUDA_LAUNCH_BLOCKING for better error messages
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
print("CUDA_LAUNCH_BLOCKING set to 1")

def convert_to_wav(input_path, output_path):
    """
    ffmpeg を用いて m4a -> wav (16kHz, mono) に変換する例です。
    ffmpeg のパスはご利用環境に合わせて書き換えてください。
    """
    command = [
        "ffmpeg", "-y", "-i", input_path,
        "-ar", "16000", output_path
    ]
    subprocess.run(command, check=True)

def transcribe_audio(input_audio_file):
    """
    Takes an audio file path and returns the transcribed text
    """
    output_wav = tempfile.mktemp(suffix='.wav')  # 一時WAVファイル

    try:
        # ----- 1) Audio -> WAV変換 -----
        convert_to_wav(input_audio_file, output_wav)

        # ----- 2) Whisper 推論 -----
        # モデルID
        # model_id = "openai/whisper-large-v3-turbo"
        model_id = "kotoba-tech/kotoba-whisper-v2.0"

        # 今回は torch.float16 を強制的に使用
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        # Whisperモデルのロード
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True
        ).to(device)

        processor = AutoProcessor.from_pretrained(model_id)

        # pipeline の作成
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            chunk_length_s=30,
            batch_size=16,
            torch_dtype=torch_dtype,
            device=0 if torch.cuda.is_available() else -1
        )

        # 音声を pydub で読み込み
        audio = AudioSegment.from_wav(output_wav)
        waveform = np.array(audio.get_array_of_samples(), dtype=np.float32)
        sample_rate = audio.frame_rate

        # モノラル変換 (ステレオの場合)
        if audio.channels == 2:
            waveform = waveform.reshape((-1, 2)).mean(axis=1)

        input_audio = {
            "array": waveform,
            "sampling_rate": sample_rate
        }

        # 推論実行
        result = pipe(input_audio)
        recognized_text = result["text"]

        # ---- GPUメモリ解放のために明示的に削除 + empty_cache ----
        del pipe
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return recognized_text

    finally:
        # 一時ファイルを削除
        if os.path.exists(output_wav):
            os.remove(output_wav)

def main():
    if len(sys.argv) < 2:
        print("Usage: python whisper_inference.py <input_audio_file>", file=sys.stderr)
        sys.exit(1)

    input_audio = sys.argv[1]
    recognized_text = transcribe_audio(input_audio)
    
    # 標準出力にテキストを返す
    print(recognized_text)

if __name__ == "__main__":
    main()
