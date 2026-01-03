import os
import json
from typing import List, Dict, Any, Optional

# Try to import LangChain components - make them optional
LANGCHAIN_AVAILABLE = False
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain.chains import ConversationalRetrievalChain
    from langchain.memory import ConversationBufferMemory
    from langchain.prompts import PromptTemplate
    from langchain.schema import Document
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    print(f"LangChain not available: {e}. Chatbot will use fallback responses.")


class RAGService:
    """RAG-based chatbot service for e-commerce assistance"""
    
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.llm = None
        self.embeddings = None
        self.vectorstore = None
        self.chain = None
        self.user_memories: Dict[int, Any] = {}
        self.initialized = False
        
    def initialize(self, products: List[Dict[str, Any]]):
        """Initialize the RAG system with product data"""
        if not LANGCHAIN_AVAILABLE:
            print("LangChain not available. Using fallback responses.")
            return False
            
        if not self.api_key:
            print("Warning: OPENAI_API_KEY not set. Chatbot will use fallback responses.")
            return False

            
        try:
            # Initialize LLM and embeddings
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.7,
                api_key=self.api_key
            )
            self.embeddings = OpenAIEmbeddings(api_key=self.api_key)
            
            # Create documents from products
            documents = self._create_documents(products)
            
            # Create vector store
            if documents:
                self.vectorstore = FAISS.from_documents(documents, self.embeddings)
            
            self.initialized = True
            print("RAG Service initialized successfully")
            return True
            
        except Exception as e:
            print(f"Error initializing RAG service: {e}")
            return False
    
    def _create_documents(self, products: List[Dict[str, Any]]) -> List:
        """Create LangChain documents from product data"""
        if not LANGCHAIN_AVAILABLE:
            return []
        documents = []

        
        for product in products:
            content = f"""
Product: {product['name']}
Category: {product['category']}
Price: ${product['price']:.2f}
Description: {product['description']}
Rating: {product.get('avg_rating', 0)}/5 ({product.get('rating_count', 0)} reviews)
Stock: {product.get('stock', 0)} available
Product ID: {product['id']}
"""
            doc = Document(
                page_content=content,
                metadata={
                    'product_id': product['id'],
                    'category': product['category'],
                    'price': product['price'],
                    'name': product['name']
                }
            )
            documents.append(doc)
        
        # Add general store information
        store_info = Document(
            page_content="""
Welcome to our E-Commerce Store!
We offer products in the following categories:
- Toys: Fun and educational toys for all ages
- Electronics: Latest gadgets and devices
- Dresses: Fashionable clothing for every occasion
- Cosmetics: Beauty and skincare products
- Footwear: Comfortable and stylish shoes

You can browse products, add them to favorites, leave reviews, and place orders.
Our AI assistant can help you find products, answer questions, and verify orders.
""",
            metadata={'type': 'store_info'}
        )
        documents.append(store_info)
        
        return documents
    
    def get_memory(self, user_id: int) -> Any:
        """Get or create conversation memory for a user"""
        if not LANGCHAIN_AVAILABLE:
            return None
        if user_id not in self.user_memories:
            self.user_memories[user_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
        return self.user_memories[user_id]
    
    def chat(self, user_id: int, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process a chat message and return response"""
        
        # If not initialized, return fallback response
        if not self.initialized or not self.vectorstore:
            return self._fallback_response(message, context)
        
        try:
            memory = self.get_memory(user_id)
            
            # Create custom prompt
            custom_prompt = PromptTemplate(
                input_variables=["context", "question", "chat_history"],
                template="""You are a helpful e-commerce assistant. Use the following product information to answer questions.
Be friendly, concise, and helpful. If asked about ordering, confirm the product details with the user.

Context from product catalog:
{context}

Chat History:
{chat_history}

Customer Question: {question}

Instructions:
- If the customer wants to order something, confirm the product name, price, and ask for confirmation
- If searching for products, suggest relevant items from the catalog
- For questions about categories (toys, electronics, dresses, cosmetics, footwear), provide helpful suggestions
- Always be polite and professional

Assistant Response:"""
            )
            
            # Create retrieval chain
            chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5}),
                memory=memory,
                return_source_documents=True,
                combine_docs_chain_kwargs={"prompt": custom_prompt}
            )
            
            # Get response
            result = chain.invoke({"question": message})
            
            response = {
                'success': True,
                'response': result.get('answer', 'I apologize, I could not process your request.'),
                'sources': []
            }
            
            # Extract product IDs from sources for potential order actions
            if 'source_documents' in result:
                for doc in result['source_documents']:
                    if 'product_id' in doc.metadata:
                        response['sources'].append({
                            'product_id': doc.metadata['product_id'],
                            'name': doc.metadata.get('name', ''),
                            'price': doc.metadata.get('price', 0)
                        })
            
            # Check if this is an order intent
            if self._detect_order_intent(message):
                response['action'] = 'order_intent'
                response['requires_confirmation'] = True
            
            return response
            
        except Exception as e:
            print(f"Chat error: {e}")
            return self._fallback_response(message, context)
    
    def _detect_order_intent(self, message: str) -> bool:
        """Detect if user wants to place an order"""
        order_keywords = [
            'order', 'buy', 'purchase', 'add to cart', 'checkout',
            'i want', 'i need', "i'd like", 'get me', 'can i get'
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in order_keywords)
    
    def _fallback_response(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Provide basic responses when LLM is not available"""
        message_lower = message.lower()
        
        if 'hello' in message_lower or 'hi' in message_lower:
            response = "Hello! Welcome to our store. I can help you find products in our categories: Toys, Electronics, Dresses, Cosmetics, and Footwear. How can I assist you today?"
        elif 'category' in message_lower or 'categories' in message_lower:
            response = "We have 5 categories: Toys, Electronics, Dresses, Cosmetics, and Footwear. Which category interests you?"
        elif 'order' in message_lower:
            response = "To place an order, please browse our products, select the items you want, and proceed to checkout. Would you like me to help you find something specific?"
        elif 'help' in message_lower:
            response = "I can help you with:\n- Finding products in different categories\n- Product recommendations\n- Order placement and confirmation\n- Answering questions about items\n\nWhat would you like assistance with?"
        else:
            response = "I'm here to help! You can ask me about our products, categories, or placing orders. What would you like to know?"
        
        return {
            'success': True,
            'response': response,
            'sources': [],
            'fallback': True
        }
    
    def confirm_order(self, user_id: int, product_ids: List[int], quantities: List[int]) -> Dict[str, Any]:
        """Generate order confirmation message"""
        return {
            'success': True,
            'response': f"I'm preparing your order with {len(product_ids)} item(s). Please confirm the details and I'll process it for you.",
            'action': 'confirm_order',
            'product_ids': product_ids,
            'quantities': quantities
        }
    
    def clear_memory(self, user_id: int):
        """Clear conversation memory for a user"""
        if user_id in self.user_memories:
            del self.user_memories[user_id]


# Global instance
rag_service = RAGService()
