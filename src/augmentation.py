def build_context(results, docmap):
    sources = []

    for chunk_id, score in results:
        source = docmap[chunk_id]

        sources.append(source)

    return sources
