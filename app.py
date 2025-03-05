#!/usr/bin/env python3
"""
Create a web application for generating meeting minutes from audio files
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from transcription import process_audio, allowed_audio_file, save_uploaded_audio

# Get the absolute path to the project directory
project_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(project_dir, 'static')

# Explicitly set the static folder path
app = Flask(__name__, static_folder=static_dir)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 最大100MBまでのファイルを許可

@app.route('/')
def index():
    """アプリケーションのホームページを表示"""
    return render_template('index.html')

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    """音声ファイルをアップロードして文字起こしする"""
    # ファイルが存在するか確認
    if 'audio' not in request.files:
        return jsonify({"error": "音声ファイルがありません"}), 400
        
    audio_file = request.files['audio']
    
    # ファイル名が空でないか確認
    if audio_file.filename == '':
        return jsonify({"error": "ファイルが選択されていません"}), 400
        
    # ファイル形式が正しいか確認
    if not allowed_audio_file(audio_file.filename):
        return jsonify({"error": "サポートされていない音声形式です"}), 400
    
    try:
        # 音声処理と文字起こし
        print(f"音声ファイルを文字起こしします: {audio_file.filename}")
        transcription = process_audio(audio_file)
        return jsonify({
            "success": True,
            "transcription": transcription
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def transcribe_audio(audio_path):
    """
    音声ファイルのパスを受け取り文字起こしを行う
    
    Args:
        audio_path: 音声ファイルのパス
        
    Returns:
        str: 文字起こし結果のテキスト
    """
    # project/whisper_inference.pyのtranscribe_audio関数を直接インポート
    from project.whisper_inference import transcribe_audio as whisper_transcribe
    
    try:
        # Whisperモデルによる文字起こし
        return whisper_transcribe(audio_path)
    except Exception as e:
        raise Exception(f"音声の文字起こしに失敗しました: {str(e)}")

def main():
    """コマンドラインからの実行時のエントリーポイント"""
    parser = argparse.ArgumentParser(description="音声からテキストを生成します")
    parser.add_argument("--server", action="store_true", help="Webサーバーとして起動する")
    
    args = parser.parse_args()
    
    if args.server:
        # Webサーバーモードで起動
        app.run(debug=True)
    else:
        # CLIモードで実行
        content = ""
        if args.audio:
            try:
                print(f"音声ファイルを文字起こしします: {args.audio}")
                content = transcribe_audio(args.audio)
                print("文字起こしが完了しました")
            except Exception as e:
                print(f"音声の文字起こしに失敗しました: {e}")
                return
                

if __name__ == "__main__":
    main()  # Changed from app.run(debug=True) to properly use the main function
