### 🎯 Execution Pipeline

```
1. Discover Files
       ↓
2. Chunking Strategy (Structure-Aware / Fixed)
       ↓
3. Docmap & Metadata Assignment (Assign chunk IDs & spans)
       ↓
4. Tokenization & Inverted Index Building
       ↓
5. TF-IDF / BM25 Matrix Calculation & Persistence
       ↓
6. Retrieval & Ranking

```

---

### Detailed Step-by-Step Breakdown

#### 1. Discover Files

* Walk the directory tree under `data/raw/`.


* Filter exclusively for `.py` and `.md` files.


* Skip unwanted artifacts (`.git`, `.venv`, `__pycache__`, binaries).



#### 2. Read + Chunk Each File (FIRST!)

Split the text into chunks **strictly bounded by `--max_chunk_size` ($\le 2000$ characters)** so the evaluation moulinette does not reject your retrieval outputs.

* **Python code:** Split by function/class boundaries (using `ast`) or fallback to line limits.


* **Markdown:** Split by headers/sections (`#`, `##`).



#### 3. Assign Chunk IDs & Build the Docmap

As you generate each chunk, assign a unique `chunk_id` and create your `docmap`:

```python
# Unique ID format
chunk_id = f"{file_path}::{start_char}_{end_char}"

# docmap entry
docmap[chunk_id] = {
    "file_path": relative_file_path,  # Must match data/raw/... verbatim
    "first_character_index": start_char,
    "last_character_index": end_char,
    "content": chunk_text,
}

```

#### 4. Tokenization & Inverted Index Building

Tokenize each **chunk's text** (lowercasing, code identifier splitting like `snake_case`). Map each token to the list of `chunk_id`s where it appears:

$$\text{inverted\_index: } \{\text{token} \rightarrow [\text{chunk\_id}_1, \text{chunk\_id}_2, \dots]\}$$

#### 5. Calculate TF-IDF / BM25 & Persist

Compute the Term Frequency for each chunk and the Inverse Document Frequency across **all chunks in your corpus**.

* Save the `inverted_index`, `docmap`, and `idf_dict` (or `TfidfVectorizer` / `BM25` matrix) to `data/processed/` using `pickle` or `joblib`.



#### 6. Retrieval & Ranking

At search time:

1. Tokenize the user's query.


2. Look up matching `chunk_id`s from the `inverted_index`.


3. Compute TF-IDF or BM25 similarity scores for candidate chunks.


4. Sort by score and use `docmap[chunk_id]` to return top-$k$ `MinimalSource` objects (`file_path`, `first_character_index`, `last_character_index`).



---
