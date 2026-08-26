# RAG (Retrieval-Augmented Generation) — Reference Facts

This file is the source of truth for the `accurate_grounded` checkpoint.
A lesson claim **fails** only if it directly contradicts something here,
or introduces a specific non-obvious fact that this reference doesn't
support. Basic, widely accepted claims consistent with this reference
still pass even if not stated verbatim.

---

## What RAG Is

- RAG stands for Retrieval-Augmented Generation.
- RAG is a technique that combines information retrieval with text generation.
- RAG connects a large language model (LLM) to an external knowledge source
  so the model can look up information before answering.
- The core idea: instead of relying only on what the model memorized during
  training, RAG lets the model fetch relevant, up-to-date information at
  the time a question is asked.
- RAG was introduced in a 2020 research paper by Lewis et al. at Meta AI
  (Facebook AI Research).
- RAG systems have three main components: a retriever, a knowledge base
  (or document store), and a generator (the language model).

## Why RAG Matters

- LLMs are trained on data up to a certain date — they have a knowledge
  cutoff and cannot know about events or information after that date.
- LLMs can "hallucinate" — generate text that sounds confident and correct
  but is actually factually wrong or made up.
- RAG provides the model with retrieved documents to ground its answers,
  which can help reduce hallucination.
- RAG allows a model to access domain-specific or private information
  (e.g. a company's internal documents) that was never part of its
  training data.
- RAG keeps the knowledge source separate from the model, making it easy
  to update information without retraining the entire model.

## How RAG Works — The Step-by-Step Process

1. **User asks a question** (the query).
2. **Retrieval step:** The system searches a knowledge base to find
   documents or passages that are relevant to the question.
   - The knowledge base typically stores documents as numerical
     representations called "embeddings" (also called "vectors").
   - An embedding is a list of numbers that captures the meaning of a
     piece of text, so that similar meanings produce similar numbers.
   - The retriever converts the user's question into an embedding and
     finds the closest-matching document embeddings using a similarity
     search (e.g. cosine similarity).
   - The knowledge base is often a vector database — a database
     optimized for storing and searching embeddings efficiently.
3. **Augmentation step:** The retrieved documents are inserted into the
   prompt as additional context alongside the user's original question.
   - This "augmented" prompt gives the LLM factual material to draw from.
   - The context is placed within the model's context window — the
     limited amount of text the model can process at one time.
4. **Generation step:** The LLM generates an answer using both the
   original question and the retrieved context.
   - Because the model has real source material, its answer is more
     likely to be accurate and grounded in facts.
   - The model can also cite or reference the sources it used.

## Key Technical Terms

- **LLM (Large Language Model):** An AI model trained on massive amounts of
  text data that can understand and generate human language.
- **Embedding / Vector:** A numerical representation of text that captures
  its meaning. Similar texts have similar embeddings.
- **Vector Database:** A specialized database designed to store and quickly
  search through embeddings.
- **Knowledge Base / Document Store:** The collection of documents or
  information that the RAG system can search through.
- **Context Window:** The maximum amount of text a language model can
  read and process at one time.
- **Hallucination:** When an AI model generates information that sounds
  plausible but is factually incorrect or fabricated.
- **Retriever:** The component that searches the knowledge base and
  returns relevant documents.
- **Generator:** The language model component that produces the final
  answer using the retrieved context.
- **Cosine Similarity:** A mathematical method for measuring how similar
  two embeddings are to each other.
- **Fine-tuning:** Retraining a model on new data to change its behavior,
  which is more expensive and complex than RAG.

## What RAG Is NOT

- RAG is not the same as fine-tuning — fine-tuning changes the model's
  weights/parameters, while RAG keeps the model unchanged and provides
  external information at query time.
- RAG is not the same as simple prompt engineering — prompt engineering
  puts all information directly in the prompt without a retrieval step.
- RAG does not guarantee perfect answers — the quality depends on the
  quality of the knowledge base and the retrieval accuracy.
- RAG does not eliminate hallucination entirely — it significantly
  reduces it but cannot prevent it in all cases.

## Common Use Cases

- Question answering over company documents or knowledge bases.
- Customer support chatbots that need accurate, up-to-date information.
- Research assistants that search through academic papers.
- Legal or medical assistants that need to reference specific regulations
  or guidelines.

## Sources

- Lewis et al., 2020. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. (NeurIPS 2020).
- AWS Architecture Center. *What is RAG?* (Amazon Web Services).
- Pinecone Reference. *What is a Vector Database?* (Pinecone Systems).
