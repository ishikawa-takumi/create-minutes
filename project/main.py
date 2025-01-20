import sys
import subprocess
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from tqdm import tqdm

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <input_m4a_file>", file=sys.stderr)
        sys.exit(1)

    input_m4a = sys.argv[1]

    # Pythonコマンドのパス (現在動作中のPythonを使う場合)
    python_cmd = sys.executable

    # --- (1) Whisper推論をサブプロセスで呼び出す ---
    proc = subprocess.Popen(
        [python_cmd, "whisper_inference.py", input_m4a],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace"
    )

    stdout, stderr = proc.communicate()

    if proc.returncode != 0:
        print("サブプロセスでエラーが発生:", stderr, file=sys.stderr)
        sys.exit(1)

    recognized_text = stdout.strip()
    print("=== Recognized text ===")
    print(recognized_text)

    # ここでサブプロセスが終了 → サブプロセスで確保していた GPU メモリは OS レベルで解放

    # --- (2) Gemmaで要約・文法修正を行う処理 ---
    # 必要に応じてGPUを使うかどうか決める
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    model_name = "google/gemma-2-2b-jpn-it"

    # Gemma モデルとトークナイザをロード
    gemma_tokenizer = AutoTokenizer.from_pretrained(model_name)
    gemma_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch_dtype
    ).to(device)

    # --- (A) テキストをチャンク分割して、段階的に要約・文法修正 ---
    CHUNK_SIZE = 1024  # 例: 500文字ごとに分割（適宜調整してください）

    text_chunks = []
    current = 0

    while current < len(recognized_text):
        text_chunks.append(recognized_text[current:current + CHUNK_SIZE])
        current += CHUNK_SIZE

    summaries = []
    for chunk in tqdm(text_chunks):
        # 各チャンクごとに文法修正＋簡易要約
        prompt_text = (
            "以下のテキストを日本語の文法を修正しながら分かりやすくまとめてください：\n"
            + chunk
        )

        # トークナイズ
        input_ids = gemma_tokenizer(prompt_text, return_tensors="pt").input_ids.to(device)

        # Gemma推論
        outputs = gemma_model.generate(
            input_ids,
            max_new_tokens=128,      # 出力トークン数（大きすぎるとメモリ負荷増大）
            do_sample=True,
            top_p=0.95,
            temperature=0.2,
            repetition_penalty=1.05,
        )

        # 要約・修正結果
        corrected_text_chunk = gemma_tokenizer.decode(outputs[0], skip_special_tokens=True)
        summaries.append(corrected_text_chunk)

    # --- (B) 各チャンクの要約を結合し、さらに全体を再要約 ---
    all_text = "\n".join(summaries)

    # 最後に、全体を読みやすくまとめ直す
    final_prompt_text = (
        "以下の文章をより簡潔にまとめてください：\n" + all_text
    )

    input_ids = gemma_tokenizer(final_prompt_text, return_tensors="pt").input_ids.to(device)

    final_outputs = gemma_model.generate(
        input_ids,
        max_new_tokens=512,
        do_sample=True,
        top_p=0.95,
        temperature=0.2,
        repetition_penalty=1.05,
    )

    final_text = gemma_tokenizer.decode(final_outputs[0], skip_special_tokens=True)

    print("=== Gemma final summary text ===")
    print(final_text)

    # 必要に応じてファイルに書き出し
    with open("Corrected_Transcription.txt", "w", encoding="utf-8") as f:
        f.write(final_text)

if __name__ == "__main__":
    main()
