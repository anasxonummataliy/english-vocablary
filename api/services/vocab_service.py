import json
import random
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

BOOK_CONFIGS = [
    {
        "slug": "elementary",
        "file": "elementary.json",
        "title": "English Vocabulary in Use: Elementary",
        "short_title": "Elementary",
        "level": "A1 - A2",
        "icon": "🌱",
        "color": "#10b981",
        "description": "Boshlang'ich daraja uchun 60 ta kundalik mavzu va 1300+ so'z"
    },
    {
        "slug": "preintermediate",
        "file": "preintermediateintermediate.json",
        "title": "English Vocabulary in Use: Pre-intermediate & Intermediate",
        "short_title": "Pre-Intermediate",
        "level": "B1",
        "icon": "🚀",
        "color": "#34d399",
        "description": "O'rta daraja uchun 55 ta mavzu va 1100+ amaliy so'z"
    },
    {
        "slug": "essential1",
        "file": "4000essentialenglishwords1.json",
        "title": "4000 Essential English Words 1",
        "short_title": "4000 Words 1",
        "level": "A2",
        "icon": "⭐",
        "color": "#059669",
        "description": "Eng ko'p uchraydigan muhim 600 ta leksik so'z"
    },
    {
        "slug": "essential2",
        "file": "4000essentialenglishwords2.json",
        "title": "4000 Essential English Words 2",
        "short_title": "4000 Words 2",
        "level": "B1",
        "icon": "🔥",
        "color": "#10b981",
        "description": "Kundalik suhbat va matnlar uchun 600 ta asosiy so'z"
    },
    {
        "slug": "essential3",
        "file": "4000essentialenglishwords3.json",
        "title": "4000 Essential English Words 3",
        "short_title": "4000 Words 3",
        "level": "B1+",
        "icon": "⚡",
        "color": "#00ff87",
        "description": "Murakkabroq mavzular va 600 ta akademik so'z"
    },
    {
        "slug": "essential4",
        "file": "4000essentialenglishwords4.json",
        "title": "4000 Essential English Words 4",
        "short_title": "4000 Words 4",
        "level": "B2",
        "icon": "💎",
        "color": "#10b981",
        "description": "IELTS va CEFR B2 daraja uchun 600 ta boy leksika"
    },
    {
        "slug": "essential5",
        "file": "4000essentialenglishwords5.json",
        "title": "4000 Essential English Words 5",
        "short_title": "4000 Words 5",
        "level": "B2 - C1",
        "icon": "🏆",
        "color": "#34d399",
        "description": "Yuqori daraja uchun 600 ta professional so'z"
    },
    {
        "slug": "essential6",
        "file": "4000essentialenglishwords6.json",
        "title": "4000 Essential English Words 6",
        "short_title": "4000 Words 6",
        "level": "C1",
        "icon": "👑",
        "color": "#00ff87",
        "description": "C1 Advanced daraja uchun 600 ta yuqori darajadagi so'z"
    }
]


