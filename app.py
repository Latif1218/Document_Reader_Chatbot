from flask import Flask, render_template, jsonify, request
from src.helper import download_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.prompt import *
import os


load_dotenv()

app = Flask(__name__)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")


os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["HUGGINGFACE_API_KEY"] = HUGGINGFACE_API_KEY

embedding = download_embeddings()

index_name = "chatbot-store"

    

docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embedding
)

retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k":3})

llm = HuggingFaceEndpoint(
    repo_id="deepseek-ai/DeepSeek-V3.2-Exp",  
    task="text-generation",
    huggingfacehub_api_token=os.getenv("HUGGINGFACE_API_KEY"),
    temperature=0.7,
    max_new_tokens=512,
    timeout=60
)

chatModel = ChatHuggingFace(llm=llm)


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

question_answer_chain = create_stuff_documents_chain(chatModel, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)


@app.route("/")
def index():
    return render_template('chat.html')



@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    input = msg
    print("User Input:", input)

    try:
        docs = retriever.get_relevant_documents(msg)
        if not docs or len(docs) == 0:
            return "Sorry, I couldn’t find any relevant information at the moment. The knowledge base might be updating. Please try again later."
    except Exception as e:
        print("Retriever Error:", repr(e))
        return "Apologies, there was an error retrieving data. Please try again later."

    try:
        response = rag_chain.invoke({"input": msg})
        print("Response:", response["answer"])
        return str(response["answer"])
    except Exception as e:
        print("LLM Error:", repr(e))
        return "Sorry, I encountered an issue while generating a response. Please try again shortly."

if __name__ == '__main__':
    app.run(host="0.0.0.0", port= 8080, debug= True)