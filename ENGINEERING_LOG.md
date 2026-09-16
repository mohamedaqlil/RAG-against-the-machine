- 80% recall@5 for docs
- 50% for code
- maximum indexing time of 5 minutes

### Target 1: File Discovery & Baseline Chunking
- [ ] Recursively walk `data/raw/` and collect all `.py` and `.md` files.
- [ ] Filter out unwanted noise (`__pycache__`, `.git`, binaries).
- [ ] Implement a strict character-based chunker bounded by `max_chunk_size` (<= 2000 chars).
- [ ] Attach required metadata: `file_path`, `first_character_index`, `last_character_index`.
- [ ] Save output array to `data/processed/chunks.json`.
