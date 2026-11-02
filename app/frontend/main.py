
"""Streamlit interface for the PoultryGuard AI MVP."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.retrieval import KnowledgeBaseRetriever
from app.services.answer_generator import PoultryAnswerGenerator


st.set_page_config(
    page_title="PoultryGuard AI",
    page_icon="🐔",
    layout="wide",
)

st.title("🐔 PoultryGuard AI")
st.subheader("Your poultry knowledge assistant")

st.write(
    "Ask questions about poultry farming, biosecurity, housing, "
    "flock management and other topics covered by the knowledge base."
)

st.info(
    "Answers are generated from retrieved knowledge-base passages. "
    "They may be incomplete or incorrect and do not replace advice "
    "from a qualified poultry veterinarian."
)


@st.cache_resource
def get_retriever():
    return KnowledgeBaseRetriever(
        index_path=PROJECT_ROOT / "vector_store" / "poultryguard.faiss",
        metadata_path=PROJECT_ROOT / "vector_store" / "metadata.json",
    )


@st.cache_resource
def get_answer_generator():
    return PoultryAnswerGenerator()


with st.sidebar:
    st.header("Search settings")

    top_k = st.slider(
        "Evidence passages",
        min_value=1,
        max_value=10,
        value=5,
        help="Choose how many knowledge-base passages to retrieve.",
    )

    st.caption(
        "More passages can provide additional context, "
        "but may also introduce less relevant information."
    )


with st.form("poultry_question_form"):
    question = st.text_area(
        "What would you like to know?",
        placeholder=(
            "Example: How should a poultry house be cleaned "
            "and disinfected between flocks?"
        ),
        height=110,
    )

    submitted = st.form_submit_button(
        "Ask PoultryGuard AI",
        type="primary",
        use_container_width=True,
    )


if submitted:
    if not question.strip():
        st.warning("Please enter a question.")

    else:
        try:
            with st.spinner("Finding relevant evidence..."):
                passages = get_retriever().search(
                    question.strip(),
                    top_k=top_k,
                )

            if not passages:
                st.warning(
                    "No relevant passages were found. Try rephrasing "
                    "your question or consult a poultry professional."
                )

            else:
                with st.spinner("Generating an evidence-based answer..."):
                    result = get_answer_generator().generate(
                        question=question.strip(),
                        passages=passages,
                    )

                st.subheader("Answer")
                st.markdown(result.answer)

                st.subheader("Supporting sources")

                for number, source in enumerate(result.sources, start=1):
                    source_path = str(
                        source.get("source", "Unknown source")
                    )
                    section = str(
                        source.get("section", "Unspecified section")
                    )
                    score = source.get("score")

                    heading = f"{number}. {section}"

                    if score is not None:
                        heading += (
                            f" — similarity {float(score):.3f}"
                        )

                    with st.expander(heading):
                        st.markdown(f"**Source file:** `{source_path}`")

                        st.caption(
                            "Similarity indicates retrieval relevance, "
                            "not factual accuracy."
                        )

        except ValueError as exc:
            st.error(str(exc))

        except Exception as exc:
            st.error(
                "PoultryGuard could not complete the request. "
                "Check your API access, model availability and "
                "terminal output, then try again."
            )
            st.caption(f"{type(exc).__name__}: {exc}")


st.divider()

st.caption(
    "PoultryGuard AI | Local knowledge retrieval + Groq answer generation"
)
