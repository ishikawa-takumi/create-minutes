document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('audioFile');
    const fileName = document.getElementById('fileName');
    const transcribeBtn = document.getElementById('transcribeBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultTextarea = document.getElementById('transcriptionResult');
    const copyBtn = document.getElementById('copyBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const clearBtn = document.getElementById('clearBtn');

    // Maximum file size (in bytes) - 500MB
    const MAX_FILE_SIZE = 500 * 1024 * 1024;

    // Drag and drop functionality
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => {
            dropArea.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => {
            dropArea.classList.remove('dragover');
        }, false);
    });

    dropArea.addEventListener('drop', (e) => {
        const file = e.dataTransfer.files[0];
        if (isValidAudioFile(file)) {
            if (isValidFileSize(file)) {
                handleFile(file);
            } else {
                showError('ファイルサイズが大きすぎます。500MB未満のファイルを選択してください。');
            }
        } else {
            showError('サポートされていないファイル形式です。音声ファイル（.mp3, .wav, .ogg, .m4a, .flac）を選択してください。');
        }
    }, false);

    // File input change
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            if (isValidAudioFile(file)) {
                if (isValidFileSize(file)) {
                    handleFile(file);
                } else {
                    showError('ファイルサイズが大きすぎます。500MB未満のファイルを選択してください。');
                    fileInput.value = '';
                }
            } else {
                showError('サポートされていないファイル形式です。音声ファイル（.mp3, .wav, .ogg, .m4a, .flac）を選択してください。');
                fileInput.value = '';
            }
        }
    });

    // Handle the selected file
    function handleFile(file) {
        fileName.textContent = file.name;
        transcribeBtn.disabled = false;
    }

    // Check if file is valid audio
    function isValidAudioFile(file) {
        const validTypes = ['audio/mp3', 'audio/wav', 'audio/ogg', 'audio/m4a', 'audio/flac', 'audio/mpeg'];
        return file && validTypes.includes(file.type) || /\.(mp3|wav|ogg|m4a|flac)$/i.test(file.name);
    }

    // Check if file size is valid
    function isValidFileSize(file) {
        return file.size <= MAX_FILE_SIZE;
    }

    // Transcribe button click
    transcribeBtn.addEventListener('click', async () => {
        if (!fileInput.files.length) return;

        const file = fileInput.files[0];
        // Check file size again before upload
        if (!isValidFileSize(file)) {
            showError('ファイルサイズが大きすぎます。500MB未満のファイルを選択してください。');
            return;
        }
        
        const formData = new FormData();
        formData.append('audio', file);

        // Show loading
        transcribeBtn.disabled = true;
        loadingIndicator.style.display = 'flex';
        resultTextarea.value = '';

        try {
            const response = await fetch('/api/transcribe', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                resultTextarea.value = data.transcription;
                copyBtn.disabled = false;
                downloadBtn.disabled = false;
                clearBtn.disabled = false;
            } else {
                let errorMessage = 'エラーが発生しました。再度お試しください。';
                if (response.status === 413) {
                    errorMessage = 'ファイルサイズが大きすぎます。500MB未満のファイルを選択してください。';
                }
                
                try {
                    const errorData = await response.json();
                    if (errorData.error) {
                        errorMessage = errorData.error;
                    }
                } catch (e) {
                    // If we can't parse JSON, just use the default error message
                }
                
                showError(errorMessage);
            }
        } catch (error) {
            showError('通信エラーが発生しました。インターネット接続を確認してください。');
            console.error('Error:', error);
        } finally {
            loadingIndicator.style.display = 'none';
            transcribeBtn.disabled = false;
        }
    });

    // Copy button
    copyBtn.addEventListener('click', () => {
        resultTextarea.select();
        document.execCommand('copy');
        showSuccess('テキストをクリップボードにコピーしました');
    });

    // Download button
    downloadBtn.addEventListener('click', () => {
        const text = resultTextarea.value;
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = 'transcription.txt';
        document.body.appendChild(a);
        a.click();
        
        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 0);
        
        showSuccess('テキストをダウンロードしました');
    });

    // Clear button
    clearBtn.addEventListener('click', () => {
        resultTextarea.value = '';
        copyBtn.disabled = true;
        downloadBtn.disabled = true;
        clearBtn.disabled = true;
    });

    // Show error message
    function showError(message) {
        const errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        errorElement.textContent = message;
        errorElement.style.cssText = `
            background-color: #ffdddd;
            color: #d8000c;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 5px solid #d8000c;
        `;
        
        // Insert before the loading indicator
        loadingIndicator.parentNode.insertBefore(errorElement, loadingIndicator);
        
        // Remove after 5 seconds
        setTimeout(() => {
            errorElement.remove();
        }, 5000);
    }

    // Show success message
    function showSuccess(message) {
        const successElement = document.createElement('div');
        successElement.className = 'success-message';
        successElement.textContent = message;
        successElement.style.cssText = `
            background-color: #ddffdd;
            color: #4F8A10;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 5px solid #4F8A10;
        `;
        
        // Insert at the top of result container
        document.querySelector('.result-container').insertBefore(successElement, document.querySelector('.result-container').firstChild);
        
        // Remove after 3 seconds
        setTimeout(() => {
            successElement.remove();
        }, 3000);
    }
});
