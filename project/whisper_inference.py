import sys
import torch
import torchaudio
import subprocess
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import io
from pydub import AudioSegment
import numpy as np
import os

# Set the encoding for stdout to UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Set CUDA_LAUNCH_BLOCKING for better error messages
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

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

def main():
    if len(sys.argv) < 2:
        print("Usage: python whisper_inference.py <input_audio_file>", file=sys.stderr)
        sys.exit(1)

    input_m4a = sys.argv[1]
    output_wav = "temp.wav"  # 一時ファイルとして WAV を出力

    # ----- 1) M4A -> WAV変換 -----
    convert_to_wav(input_m4a, output_wav)

    # ----- 2) Whisper 推論 -----
    # モデルID
    # model_id = "openai/whisper-large-v3-turbo"
    model_id = "kotoba-tech/kotoba-whisper-v2.0"


    # 今回は torch.float16 を強制的に使用
    # GPU がない環境ではエラーになる可能性があります
    device = "cuda:0"  # GPU が複数ある場合は必要に応じて変更
    torch_dtype = torch.float16

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
        torch_dtype=torch_dtype,  # pipelineにも指定
        device=0  # デバイスはGPU:0 (CUDA) を示すために int で書いています
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
    torch.cuda.empty_cache()

    # 標準出力にテキストを返す
    print(recognized_text)

if __name__ == "__main__":
    main()
