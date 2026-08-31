"""
Build FINAL_INTRODUCTION_TO_RAG_LESSON.docx from the approved pipeline output.

The lesson text below mirrors output/lesson_output.md from the accepted run
(passed all 6 evaluation checkpoints on attempt 1 — Flesch 63.8, avg sentence
12.8 words). Run from the project root:

    python assets/create_docx.py
"""

from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


def add_heading(doc, text, level):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.name = 'Arial'
    return h


def add_paragraph(doc, text, bold=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(11)
    if bold:
        run.bold = True
    return p


def add_bullet(doc, text, bold_start=None):
    p = doc.add_paragraph(style='List Bullet')
    if bold_start:
        run = p.add_run(bold_start)
        run.bold = True
        run.font.name = 'Arial'
        run.font.size = Pt(11)
        run = p.add_run(text)
    else:
        run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(11)
    return p


def main():
    doc = Document()

    title = doc.add_heading('Introduction to RAG', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.name = 'Arial'

    # Opening
    add_paragraph(doc, "Welcome to your AI learning journey! Today, we will learn about a very useful technology called RAG.")
    add_paragraph(doc, "If you want to build a career in AI, understanding RAG is a big step forward. Let us break it down step by step in simple English.")

    # SECTION 1
    add_heading(doc, '1. What is RAG?', 1)
    add_paragraph(doc, "RAG stands for Retrieval-Augmented Generation.")
    add_paragraph(doc, "Do not worry about these big words. Let us split them up:")
    add_bullet(doc, ": Finding the right information from a collection of documents.", bold_start="Retrieval")
    add_bullet(doc, ": Creating a human-like answer using AI.", bold_start="Generation")
    add_paragraph(doc, "An LLM (Large Language Model) is a computer program trained on a huge amount of text. It can talk, write essays, and answer questions.")
    add_paragraph(doc, "Think of an LLM as a very smart student who read many books in the past. But this student is taking a closed-book exam. They can only use their memory.")
    add_paragraph(doc, "RAG gives this smart student an open book during the exam.")
    add_paragraph(doc, "Analogy: Imagine you work at a new job. Your boss asks you a question about company rules. Without RAG, you guess the answer from memory. With RAG, you quickly look at the company rulebook on your desk and give the exact answer. RAG is like giving the AI a search tool and a library to use before it replies.")

    # SECTION 2
    add_heading(doc, '2. Why do we need RAG?', 1)
    add_paragraph(doc, "LLMs are very powerful, but they have two big limits:")
    add_bullet(doc, " They only know what they learned during training. They do not know new facts or private company data.", bold_start="Limit 1:")
    add_bullet(doc, " Sometimes, an AI makes mistakes. A hallucination is when an AI gives an answer that sounds confident but contains incorrect or unsupported information.", bold_start="Limit 2:")
    add_paragraph(doc, "Also, an LLM has a context window. A context window is the amount of information a model can consider at one time when generating an answer. It cannot read a million books all at once.")
    add_paragraph(doc, "Analogy: Imagine asking a famous chef how to make a secret local dish from your town. If the chef never visited your town, they might guess the recipe. They might sound very sure of themselves, but the food will taste wrong. RAG gives the chef the actual local recipe first so they can cook the correct dish.")
    add_paragraph(doc, "RAG matters because it helps the AI look at real facts before replying. This can reduce the chance of unsupported answers.")

    # SECTION 3
    add_heading(doc, '3. How does RAG work?', 1)
    add_paragraph(doc, "A RAG system works in three main steps:")

    add_heading(doc, 'Step 1: Building a Knowledge Base', 2)
    add_paragraph(doc, "First, you gather your documents, manuals, or notes. This is your knowledge base, which is a collection of information used to help answer questions.")

    add_heading(doc, 'Step 2: Retrieval (Finding the Data)', 2)
    add_paragraph(doc, "When a user asks a question, the system searches the knowledge base for the most helpful parts. This step is called retrieval, which is the process of finding and pulling out relevant information from a larger set of files.")
    add_paragraph(doc, "To make search fast and smart, computers use embeddings and vectors.")
    add_bullet(doc, " An embedding is a way to turn words and sentences into lists of numbers so a computer can understand their meaning.", bold_start="Embedding:")
    add_bullet(doc, " A vector is a list of numbers that represents the meaning of a piece of text.", bold_start="Vector:")
    add_paragraph(doc, "In many RAG systems, embeddings are stored in a vector database, which is a special type of database designed to store and search these number lists quickly. Other retrieval methods, such as simple keyword search, can also be used.")

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture('assets/infographic1_rag_flow.png', width=Inches(3.5))

    add_heading(doc, 'Step 3: Generation (Writing the Answer)', 2)
    add_paragraph(doc, "The system takes the user's question and the retrieved text, and gives both to the LLM. The retrieved information helps the model answer the question. The LLM then writes a clear, helpful reply for the user.")

    # SECTION 4
    add_heading(doc, '4. Concrete Example', 1)
    add_paragraph(doc, "Let us look at a fictional example to see this in action.")
    add_paragraph(doc, "Imagine a fictional college called Apex Institute.")
    add_bullet(doc, " The college has a digital handbook with all exam rules. This is the knowledge base.", bold_start="1.")
    add_bullet(doc, " A student asks: \"What is the rule for late exam submission?\"", bold_start="2.")
    add_bullet(doc, " The RAG system performs retrieval. It searches the handbook and finds the exact paragraph about late exams.", bold_start="3.")
    add_bullet(doc, " The system sends the student's question and that specific paragraph to the AI.", bold_start="4.")
    add_bullet(doc, " The AI reads the paragraph and generates a polite, correct answer for the student.", bold_start="5.")

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.add_run().add_picture('assets/infographic2_comparison.png', width=Inches(5.0))

    # SECTION 5
    add_heading(doc, '5. Important Limitations', 1)
    add_paragraph(doc, "RAG is a wonderful tool, but it is not magic. You must remember these important points:")
    add_bullet(doc, " RAG does not guarantee that every answer is correct.", bold_start="Point 1:")
    add_bullet(doc, " If the retrieval step finds the wrong document, the AI might still give a bad answer.", bold_start="Point 2:")
    add_bullet(doc, " RAG can reduce the chance of unsupported answers, but it does not completely stop hallucinations.", bold_start="Point 3:")

    # SECTION 6
    add_heading(doc, '6. Summary / Key Takeaways', 1)
    add_bullet(doc, " RAG (Retrieval-Augmented Generation) connects an AI model to an external source of information.", bold_start="What:")
    add_bullet(doc, " Retrieval finds the right facts, and Generation writes the final answer. RAG can reduce hallucinations, but it does not completely eliminate them.", bold_start="How & Why:")
    add_bullet(doc, " Embeddings and vectors help computers compare the meaning of words and find relevant text.", bold_start="Key terms:")

    doc.save('FINAL_INTRODUCTION_TO_RAG_LESSON.docx')


if __name__ == '__main__':
    main()
