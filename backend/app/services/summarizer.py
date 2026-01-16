from __future__ import annotations
from typing import List, Dict, Any
import logging
from .searcher import search_chunks

import ollama

logger = logging.getLogger(__name__)

'''
Turns a list of chunks from search_chunks() into a context string
'''
def build_context(chunks: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    
    # Loop through each chunk starting at 1. Get the index and chunk value
    for idx, chunk in enumerate(chunks, start=1):

        #Get file_path and score from chunk if possible. And provide defaults if not.
        file_path = chunk.get("file_path", "<unknown>")
        score = chunk.get("score", None)

        # Format header based on whether score exists
        if score is not None:
            header = f"[{idx}] ({file_path}) [Score: {score:.3f}]"
        else:
            header = f"[{idx}] ({file_path})"

        lines.append(header)

        # Get and clean chunk text and set it empy if it doesn't exist
        text = (chunk.get("text") or "").strip()
        lines.append(text)
        lines.append("")  # Add a blank line after each chunk

    return "\n".join(lines)

'''
Builds prompt for LLM based on query and context

@param query: User query
@param context: Context string built from relevant chunks
'''
def make_prompt(query: str, context: str) -> str:
    
    prompt = f"""You are an AI assistant that answers question using ONLY, and I repeat ONLY the notes provided below. 
    If the notes do not contain the answer, you MUST say "I don't know based on the notes."

    --- NOTES BEGIN ---
{context}
--- NOTES END ---

Question: {query}
Answer:"""

    return prompt



'''
Calls the LLM model with the built prompt to get an answer

@param prompt: The prompt string to send to the LLM
'''
def call_llm(prompt: str) -> str:
    try:
        response = ollama.chat(
           model = "llama3.2",
           messages=[
               {"role": "user", "content": prompt}
               ],
        )

        content = response.get("message", {}).get("content", "")
        return content.strip() if content else "Model returned empty response."
    except Exception as e:
       logger.error("Error calling local LLM: %s", e)
       return "There was an error calling the model. Check the logs for details."
         


def summarize_answer(query: str, context: str) -> str:
    """
    Simple helper used by tests: given a query and a context string,
    build a prompt and return only the model's answer text.
    """
    cleaned_query = query.strip()
    cleaned_context = (context or "").strip()

    if not cleaned_query:
        return "Query is empty. Please provide a question."

    prompt = make_prompt(cleaned_query, cleaned_context)
    return call_llm(prompt)


'''
Retrieves chunks, build prompt, and calls LLM to get answer
'''
def answer_query(query: str, top_k: int = 5) -> Dict[str, Any]:
    # Clean the query
    cleaned_query = query.strip()

    # Ensure query is not empty. Provide message if it is.
    if not cleaned_query:
        return {
          "query": query,
          "answer": "Query, is empty. Please provide a question.",
          "chunks": [],
        }
    
    # Search for relevant chunks
    chunks = search_chunks(cleaned_query, top_k=top_k)

    # If no chunks found, return message
    if not chunks:
        logger.info("No relevant chunks found for the query: %r", cleaned_query)
        return {
            "query": query,
            "answer": "I could not find any relevant information in the notes.",
            "chunks": [],
        }
    
    # Build context from chunks
    context = build_context(chunks)

    # Build prompt for LLM
    prompt = make_prompt(cleaned_query, context)

    # Call LLM
    answer = call_llm(prompt)

    return {
        "query": query,
        "answer": answer,
        "chunks": chunks,
    }