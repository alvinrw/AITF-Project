import json
import os
import random
from datasets import load_dataset

def mix_wikipedia_data(input_file="data/data_training_cpt.jsonl", output_file="data/data_training_mixed.jsonl", wiki_output_file="data/wikipedia_subset.jsonl", num_wiki_samples=5000):
    """
    Mengambil data Wikipedia Indonesia (subset 20231101.id) via streaming,
    memformatnya sesuai schema AITF, dan menggabungkannya dengan data lokal.
    Juga menyimpan subset Wikipedia asli ke file terpisah.
    """
    print(f"\n[🌐] Memulai proses data mixing (Wikipedia ID)...")
    
    # 1. Load Wikipedia Indonesia menggunakan mode streaming
    try:
        print(f"[*] Menghubungkan ke Hugging Face (streaming: wikimedia/wikipedia)...")
        ds_wiki = load_dataset("wikimedia/wikipedia", "20231101.id", split="train", streaming=True, trust_remote_code=True)
        wiki_subset = ds_wiki.take(num_wiki_samples)
    except Exception as e:
        print(f"[!] Gagal mengambil data Wikipedia: {e}")
        return False

    wiki_entries = []
    
    # 2. Format data Wikipedia
    print(f"[*] Memproses {num_wiki_samples} artikel Wikipedia...")
    for item in wiki_subset:
        # Format: "Judul: {title}. Isi: {text}" sesuai standar data_cleaner.py
        formatted_text = f"Judul: {item['title']}. Isi: {item['text']}"
        entry = {
            "text": formatted_text,
            "source_type": "wikipedia",
            "url": item.get('url', 'https://id.wikipedia.org')
        }
        wiki_entries.append(entry)

    # 2b. SIMPAN SUBSET WIKIPEDIA KE FILE TERPISAH (Sesuai permintaan USER)
    if wiki_output_file:
        os.makedirs(os.path.dirname(wiki_output_file), exist_ok=True)
        try:
            with open(wiki_output_file, 'w', encoding='utf-8') as f:
                for entry in wiki_entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"[✅] Subset Wikipedia disimpan di: {wiki_output_file}")
        except Exception as e:
            print(f"[⚠️] Gagal menyimpan subset Wikipedia: {e}")

    # 3. Baca data lokal (hasil crawling kemiskinan)
    mixed_entries = wiki_entries.copy()
    if os.path.exists(input_file):
        print(f"[*] Membaca data lokal: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    mixed_entries.append(json.loads(line))
    else:
        print(f"[⚠️] Warning: File {input_file} tidak ditemukan. Hasil hanya berisi Wikipedia.")

    # 4. Shuffle agar data pencampuran merata (penting untuk ngurangin bias training)
    print(f"[*] Mengacak (shuffling) {len(mixed_entries)} total entries...")
    random.shuffle(mixed_entries)

    # 5. Simpan ke file akhir (MIXED)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for entry in mixed_entries:
                outfile.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"[✅] Dataset CAMPURAN disimpan di: {output_file}")
        return True
    except Exception as e:
        print(f"[!] Gagal menyimpan file campuran: {e}")
        return False

if __name__ == "__main__":
    # Script ini relatif ke folder Crawl/
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    _input = os.path.join(_base_dir, "data", "data_training_cpt.jsonl")
    _output = os.path.join(_base_dir, "data", "data_training_mixed.jsonl")
    
    mix_wikipedia_data(input_file=_input, output_file=_output)
