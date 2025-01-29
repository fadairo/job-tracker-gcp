from google.cloud import firestore
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models import JobApplication

class JobApplicationStore:
    """
    Handles all database operations related to job applications.
    Provides a clean interface for creating, reading, updating, and
    deleting job applications in Firestore.
    """
    def __init__(self, db: Optional[firestore.Client] = None):
        """
        Initialize the store with a Firestore client.
        If no client is provided, creates a new one.
        """
        self.db = db or firestore.Client()
        self.collection = self.db.collection('job_applications')
        
    async def create(self, application: JobApplication) -> str:
        """
        Creates a new job application in the database.
        Validates the data before saving and returns the new document ID.
        """
        # Validate the application data
        errors = application.validate()
        if errors:
            raise ValueError(f"Invalid application data: {', '.join(errors)}")
            
        # Create the document
        doc_ref = self.collection.document()
        doc_ref.set(application.to_dict())
        return doc_ref.id
        
    async def get(self, application_id: str) -> Optional[JobApplication]:
        """
        Retrieves a job application by its ID.
        Returns None if no application is found.
        """
        doc_ref = self.collection.document(application_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
            
        return JobApplication.from_dict(doc.to_dict())
        
    async def update(self, 
                    application_id: str, 
                    updates: Dict[str, Any]) -> Optional[JobApplication]:
        """
        Updates an existing job application with new data.
        Returns the updated application or None if not found.
        """
        doc_ref = self.collection.document(application_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
            
        # Get current data and update it
        current_data = doc.to_dict()
        current_data.update(updates)
        current_data['updated_at'] = datetime.utcnow()
        
        # Validate the updated data
        application = JobApplication.from_dict(current_data)
        errors = application.validate()
        if errors:
            raise ValueError(f"Invalid update data: {', '.join(errors)}")
            
        # Save the updates
        doc_ref.update(application.to_dict())
        return application
        
    async def list(self, 
                   limit: int = 10, 
                   status: Optional[str] = None) -> List[JobApplication]:
        """
        Lists job applications with optional filtering and pagination.
        Returns a list of job applications matching the criteria.
        """
        query = self.collection.order_by('created_at', direction=firestore.Query.DESCENDING)
        
        if status:
            query = query.where('status', '==', status)
            
        docs = query.limit(limit).stream()
        return [JobApplication.from_dict(doc.to_dict()) for doc in docs]