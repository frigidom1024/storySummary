from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from src.models.narrative_node import NarrativeNode


class VectorStore:
    def __init__(self, persist_dir: str):
        self.persist_dir = persist_dir
        self.collections = {}
    
    def get_node_collection(self, book_id: str):
        collection_name = f"node_{book_id}"
        if collection_name not in self.collections:
            self.collections[collection_name] = Chroma(
                collection_name=collection_name,
                persist_directory=self.persist_dir
            )
        return self.collections[collection_name]
    
    def get_original_text_collection(self, book_id: str):
        collection_name = f"original_text_{book_id}"
        if collection_name not in self.collections:
            self.collections[collection_name] = Chroma(
                collection_name=collection_name,
                persist_directory=self.persist_dir
            )
        return self.collections[collection_name]
    
    def add_nodes(self, book_id: str, nodes: list[NarrativeNode]):
        collection = self.get_node_collection(book_id)
        documents = []
        for node in nodes:
            content, metadata = node.to_vector_content()
            doc = Document(
                page_content=content,
                metadata=metadata
            )
            documents.append(doc)
        collection.add_documents(documents)
    
    def add_original_text(self, book_id: str, text: str, chapter_id: str, chunk_id: str, chunk_size: int = 1000, chunk_overlap: int = 100):
        collection = self.get_original_text_collection(book_id)
        
        # 使用langchain的语义分片处理过长的章节内容
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "]
        )
        
        # 创建Document对象，包含系统外部的chunk信息
        doc = Document(
            page_content=text,
            metadata={
                "book_id": book_id,
                "chapter_id": chapter_id,
                "original_chunk_id": chunk_id,
                "source": "original_text"
            }
        )
        
        # 语义分片
        split_docs = text_splitter.split_documents([doc])
        
        # 为每个分片添加更详细的元数据
        for i, split_doc in enumerate(split_docs):
            split_doc.metadata.update({
                "sub_chunk_index": i,
                "sub_chunk_id": f"{chunk_id}_sub_{i}"
            })
        
        if split_docs:
            collection.add_documents(split_docs)
    
    def query_nodes(self, book_id: str, query_text: str, n_results: int = 5):
        collection = self.get_node_collection(book_id)
        return collection.similarity_search(query_text, k=n_results)
    
    def query_original_text(self, book_id: str, query_text: str, n_results: int = 5):
        collection = self.get_original_text_collection(book_id)
        return collection.similarity_search(query_text, k=n_results)
    
    def delete_book_collections(self, book_id: str):
        node_collection_name = f"node_{book_id}"
        original_text_collection_name = f"original_text_{book_id}"
        
        # 从内存中移除
        if node_collection_name in self.collections:
            del self.collections[node_collection_name]
        if original_text_collection_name in self.collections:
            del self.collections[original_text_collection_name]
        
        # 从持久化存储中删除（需要使用底层chromadb客户端）
        try:
            import chromadb
            client = chromadb.PersistentClient(path=self.persist_dir)
            client.delete_collection(node_collection_name)
            client.delete_collection(original_text_collection_name)
        except Exception:
            pass