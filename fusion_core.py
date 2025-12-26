import os
import pdfplumber
import docx
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# Load environment variables (e.g. HF_TOKEN from .env)
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

# ---- SAFETY CHECK ----
if not HF_TOKEN:
    raise ValueError("❌ HF token required for remote Llama. Please add it to your .env file as HF_TOKEN=hf_...")

# ---- MODEL SETUP ----
LEGAL_BERT = SentenceTransformer("nlpaueb/legal-bert-base-uncased")

# Remote Llama client setup (using Hugging Face Inference API)
LLAMA_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
llama_client = InferenceClient(model=LLAMA_MODEL, token=HF_TOKEN)


# ---- TEXT EXTRACTION ----
def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text.strip()


def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])


def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    elif ext.endswith(".docx"):
        return extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file format. Please upload PDF or DOCX.")


# ---- CHUNKING ----
def chunk_text(text, max_length=512):
    sentences = text.split(". ")
    chunks, current_chunk = [], ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_length:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks


# ---- VECTOR SEARCH (FAISS + LegalBERT) ----
def build_faiss_index(chunks):
    embeddings = LEGAL_BERT.encode(chunks)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings, dtype="float32"))
    return index, embeddings


def search_context(query, chunks, index, top_k=3):
    query_embedding = LEGAL_BERT.encode([query])
    distances, indices = index.search(np.array(query_embedding, dtype="float32"), top_k)
    return [chunks[i] for i in indices[0]]


# ---- LLAMA REMOTE COMPLETION ----
def llama_answer_from_context(prompt, context_chunks):
    context_text = "\n\n".join(context_chunks)
    final_prompt = f"Context:\n{context_text}\n\nQuestion:\n{prompt}\n\nAnswer clearly and legally."

    response = llama_client.chat.completions.create(
        model=LLAMA_MODEL,
        messages=[{"role": "user", "content": final_prompt}],
        max_tokens=300,
        temperature=0.4,
    )

    return response.choices[0].message["content"].strip()


# ---- MAIN PIPELINES ----
def analyze_document_file(file_path):
    text = extract_text(file_path)
    chunks = chunk_text(text)
    index, _ = build_faiss_index(chunks)

    results = []
    for clause in chunks:
        risk_prompt = (
            "Please analyze risk for the following clause and give short risk level (Low/Medium/High) with reason:"
        )
        llama_resp = llama_answer_from_context(risk_prompt, [clause])
        results.append({"clause": clause, "risk_analysis": llama_resp})

    return results


def analyze_query_over_document(query, file_path):
    text = extract_text(file_path)
    chunks = chunk_text(text)
    index, _ = build_faiss_index(chunks)

    relevant_context = search_context(query, chunks, index)
    answer = llama_answer_from_context(query, relevant_context)
    return answer
