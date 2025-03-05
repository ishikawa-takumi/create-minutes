"""
音声ファイルの文字起こし機能を提供するモジュール
Whisperモデルを使用した高精度な音声認識を提供
"""

import os
import tempfile
import subprocess
from pathlib import Path
from werkzeug.utils import secure_filename
from project.whisper_inference import transcribe_audio as whisper_transcribe

ALLOWED_AUDIO_EXTENSIONS = {'wav', 'mp3', 'mp4', 'm4a', 'flac', 'ogg'}

def allowed_audio_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

def save_uploaded_audio(audio_file):
    """アップロードされた音声ファイルを一時ディレクトリに保存する"""
    temp_dir = tempfile.gettempdir()
    filename = secure_filename(audio_file.filename)
    filepath = os.path.join(temp_dir, filename)
    audio_file.save(filepath)
    return filepath

def process_audio(file_storage):
    """Process audio file and return transcription using Whisper model"""
    # Create a temporary file
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, secure_filename(file_storage.filename))
    file_storage.save(temp_path)
    
    try:
        # Use the Whisper model for transcription
        text = whisper_transcribe(temp_path)
        return text
    
    finally:
        # Clean up temporary files
        if os.path.exists(temp_path):
            os.remove(temp_path)
