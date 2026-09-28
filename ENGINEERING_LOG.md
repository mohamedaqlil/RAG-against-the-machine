- 80% recall@5 for docs
- 50% for code
- maximum indexing time of 5 minutes

### Target 1: File Discovery & Baseline Chunking
- [ ] Recursively walk `data/raw/` and collect all `.py` and `.md` files.
- [ ] Filter out unwanted noise (`__pycache__`, `.git`, binaries).
- [ ] Implement a strict character-based chunker bounded by `max_chunk_size` (<= 2000 chars).
- [ ] Attach required metadata: `file_path`, `first_character_index`, `last_character_index`.
- [ ] Save output array to `data/processed/chunks.json`.


retrieval architecture:
docmap
  │
  ├── body_corpus
  │      ├── IDF
  │      ├── document length
  │      └── avgdl
  │
  └── build_search_corpus()
         ├── Python → body tokens
         └── Markdown
               ├── heading → normal
               ├── first meaningful chunk → normal
               └── later chunks → + heading context
                        │
                        ▼
                  search_corpus
                        │
                        ├── TF
                        └── postings
                              │
                              ▼
                       BM25 index
                       k1 = 0.8
                       b  = 1.0
