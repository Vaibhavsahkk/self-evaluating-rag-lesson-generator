# Introduction to RAG

Welcome to your exciting journey into Artificial Intelligence, or AI! 

As you start your career in tech, you will hear many new words. One of the most important words today is **RAG**. 

This lesson will teach you what RAG is, why we need it, and how it works. You do not need any coding or computer science background to understand this lesson. Let us begin!

---

## 1. What is RAG?

**RAG** stands for **Retrieval-Augmented Generation**. 

That is a big phrase, but the idea is very simple. 

Think of RAG as an open-book exam for an AI. 
* Normally, an AI tries to answer your questions using only its memory. 
* With RAG, the AI looks up information in a **knowledge base** first. A knowledge base is a collection of documents, files, or data that the AI can read. 
* Then, the AI uses that fetched information to write a good answer for you.

**Everyday Analogy:**
Imagine you are writing an essay in a library. 
* Without RAG, you must write the whole essay using only facts you remember from your past classes. 
* With RAG, you first walk to the shelf, **retrieve** (find and bring back) a helpful book, read the correct pages, and then write your essay using those fresh facts. 

In technical terms, **retrieval** is the process of searching and finding relevant information from a large set of documents.

---

## 2. Why do we need RAG?

To understand why RAG is useful, we must first look at how standard AI models work. 

An **LLM** (Large Language Model) is a type of AI trained on massive amounts of text. It can talk, write, and answer questions. However, LLMs have two big problems:
1. They only know what was in their training data. They do not know private company documents, recent news, or your personal notes.
2. They can suffer from a **hallucination**. A hallucination is when an AI gives an answer that sounds confident but contains incorrect or unsupported information.

**Why RAG is useful:**
Imagine a fictional college that has a rulebook for student housing. An AI trained last year does not know the new housing rules added yesterday. If a student asks about housing, the standard AI might guess and make a mistake. 

With RAG, the system looks up the brand-new rulebook first. The retrieved information helps the model answer the question accurately. RAG can reduce the chance of unsupported answers by giving the AI real facts to look at while it works.

---

## 3. How does RAG work?

A RAG system follows three main steps:

1. **Retrieval:** When you ask a question, the system searches the knowledge base to find the most relevant pieces of text. 
   * In many RAG systems, text is converted into numbers called **embeddings**. An embedding is a list of numbers that captures the meaning of words. 
   * These numbers are often called **vectors**. A vector is simply a mathematical list of numbers used by computers to compare meanings. 
   * In many RAG systems, embeddings are stored in a **vector database**, which is a special computer storage system designed to search through vectors very quickly. Other retrieval methods, such as keyword search, can also be used.
2. **Context:** The system takes your question and the retrieved text, and puts them together. This combined text is fed into the AI. 
   * A **context window** is the amount of information a model can consider at one time when generating an answer. 
3. **Generation:** The AI reads the provided context and writes a clear, helpful response for you.

---

## 4. Concrete Example

Let us trace a simple RAG request step by step:

* **User Question:** "What is the library fee for late book returns?"
* **Step 1 (Retrieval):** The system searches the college library manual and finds the exact paragraph about late fees.
* **Step 2 (Context):** The system places the user question and that specific paragraph into the AI's **context window**.
* **Step 3 (Generation):** The AI reads the paragraph and answers: "The library fee is a small charge per day for late book returns, according to your library manual."

---

## 5. Important Limitations

RAG is a powerful tool, but it is not magic. You should know its limits:

* RAG does not guarantee that every answer is correct. 
* If the retrieval step finds the wrong document, the AI might still give a bad answer. 
* RAG can reduce hallucinations, but it does not completely stop the AI from making mistakes.

---

## 6. Summary / Key Takeaways

* **RAG (Retrieval-Augmented Generation):** A method that helps AI models find facts in a knowledge base before answering a question.
* **LLM (Large Language Model):** An AI trained to understand and generate text.
* **Retrieval:** The process of searching for and bringing back relevant information.
* **Knowledge Base:** A collection of documents or data used as a reference.
* **Embedding & Vector:** Ways to turn text into numbers so computers can compare meanings.
* **Vector Database:** One common way to store and search through embeddings. Other search methods also exist.
* **Context Window:** The amount of information a model can consider at one time when generating an answer.
* **Hallucination:** When an AI gives an answer that sounds confident but contains incorrect or unsupported information.
* **Main Benefit:** RAG helps ground AI answers in real documents, which can reduce the chance of hallucinations.