import re
from pathlib import Path
from typing import List

from src.schema.types import SentenceRecord
from src.utils.io import read_text_files


class TextCleaner:
    def clean_text(self, text: str) -> str:
        text = text.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n+", "\n", text)
        return text.strip()

    def split_sentences(self, text: str) -> List[str]:
        merged = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
        if not merged:
            return []

        # 切割方式：中文的。！？!?；;之后，或者英文的.之后跟着空格并且下一个字符是大写字母、数字或汉字
        sentences = re.split(r"(?<=[。！？!?；;])\s+|(?<=[.])\s+(?=[A-Z0-9\u4e00-\u9fff])", merged)
        return [sentence.strip() for sentence in sentences if sentence.strip()]


def preprocess_raw_texts(raw_dir: Path) -> List[SentenceRecord]:
    cleaner = TextCleaner()
    sentences: List[SentenceRecord] = []

    for record in read_text_files(raw_dir):
        cleaned_text = cleaner.clean_text(record["content"])
        for sentence_index, sentence in enumerate(
            cleaner.split_sentences(cleaned_text), start=1
        ):
            sentences.append(
                SentenceRecord(
                    text_id=record["text_id"],
                    sentence_id=sentence_index,
                    text=sentence,
                )
            )

    return sentences
