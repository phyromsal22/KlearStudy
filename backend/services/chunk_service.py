import re


class ChunkService:
    """
    Split extracted lesson text into manageable chunks.

    Default:
    - chunk size: 4000 characters
    - overlap: 400 characters
    """

    def __init__(
        self,
        chunk_size: int = 4000,
        overlap: int = 400,
    ):
        if chunk_size <= 0:
            raise ValueError(
                "chunk_size must be greater than 0."
            )

        if overlap < 0:
            raise ValueError(
                "overlap cannot be negative."
            )

        if overlap >= chunk_size:
            raise ValueError(
                "overlap must be smaller than chunk_size."
            )

        self.chunk_size = chunk_size
        self.overlap = overlap

    def clean_text(self, text: str) -> str:
        if not text:
            return ""

        # Normalize line endings
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Remove excessive spaces
        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )

        # Reduce excessive blank lines
        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        return text.strip()

    def split_text(self, text: str) -> list[str]:
        text = self.clean_text(text)

        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        chunks = []

        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(
                start + self.chunk_size,
                text_length,
            )

            # Try to end at a paragraph
            if end < text_length:
                paragraph_break = text.rfind(
                    "\n\n",
                    start,
                    end,
                )

                if (
                    paragraph_break > start
                    + int(self.chunk_size * 0.5)
                ):
                    end = paragraph_break

            # If no paragraph break,
            # try sentence boundary
            if end < text_length:
                sentence_break = max(
                    text.rfind(". ", start, end),
                    text.rfind("។ ", start, end),
                    text.rfind("? ", start, end),
                    text.rfind("! ", start, end),
                )

                if (
                    sentence_break > start
                    + int(self.chunk_size * 0.5)
                ):
                    end = sentence_break + 1

            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            if end >= text_length:
                break

            next_start = end - self.overlap

            if next_start <= start:
                next_start = end

            start = next_start

        return chunks

    def create_chunks(
        self,
        text: str,
    ) -> list[dict]:

        chunks = self.split_text(text)

        return [
            {
                "chunk_index": index,
                "text": chunk,
                "character_count": len(chunk),
            }
            for index, chunk in enumerate(
                chunks,
                start=1,
            )
        ]


chunk_service = ChunkService()