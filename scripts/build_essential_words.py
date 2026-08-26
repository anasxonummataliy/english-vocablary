import json
import os
from pathlib import Path

pos_map = {
    "adj.": "adjective",
    "adj": "adjective",
    "v.": "verb",
    "v": "verb",
    "n.": "noun",
    "n": "noun",
    "adv.": "adverb",
    "adv": "adverb",
    "prep.": "preposition",
    "prep": "preposition",
    "conj.": "conjunction",
    "conj": "conjunction",
    "pron.": "pronoun",
    "pron": "pronoun",
    "intj.": "interjection",
    "intj": "interjection",
    "aux. v.": "auxiliary verb",
}


def clean_transcription(t: str) -> str:
    t = t.strip()
    if not t.startswith("/"):
        t = "/" + t
    if not t.endswith("/"):
        t = t + "/"
    return t


def clean_example(s: str) -> str:
    s = s.strip()
    if s.startswith("→"):
        s = s.lstrip("→").strip()
    return s


def clean_pos(tp: str) -> str:
    tp = tp.strip()
    return pos_map.get(tp.lower(), tp)


def build_from_sources(p_en: str, p_uz: str, output_dir: str = "data") -> None:
    with open(p_en, encoding="utf-8") as f:
        en_data = json.load(f)

    with open(p_uz, encoding="utf-8") as f:
        uz_data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    for book_idx in range(6):
        book_str = str(book_idx)
        book_num = book_idx + 1
        en_book = en_data[book_str]
        uz_book = uz_data[book_str]

        units = []
        for unit_idx in range(30):
            unit_str = str(unit_idx)
            unit_num = unit_idx + 1
            en_words = en_book[unit_str]
            uz_words = uz_book[unit_str]

            word_list = []
            for w_idx, en_w in enumerate(en_words):
                uz_w = uz_words[w_idx]
                word_obj = {
                    "id": f"eew{book_num}_u{unit_num}_{w_idx + 1}",
                    "word": en_w["w"].strip(),
                    "transcription": clean_transcription(en_w["t"]),
                    "part_of_speech": clean_pos(en_w["tp"]),
                    "uzbek": uz_w["w"].strip(),
                    "description": en_w["d"].strip(),
                    "example": clean_example(en_w["s"]),
                }
                word_list.append(word_obj)

            units.append({
                "unit": unit_num,
                "title": f"Unit {unit_num}",
                "topic": f"4000 Essential English Words {book_num} — Unit {unit_num}",
                "words": word_list,
            })

        result = {
            "book": f"4000 Essential English Words {book_num}",
            "edition": "Second Edition",
            "units": units,
        }

        out_file = Path(output_dir) / f"4000essentialenglishwords{book_num}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Generated {out_file}: {len(units)} units, {sum(len(u['words']) for u in units)} words")


if __name__ == "__main__":
    p_en = "/Users/anasxonummataliyev/.gemini/antigravity-ide/brain/3057b879-a051-49a0-858b-31a698d77895/.user_uploaded/media_1787763100013.json"
    p_uz = "/Users/anasxonummataliyev/.gemini/antigravity-ide/brain/3057b879-a051-49a0-858b-31a698d77895/.user_uploaded/media_1787763102185.json"
    build_from_sources(p_en, p_uz)