class VocabService:
    def __init__(self):
        self.books: dict[str, dict] = {}
        self.all_words_index: list[dict] = []
        self._load_data()

    def _load_data(self):
        self.books.clear()
        self.all_words_index.clear()

        for cfg in BOOK_CONFIGS:
            file_path = DATA_DIR / cfg["file"]
            if not file_path.exists():
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
                continue

            units_raw = content.get("units", [])
            units_list = []
            book_all_words = []

            for u in units_raw:
                unit_num = u.get("unit", 1)
                unit_title = u.get("title", f"Unit {unit_num}")
                unit_topic = u.get("topic", "")
                words = u.get("words", [])

                for w in words:
                    w_item = {
                        "id": w.get("id") or f"{cfg['slug']}_u{unit_num}_{w.get('word')}",
                        "word": (w.get("word") or "").strip(),
                        "transcription": (w.get("transcription") or "").strip(),
                        "part_of_speech": (w.get("part_of_speech") or "").strip(),
                        "uzbek": (w.get("uzbek") or "").strip(),
                        "description": (w.get("description") or "").strip(),
                        "example": (w.get("example") or "").strip(),
                        "book_slug": cfg["slug"],
                        "book_title": cfg["short_title"],
                        "unit_num": unit_num,
                    }
                    book_all_words.append(w_item)
                    self.all_words_index.append(w_item)

                units_list.append({
                    "unit_num": unit_num,
                    "title": unit_title,
                    "topic": unit_topic,
                    "word_count": len(words),
                    "words": words,
                })

            self.books[cfg["slug"]] = {
                "slug": cfg["slug"],
                "title": cfg["title"],
                "short_title": cfg["short_title"],
                "level": cfg["level"],
                "icon": cfg["icon"],
                "color": cfg["color"],
                "description": cfg["description"],
                "total_units": len(units_list),
                "total_words": len(book_all_words),
                "units": units_list,
                "_all_words": book_all_words,
            }

    def get_books_list(self) -> list[dict]:
        res = []
        for slug, b in self.books.items():
            res.append({
                "slug": b["slug"],
                "title": b["title"],
                "short_title": b["short_title"],
                "level": b["level"],
                "icon": b["icon"],
                "color": b["color"],
                "description": b["description"],
                "total_units": b["total_units"],
                "total_words": b["total_words"]
            })
        return res

    def get_units(self, book_slug: str) -> list[dict]:
        book = self.books.get(book_slug)
        if not book:
            return []
        return [
            {
                "unit_num": u["unit_num"],
                "title": u["title"],
                "topic": u["topic"],
                "word_count": u["word_count"]
            }
            for u in book["units"]
        ]

    def get_words(self, book_slug: str, unit_num: int) -> dict:
        book = self.books.get(book_slug)
        if not book:
            return {"unit": None, "words": []}

        for u in book["units"]:
            if u["unit_num"] == unit_num:
                # Add slug & unit
                formatted_words = []
                for w in u["words"]:
                    formatted_words.append({
                        "id": w.get("id") or f"{book_slug}_u{unit_num}_{w.get('word')}",
                        "word": (w.get("word") or "").strip(),
                        "transcription": (w.get("transcription") or "").strip(),
                        "part_of_speech": (w.get("part_of_speech") or "").strip(),
                        "uzbek": (w.get("uzbek") or "").strip(),
                        "description": (w.get("description") or "").strip(),
                        "example": (w.get("example") or "").strip(),
                        "book_slug": book_slug,
                        "unit_num": unit_num,
                    })
                return {
                    "book_slug": book_slug,
                    "book_title": book["short_title"],
                    "unit_num": unit_num,
                    "title": u["title"],
                    "topic": u["topic"],
                    "words": formatted_words
                }
        return {"unit": None, "words": []}

    def search(self, query: str, limit: int = 50) -> list[dict]:
        q = query.strip().lower()
        if not q:
            return []
        
        matches = []
        for w in self.all_words_index:
            if q in w["word"].lower() or q in w["uzbek"].lower():
                matches.append(w)
                if len(matches) >= limit:
                    break
        return matches

    def generate_quiz(self, book_slug: str, unit_num: Optional[int] = None, count: int = 10, mode: str = "en_uz") -> list[dict]:
        book = self.books.get(book_slug)
        if not book:
            return []

        pool = []
        if unit_num:
            for u in book["units"]:
                if u["unit_num"] == unit_num:
                    pool = u["words"]
                    break
        if not pool or len(pool) < 4:
            pool = book["_all_words"]

        if not pool:
            return []

        selected = random.sample(pool, min(count, len(pool)))
        questions = []

        all_uz_options = [w["uzbek"] for w in book["_all_words"] if w.get("uzbek")]
        all_en_options = [w["word"] for w in book["_all_words"] if w.get("word")]

        for item in selected:
            correct_word = item["word"]
            correct_uzbek = item["uzbek"]

            if mode == "en_uz":
                question_text = correct_word
                correct_answer = correct_uzbek
                distractor_pool = [opt for opt in all_uz_options if opt != correct_answer]
                distractors = random.sample(distractor_pool, min(3, len(distractor_pool)))
            else:
                question_text = correct_uzbek
                correct_answer = correct_word
                distractor_pool = [opt for opt in all_en_options if opt.lower() != correct_answer.lower()]
                distractors = random.sample(distractor_pool, min(3, len(distractor_pool)))

            options = distractors + [correct_answer]
            random.shuffle(options)

            questions.append({
                "id": item.get("id"),
                "question": question_text,
                "transcription": item.get("transcription", ""),
                "part_of_speech": item.get("part_of_speech", ""),
                "description": item.get("description", ""),
                "example": item.get("example", ""),
                "correct": correct_answer,
                "options": options,
                "mode": mode,
                "word": item["word"],
                "uzbek": item["uzbek"]
            })

        return questions

    def generate_speed_match(self, book_slug: str, unit_num: Optional[int] = None, count: int = 6) -> list[dict]:
        book = self.books.get(book_slug)
        if not book:
            return []

        pool = []
        if unit_num:
            for u in book["units"]:
                if u["unit_num"] == unit_num:
                    pool = u["words"]
                    break
        if not pool or len(pool) < count:
            pool = book["_all_words"]

        if not pool:
            return []

        selected = random.sample(pool, min(count, len(pool)))
        pairs = []
        for idx, item in enumerate(selected):
            pairs.append({
                "id": f"p_{idx}",
                "word": item["word"],
                "uzbek": item["uzbek"],
                "transcription": item.get("transcription", ""),
            })
        return pairs


vocab_service = VocabService()
