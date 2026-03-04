import json
import os
import re

class DataCleaner:
    def __init__(self, input_dir="data_raw", output_file="data_training_cpt.jsonl"):
        self.input_dir = input_dir
        self.output_file = output_file

        self.noise_patterns = [
            r"Facebook", r"Twitter", r"WhatsApp", r"Telegram", r"Instagram",
            r"Follow us", r"Share this", r"Bagikan artikel", r"Bagikan ke",
            r"Klik di sini", r"Baca Juga[:\s]*", r"Artikel Terkait[:\s]*",
            r"Post Selanjutnya[:\s]*", r"Lihat Komentar", r"Tulis Komentar",
            r"Copyright.*?Reserved", r"All Rights Reserved",
            r"Powered by \S+", r"©\s*\d{4}.*",
            r"Skip to content", r"Quick Menu", r"Daftar Isi",
            r"Back to top", r"Kembali ke atas",
            r"Home\s*[>\|•]", r"Beranda\s*[>\|•]",
            r"Menu\s+(Utama|Navigasi)",
            r"Tags?:", r"Kategori:", r"Label:",
            r"Edit(ed)?(\s+by)?:?",
            r"rizal\s*hadizan", r"rizalhadizan",
            # Typo bawaan web Dinsos
            r"Detail Beria",
            # Tanggal
            r"(Senin|Selasa|Rabu|Kamis|Jumat|Sabtu|Minggu),\s+\d+\s+\w+\s+\d{4}",
            r"\d{1,2}/\d{1,2}/\d{4}",
            # Inisial penulis: (din), (ant), (red), dll
            r"\(\s*[a-z]{2,4}\s*\)",
            # Navigasi jurnal/OJS
            r"QUICK MENU", r"EDITORIAL TEAM", r"PEER REVIEW",
            r"AUTHOR GUIDELINES", r"PUBLICATION ETHICS",
            r"View My Stats", r"ISSN \d+-\d+",
        ]

        self.boilerplate_triggers = [
            r"Berita Terkait", r"Artikel Terkait", r"Lihat Juga",
            r"Rekomendasi Artikel", r"Artikel Lainnya",
            r"Topik Terkait", r"Simak Berita", r"Baca Berikutnya",
            r"Editor\s*:", r"Penulis\s*:",
            # Penanda daftar link spesifik Dinsos Jatim
            r"Masuk Titik Ke-\d+", r"Gubernur Khofifah Salurkan",
            # Penutup jurnal/OJS
            r"Refbacks", r"Daftar Pustaka", r"References",
            r"Rumah Jurnal IAIN",
        ]

    def remove_boilerplate_tail(self, text):
        """Potong teks mulai dari frasa penanda berita terkait/navigasi."""
        for trigger in self.boilerplate_triggers:
            match = re.search(trigger, text, flags=re.IGNORECASE)
            if match:
                text = text[:match.start()].strip()
        return text

    def deduplicate_paragraphs(self, text):
        """
        Deduplikasi dua lapis:
        1. Per baris (\n) untuk teks yang masih punya newline
        2. Per kalimat untuk teks yang sudah di-collapse jadi satu baris
        Gunakan fingerprint 50 karakter pertama.
        """
        seen = set()
        unique = []

        # Lapis 1: coba split per \n dulu
        chunks = text.split('\n')
        # Kalau hasilnya cuma 1 chunk (teks sudah 1 baris), split per kalimat
        if len(chunks) <= 1:
            chunks = re.split(r'(?<=[.!?])\s+', text)

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            fingerprint = re.sub(r'\s+', '', chunk[:50].lower())
            if fingerprint and fingerprint not in seen:
                seen.add(fingerprint)
                unique.append(chunk)

        return ' '.join(unique)

    def is_garbage(self, text):
        """Skip file yang teksnya rusak binary atau terlalu pendek."""
        if not text or len(text) < 100:
            return True, "teks kosong/terlalu pendek"
        non_print = sum(1 for c in text if ord(c) < 32 and c not in '\n\t\r ')
        if non_print / len(text) > 0.05:
            return True, "karakter binary"
        alpha = sum(1 for c in text if c.isalpha())
        if alpha / len(text) < 0.30:
            return True, "rasio huruf rendah"
        return False, ""

    def clean_text(self, text):
        # 1. Potong ekor boilerplate & inisial penulis lebih dulu
        text = self.remove_boilerplate_tail(text)

        # 2. Hapus noise patterns
        for pattern in self.noise_patterns:
            text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

        # 3. Hapus sisa tag HTML, entities, dan URL
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&[a-zA-Z]{2,6};', ' ', text)
        text = re.sub(r'http\S+|www\.\S+', '', text)

        # 4. Filter karakter non-ASCII
        text = re.sub(r'[^\w\s\.,;:()\-\'"!?]', ' ', text)

        # 5. Deduplikasi paragraf/kalimat
        text = self.deduplicate_paragraphs(text)

        # 6. Rapikan spasi
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def process_all(self):
        files = [f for f in os.listdir(self.input_dir) if f.endswith('.json')]
        saved = 0
        skipped_garbage = 0
        skipped_short = 0

        with open(self.output_file, 'w', encoding='utf-8') as outfile:
            for filename in sorted(files):
                filepath = os.path.join(self.input_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception as e:
                    # Spesifik: hanya tangkap error baca file, bukan semua error
                    print(f"[!] Skip (error baca): {filename} — {e}")
                    skipped_garbage += 1
                    continue

                raw_content = data.get('content', '')
                title = data.get('metadata', {}).get('title', 'Tanpa Judul')
                source_type = data.get('metadata', {}).get('source_type', '')
                url = data.get('metadata', {}).get('url', '')

                garbage, reason = self.is_garbage(raw_content)
                if garbage:
                    print(f"[✗] SKIP (garbage - {reason}): {filename[:55]}")
                    skipped_garbage += 1
                    continue

                clean_content = self.clean_text(raw_content)

                if len(clean_content) > 350:
                    formatted_text = f"Judul: {title}. Isi: {clean_content}"
                    entry = {
                        "text": formatted_text,
                        "source_type": source_type,   # berguna saat fine-tuning
                        "url": url
                    }
                    outfile.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    saved += 1
                    print(f"[✓] Saved: {title[:55]}")
                else:
                    print(f"[✗] SKIP (terlalu pendek setelah clean): {filename[:55]}")
                    skipped_short += 1

        print(f"\n{'='*55}")
        print(f"[DONE] Saved          : {saved} dokumen")
        print(f"[DONE] Skip garbage   : {skipped_garbage} file")
        print(f"[DONE] Skip pendek    : {skipped_short} file")
        print(f"[DONE] Output         : {self.output_file}")

if __name__ == "__main__":
    cleaner = DataCleaner()
    cleaner.process_all()
