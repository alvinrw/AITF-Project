import os
import re
import time
import logging
from urllib.parse import urlparse
from duckduckgo_search import DDGS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_domain(url):
    try:
        domain = urlparse(url).netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return "".join(c for c in domain if c.isalnum() or c in ('-', '.')) or "unknown"
    except:
        return "unknown"

def parse_keyword_line(line):
    match = re.match(r'^(.*?)\((.+)\)$', line.strip())
    if match:
        keyword = match.group(1).strip()
        domains = re.findall(r'site:([^\s)]+)', match.group(2))
        return keyword, domains
    return line.strip(), []

def main():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    keyword_file = os.path.join(BASE_DIR, 'data', 'keywords.txt')
    output_dir = os.path.join(BASE_DIR, 'data', 'urls')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(keyword_file, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]

    logging.info(f"Ditemukan {len(lines)} keyword.")

    main_output_file = os.path.join(output_dir, 'list_url.txt')
    seen_urls = set()
    total = 0

    for idx, line in enumerate(lines, 1):
        keyword, domains = parse_keyword_line(line)
        logging.info(f"[{idx}/{len(lines)}] Keyword: {keyword[:50]}, {len(domains)} domain")

        targets = domains if domains else ['']

        for domain in targets:
            query = f"{keyword} site:{domain}" if domain else keyword

            try:
                with DDGS() as ddgs:
                    results = ddgs.text(query, region='id-id', max_results=5)
                    for item in results:
                        url = item.get('href', '')
                        if not url or url in seen_urls:
                            continue
                        seen_urls.add(url)

                        # Langsung tulis begitu dapat URL
                        with open(main_output_file, 'a', encoding='utf-8') as f_main:
                            f_main.write(url + '\n')

                        d = get_domain(url)
                        with open(os.path.join(output_dir, f"{d}.txt"), 'a', encoding='utf-8') as fd:
                            fd.write(url + '\n')

                        total += 1
                        logging.info(f"  - [{total}] {url}")

            except Exception as e:
                logging.error(f"Error: {e}")
                time.sleep(10)

            time.sleep(2)

        time.sleep(2)

    logging.info(f"Selesai! Total {total} URL unik.")

if __name__ == "__main__":
    main()
