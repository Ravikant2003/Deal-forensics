import chromadb
import json

class DealVectorStore:
    def __init__(self):
        # New ChromaDB client configuration
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection("deals_data")
    
    def store_deals(self, deals_data):
        """Store deals data in vector database"""
        documents = []
        metadatas = []
        ids = []
        
        # Process lost deals
        for deal in deals_data.get("lost_deals", []):
            doc_text = f"Lost Deal: {deal['company']}. Reason: {deal.get('loss_reason', 'unknown')}. "
            for event in deal['timeline']:
                doc_text += f"Day {event['day']}: {event['event']} - {event['details']}. "
            
            documents.append(doc_text)
            metadatas.append({"type": "lost", "deal_id": deal["deal_id"], "company": deal["company"]})
            ids.append(f"lost_{deal['deal_id']}")
        
        # Process won deals
        for deal in deals_data.get("won_deals", []):
            doc_text = f"Won Deal: {deal['company']}. "
            for event in deal['timeline']:
                doc_text += f"Day {event['day']}: {event['event']} - {event['details']}. "
            
            documents.append(doc_text)
            metadatas.append({"type": "won", "deal_id": deal["deal_id"], "company": deal["company"]})
            ids.append(f"won_{deal['deal_id']}")
        
        # Clear existing data by getting all IDs and deleting them
        try:
            existing_data = self.collection.get()
            if existing_data['ids']:
                self.collection.delete(ids=existing_data['ids'])
        except Exception as e:
            print(f"Note: Could not clear existing data: {e}")
        
        # Add new data
        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"✅ Stored {len(documents)} deals in vector database")
        else:
            print("⚠️  No documents to store")
    
    def search_similar_deals(self, query, deal_type=None, n_results=3):
        """Search for similar deals"""
        try:
            where_filter = {"type": deal_type} if deal_type else None
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            return results
        except Exception as e:
            print(f"Error searching similar deals: {e}")
            return {"documents": [[]], "metadatas": [[]], "ids": [[]]}
    
    def get_all_deals(self, deal_type=None):
        """Get all deals from the collection"""
        try:
            where_filter = {"type": deal_type} if deal_type else None
            results = self.collection.get(where=where_filter)
            return results
        except Exception as e:
            print(f"Error getting all deals: {e}")
            return {"documents": [], "metadatas": [], "ids": []}
    
    def get_deal_by_id(self, deal_id, deal_type="lost"):
        """Get specific deal by ID"""
        try:
            results = self.collection.get(
                where={"deal_id": deal_id, "type": deal_type}
            )
            return results
        except Exception as e:
            print(f"Error getting deal by ID: {e}")
            return None
    
    def delete_all_data(self):
        """Delete all data from the collection (for testing)"""
        try:
            # Get all IDs first, then delete them
            existing_data = self.collection.get()
            if existing_data['ids']:
                self.collection.delete(ids=existing_data['ids'])
                print("✅ All data deleted from vector database")
            else:
                print("ℹ️  No data to delete")
        except Exception as e:
            print(f"Error deleting data: {e}")