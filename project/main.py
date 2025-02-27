import sys
import subprocess
import os
import torch
from dotenv import load_dotenv
from huggingface_hub import login
from transformers import AutoModelForCausalLM, AutoTokenizer
from tqdm import tqdm

# Load environment variables from .env file
load_dotenv()

os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
os.environ["TORCH_USE_CUDA_DSA"] = "1"

# Use environment variable for HF token
access_token = os.environ.get("HF_TOKEN")
if access_token:
    login(token=access_token)
else:
    print("Warning: HF_TOKEN environment variable not set. Some features may not work correctly.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <input_m4a_file>", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    python_cmd = sys.executable

    if input_file.endswith(".m4a"):
        # Whisper推論
        proc = subprocess.Popen([python_cmd, "whisper_inference.py", input_file],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, encoding="utf-8", errors="replace")
        stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            print("サブプロセスでエラーが発生:", stderr, file=sys.stderr)
            sys.exit(1)

        recognized_text = stdout.strip()
        file = open("transcription.txt", "w", encoding="utf-8")
        file.write(recognized_text)
        file.close()
    elif input_file.endswith(".txt"):
        with open(input_file, "r", encoding="utf-8") as f:
            recognized_text = f.read().strip()
    else:
        print("Unsupported file type. Please provide a .m4a or .txt file.", file=sys.stderr)
        sys.exit(1)

    print("=== Recognized text ===")
    print(recognized_text)

    # デバイス選択
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    model_name = "google/gemma-2-2b-jpn-it"
    gemma_tokenizer = AutoTokenizer.from_pretrained(model_name)
    gemma_model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch_dtype).to(device)

    # Create overlapping text chunks
    chunk_size = 1024
    overlap = 100
    text_chunks = [recognized_text[i:i + chunk_size] for i in range(0, len(recognized_text), chunk_size - overlap)]

    summaries = []
    for chunk in tqdm(text_chunks):
        prompt_text = "以下のテキストを要約してください：\n" + chunk
        input_ids = gemma_tokenizer(prompt_text, return_tensors="pt").input_ids.to(device)

        if input_ids.numel() == 0:
            print("Warning: input_ids is empty. Skipping this chunk.")
            continue

        max_length = gemma_model.config.max_position_embeddings
        max_new_tokens = min(128, max_length - input_ids.shape[1])

        outputs = gemma_model.generate(input_ids, max_new_tokens=max_new_tokens, do_sample=False)
        summaries.append(gemma_tokenizer.decode(outputs[0], skip_special_tokens=True))

    final_text = "\n".join(summaries)

    # Summarize the concatenated summaries
    prompt_text = "以下は議事録を細切れにして、それぞれ要約して、再度結合した文章です。さらに、要約してく、議事録として提示してください。：\n" + final_text
    input_ids = gemma_tokenizer(prompt_text, return_tensors="pt").input_ids.to(device)

    if input_ids.numel() > 0:
        max_length = gemma_model.config.max_position_embeddings
        max_new_tokens = max(1, min(128, max_length - input_ids.shape[1]))  # Ensure max_new_tokens is greater than 0

        outputs = gemma_model.generate(input_ids, max_new_tokens=max_new_tokens, do_sample=False)
        final_summary = gemma_tokenizer.decode(outputs[0], skip_special_tokens=True)
    else:
        final_summary = "Warning: input_ids is empty. No final summary generated."

    with open("Corrected_Transcription.txt", "w", encoding="utf-8") as f:
        f.write(final_summary)

if __name__ == "__main__":
    main()
