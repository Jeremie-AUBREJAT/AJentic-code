def chunk_text(text, max_chars=12000):
    """
    Chunk intelligent pour code (PHP / JS / WP plugins)
    - évite fragmentation excessive
    - garde cohérence fonctionnelle
    """

    if len(text) <= max_chars:
        return [text]

    chunks = []
    buffer = []

    current_size = 0

    lines = text.splitlines(keepends=True)

    for line in lines:

        # si gros bloc → flush
        if current_size + len(line) > max_chars:
            chunks.append("".join(buffer))
            buffer = [line]
            current_size = len(line)
        else:
            buffer.append(line)
            current_size += len(line)

    if buffer:
        chunks.append("".join(buffer))

    return chunks