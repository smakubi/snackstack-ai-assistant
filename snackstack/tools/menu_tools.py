"""
tools/menu_tools.py — Tools available to the Menu Agent.
"""

from langchain_core.tools import tool
from snackstack.tools.rag import menu_retriever


@tool
def search_menu_catalog(query: str) -> str:
    """Search the SnackStack menu catalog using semantic similarity.

    Use this to find dishes by name, cuisine, dietary preference, or description.

    Args:
        query: Natural language search query, e.g. 'vegan pasta' or 'spicy Indian starter'

    Returns:
        Formatted list of matching menu items with details.
    """
    results = menu_retriever.invoke(query)
    if not results:
        return "No matching dishes found for your query."

    output = f'Top {len(results)} matches for "{query}":\n\n'
    for doc in results:
        output += doc.page_content + "\n---\n"
    return output


# Convenient list for binding to the LLM / building ToolNodes
menu_tools_list = [search_menu_catalog]
