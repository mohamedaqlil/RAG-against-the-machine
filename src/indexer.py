import math
import re
from collections import defaultdict

from nltk.stem import PorterStemmer


class InvertedIndex:
    def __init__(self):
        self.idf = {}
        self.inverted_index = defaultdict(dict)
        self.document_norms = {}

    def build(self, corpus):
        self.idf = inverse_document_frequency(corpus)
        for doc_id, tokens in corpus.items():
            doc_vector = tf_idf(tokens, self.idf)
            self.document_norms[doc_id] = vector_magnitude(doc_vector)
            for term, weight in doc_vector.items():
                self.inverted_index[term][doc_id] = weight

    def search(self, query_tokens, k=5):
        dot_scores = defaultdict(float)
        query_vector = tf_idf(query_tokens, self.idf)
        if not query_vector:
            return []

        for term, query_weight in query_vector.items():
            for doc_id in self.inverted_index[term]:
                dot_scores[doc_id] += (query_weight * self.inverted_index[term][doc_id])

        query_norm = vector_magnitude(query_vector)
        cosine_scores = defaultdict(float)

        for doc_id in dot_scores:
            cosine_scores[doc_id] = dot_scores[doc_id] / (query_norm * self.document_norms[doc_id])

        cosine_scores = sorted(cosine_scores.items(), key=lambda item: item[1], reverse=True)
        return cosine_scores[:k]


def load_stopwords():
    with open("data/stopwords.txt") as f:
        return {word.lower() for word in f.read().splitlines()}

stop_words = load_stopwords()

def tokenize_text(text: str, remove_stopwords=True, use_stemming=True):
    pattern = r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|\d+'
    tokens = re.findall(pattern, text)
    valid_tokens = []
    for token in tokens:
        if token:
            valid_tokens.append(token.lower())
    if remove_stopwords:
        filtered_words = []
        for word in valid_tokens:
            if word not in stop_words:
                filtered_words.append(word)
        valid_tokens = filtered_words
    if use_stemming:
        stemmer = PorterStemmer()
        stemmed_words = []
        for word in valid_tokens:
            stemmed_words.append(stemmer.stem(word))
        valid_tokens = stemmed_words

    return valid_tokens

def term_tokenizer(text):
    res = tokenize_text(text)
    if len(res) != 1:
        raise ValueError(f"'{text}' is invalid term")
    return res[0]

test_strings = [
    # 1. Normal English + capitalization
    "The cache is reading blocks",

    # 2. snake_case
    "get_cache_block_size",

    # 3. camelCase
    "getCacheBlockSize",

    # 4. PascalCase + acronym
    "KVCacheManager",

    # 5. Punctuation should create boundaries
    "cache-size, block.manager/get:value",

    # 6. Realistic Python expression
    "KVCacheManager.getBlockSize(max_num_blocks=128)",

    # 7. Stemming
    "reading reads managing manager blocks",

    # 8. Stop words
    "the cache is used for reading the blocks",

    # 9. Mixed code + English
    "The blockManager reads cached_blocks from KVCacheManager.",

    # 10. More realistic retrieval-style code
    "def getNumAvailableBlocks(self, max_num_seqs=128): return self.num_free_blocks",

    "!!! ___ ... () [] {}",
]

def term_counts(text_tokens):
    term_counter = defaultdict(int)
    for token in text_tokens:
        term_counter[token] += 1
    return dict(term_counter)

def term_frequency(text_tokens):
    if not text_tokens:
            raise ValueError(f"'{text_tokens}' is empty")
    term_frequencies = defaultdict(float)
    term_counter = term_counts(text_tokens)
    for token, count in term_counter.items():
        term_frequencies[token] = count / len(text_tokens)

    return dict(term_frequencies)

def document_frequency(corpus):
    df: dict = defaultdict(int)
    for text_tokens in corpus.values():
        for token in set(text_tokens):
            df[token] += 1
    return dict(df)

def inverse_document_frequency(corpus):
    idf: dict = defaultdict(float)
    df = document_frequency(corpus)
    l = len(corpus)
    for term, document_count in df.items():
            idf[term] = math.log(l/document_count)
    return dict(idf)

def tf_idf(token_texts, idf):
    tf = term_frequency(token_texts)
    tfidf = defaultdict(float)
    for token in tf:
        if token not in idf:
            continue
        tfidf[token] = tf[token] * idf[token]

    return dict(tfidf)

corpus = {
    "D1": ["cach", "cach", "manag"],
    "D2": ["cach", "schedul"],
    "D3": ["attent", "schedul"],
}


idf = inverse_document_frequency(corpus)

# print(idf)
# print(tf_idf(["cach", "cach", "manag"], idf))

query = {
    "cach": 0.4,
    "manag": 0.8
}

d1 = {
    "cach": 0.3,
    "manag": 0.5
}

d3 = {

    "attent": 0.4,

    "schedul": 0.8

}

d4 = {

    "other": 0.9,

    "cach": 0.3,

    "manag": 0.5

}

def dot_product(query, d):
    res = 0
    for term, query_v in query.items():
        res += (query_v * d.get(term, 0))
    return res

def vector_magnitude(vector):
    return math.sqrt(sum(x**2 for x in vector.values()))

def cosine_similarity(query, document):
    if not query or not document:
        return 0.0
    return dot_product(query, document) / (vector_magnitude(query) * vector_magnitude(document))


if "__name__" == "__main__":

    query = ["cach", "manag"]

    idf = inverse_document_frequency(corpus)

    query_vector = tf_idf(query, idf)
    scores = []

    for doc_id, tokens in corpus.items():
        scores.append((doc_id, cosine_similarity(query_vector, tf_idf(tokens, idf))))

    scores = sorted(scores, key=lambda score: score[1], reverse=True)
    # print(scores[:2])

    index = InvertedIndex()
    index.build(corpus)

    print(index.search(["cach", "manag"], k=2))
    print(index.search(["attent", "schedul"], k=2))
    print(index.search(["unknown"], k=2))
    print(index.search(["unknown", "cach", "manag"], k=2))

    # print(index.idf)
    # print(dict(index.inverted_index))
    # print(index.document_norms)

    # print(index.inverted_index["cach"])
    # print(index.inverted_index["manag"])

    dot_scores = defaultdict(float)

    for term, query_weight in query_vector.items():
        for doc_id in index.inverted_index[term]:
            dot_scores[doc_id] += (query_weight * index.inverted_index[term][doc_id])

    query_norm = vector_magnitude(query_vector)
    cosine_scores = defaultdict(float)

    for doc_id in dot_scores:
        cosine_scores[doc_id] = dot_scores[doc_id] / (query_norm * index.document_norms[doc_id])

    cosine_scores = sorted(cosine_scores.items(), key=lambda item: item[1], reverse=True)
