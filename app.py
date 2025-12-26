import streamlit as st
from fusion_core import analyze_document_file, analyze_query_over_document

st.set_page_config(page_title="AI Legal Document Analyzer", layout="wide")

st.title("⚖️ AI Legal Document Analyzer & Advisor")
st.markdown("""
Upload a legal document (PDF or DOCX) and get clause risk analysis or legal Q&A  
using **LegalBERT** for clause understanding and **Llama** for reasoning.
""")

uploaded_file = st.file_uploader("📁 Upload your document", type=["pdf", "docx"])

if uploaded_file:
    file_path = f"temp_{uploaded_file.name}"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())

    st.success("✅ File uploaded successfully!")

    # --- Full Legal Risk Analysis ---
    if st.button("🚀 Run Full Legal Analysis"):
        with st.spinner("Analyzing document using LegalBERT + Llama..."):
            try:
                results = analyze_document_file(file_path)
                if not results:
                    st.warning("⚠️ No clauses found or analysis returned empty.")
                else:
                    st.subheader("📄 Clause Risk Analysis")
                    for i, item in enumerate(results, 1):
                        clause = item.get("clause", "N/A")
                        risk = item.get("risk_analysis", "No analysis available.")
                        st.markdown(f"### Clause {i}")
                        st.markdown(f"**Clause:** {clause}")
                        st.markdown(f"**Risk Analysis:** {risk}")
                        st.markdown("---")
            except Exception as e:
                st.error(f"❌ Error during analysis: {e}")

    # --- Legal Q&A ---
    st.subheader("💬 Ask a question about the document")
    query = st.text_input("Enter your legal question:")
    if st.button("Ask Llama"):
        if not query.strip():
            st.warning("Please enter a question first.")
        else:
            with st.spinner("Querying the document using Llama..."):
                try:
                    answer = analyze_query_over_document(query, file_path)
                    if answer:
                        st.success("✅ Answer:")
                        st.write(answer)
                    else:
                        st.warning("⚠️ No answer returned from the model.")
                except Exception as e:
                    st.error(f"❌ Error while answering: {e}")
