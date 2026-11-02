
from rag.retrieval import KnowledgeBaseRetriever

retriever = KnowledgeBaseRetriever()

question = "How should a poultry house be cleaned and disinfected between flocks?"
results = retriever.search(question, top_k=3)

print("Retrieved passages:", len(results))

for number, result in enumerate(results, start=1):
    print(f"\nResult {number}")
    print("Source:", result.get("source"))
    print("Section:", result.get("section"))
    print("Score:", round(result.get("score", 0), 3))
