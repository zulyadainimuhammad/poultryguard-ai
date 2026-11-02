from app.services.answer_generator import PoultryAnswerGenerator
from rag.retrieval import KnowledgeBaseRetriever

question = "How should a poultry house be cleaned and disinfected between flocks?"

print("1. Retrieving relevant evidence...")
retriever = KnowledgeBaseRetriever()
results = retriever.search(question, top_k=3)
print(f"Retrieved {len(results)} passages.")

print("\n2. Generating an answer with Groq...")
generator = PoultryAnswerGenerator()
generated = generator.generate(question, results)

print("\n--- POULTRYGUARD AI ANSWER ---\n")
print(generated.answer)

print("\n--- SOURCES ---")
for source in generated.sources:
    print(source)
