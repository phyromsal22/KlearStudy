def extract_text(file_path: str) -> str:
    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
    ]

    for encoding in encodings:
        try:
            with open(
                file_path,
                "r",
                encoding=encoding,
            ) as file:
                return file.read().strip()

        except UnicodeDecodeError:
            continue

    raise ValueError(
        "Unable to decode the text file."
    )