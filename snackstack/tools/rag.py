"""
tools/rag.py — Build and expose the ChromaDB menu retriever for SnackStack.

Called once at import time; the retriever is then used by menu_tools.
"""

from langchain_core.documents import Document
from langchain_chroma import Chroma

from snackstack.data.menu import MENU_CATALOG
from snackstack.config import embeddings


def build_documents() -> list[Document]:
    """Convert the menu catalog into LangChain Documents."""
    docs: list[Document] = []
    for item in MENU_CATALOG:
        content = (
            f"Dish: {item['name']}\n"
            f"Category: {item['category']} | Cuisine: {item['cuisine']}\n"
            f"Price: ₹{item['price']} | Rating: {item['rating']}/5\n"
            f"Dietary: {', '.join(item['dietary_tags']) if item['dietary_tags'] else 'None'}\n"
            f"Description: {item['description']}\n"
            f"Available: {'Yes' if item['available'] else 'No'}"
        )
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "id": item["id"],
                    "name": item["name"],
                    "price": item["price"],
                },
            )
        )
    return docs


def build_retriever(k: int = 3):
    """Create the ChromaDB vector store and return a retriever."""
    docs = build_documents()
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name="snackstack_menu",
    )
    return vectorstore.as_retriever(search_kwargs={"k": k})


# Singleton retriever — built once when this module is first imported
menu_retriever = build_retriever()
