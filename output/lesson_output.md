# Introduction to RAG

Welcome to your AI learning journey! If you want to build a career in Artificial Intelligence, you are in the right place. Today, we will learn about a very useful technique called **RAG**. 

---

## 1. What is RAG?

**RAG** stands for **Retrieval-Augmented Generation**. 

That is a big phrase. Let us break it down into simple parts:
* **Retrieval:** Finding the right information from a collection of documents.
* **Generation:** Creating a human-like answer using AI.

Think of **RAG** like an open-book exam for an AI. 

Imagine a student taking a test. If the student relies only on memory, they might forget important details. But if the student is allowed to open a textbook, look up the exact page, and write the answer, they will do much better. 

An **LLM** (which stands for **Large Language Model**, an AI trained on vast amounts of text to understand and generate human language) is like that student. By itself, an LLM relies only on its training. **RAG** gives the LLM a textbook to look at before it writes an answer.

---

## 2. Why do we need RAG?

To understand why **RAG** is useful, we must look at how standard AI models work. 

An LLM has a **context window**. A context window is the amount of information a model can consider at one time when generating an answer. 

If you ask an AI about private company rules or new local news, it might not know the answer. Worse, it might guess. 

This leads to a **hallucination**. A hallucination is when an AI gives an answer that sounds confident but contains incorrect or unsupported information.

Imagine asking a chef to cook a dish without giving them the recipe book. They might guess the ingredients and ruin the meal. **RAG** gives the chef the recipe book first. 

**RAG** is useful because it helps the AI find up-to-date facts from a **knowledge base**. A knowledge base is a collection of documents, files, or data sources used as a reference. This helps the model answer questions accurately using real documents.

---

## 3. How does RAG work?

A **RAG** system works in three main steps: **retrieval**, **context**, and **generation**.

1. **Retrieval:** When you ask a question, the system searches through a **knowledge base** to find the most useful text. 
   To do this, computers often turn words into numbers called **embeddings**. An embedding is a list of numbers that represents the meaning of a word or text. These numbers are called **vectors**. A vector is a list of numbers used by computers to measure how similar different pieces of text are. 
   In many RAG systems, embeddings are stored in a **vector database**, which is a special type of database designed to search through these number lists very quickly. Other retrieval methods, such as simple keyword search, can also be used.
2. **Context:** The system takes the retrieved text and adds it to the prompt. This gives the AI model the right background information inside its **context window**.
3. **Generation:** The AI model reads your question along with the retrieved text. Then, it writes a clear, helpful answer for you.

---

## 4. Concrete example

Let us look at a fictional example to see this in action.

Imagine a fictional college named *North Star College*. 

A student asks the college chatbot: *"What is the refund policy for hostel fees?"*

* **Without RAG:** The AI does not know the specific rules of North Star College. It might guess a random policy or give a generic answer.
* **With RAG:** 
  1. The system performs **retrieval** by searching the college rulebook and finding the exact page about hostel refunds.
  2. It passes this text as **context** to the AI model.
  3. The AI reads the policy and performs **generation**, writing a helpful, correct answer about the hostel refund dates and rules for the student.

---

## 5. Important limitations

**RAG** is a powerful tool, but it is not perfect. You should know its limits:

* **RAG can reduce the chance of unsupported answers.** It cannot stop all errors. 
* **RAG does not guarantee that every answer is correct.** If the retrieved documents contain mistakes, the AI might repeat those mistakes.
* **RAG depends on good search results.** If the retrieval step fails to find the right document, the AI will not have the information it needs.

---

## 6. Summary / key takeaways

* **RAG** (**Retrieval-Augmented Generation**) combines document search with AI text generation.
* It works by **retrieving** relevant data, providing it as **context**, and **generating** an answer.
* An **LLM** is an AI model that understands and generates human text.
* A **context window** is the amount of information a model can consider at one time when generating an answer.
* A **hallucination** is when an AI gives an answer that sounds confident but contains incorrect or unsupported information.
* **RAG** can reduce the risk of hallucinations, but it does not guarantee perfect answers every time.