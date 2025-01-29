from google.cloud import firestore
from datetime import datetime
from typing import Dict, Any, Optional, List

class JobApplication:
    """
    Represents a job application in our system. This class defines the structure
    of our job application data and provides methods for data validation and
    transformation.
    """
    def __init__(self, 
                 company: str,
                 position: str,
                 status: str = "applied",
                 resume_url: Optional[str] = None,
                 notes: Optional[str] = None) -> None:
        self.company = company
        self.position = position
        self.status = status
        self.resume_url = resume_url
        self.notes = notes
        self.created_at = datetime.utcnow()
        self.updated_at = self.created_at
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the job application instance to a dictionary format
        suitable for storing in Firestore.
        """
        return {
            'company': self.company,
            'position': self.position,
            'status': self.status,
            'resume_url': self.resume_url,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'JobApplication':
        """
        Creates a JobApplication instance from a dictionary, typically
        used when retrieving data from Firestore.
        """
        app = JobApplication(
            company=data.get('company'),
            position=data.get('position'),
            status=data.get('status', 'applied'),
            resume_url=data.get('resume_url'),
            notes=data.get('notes')
        )
        app.created_at = data.get('created_at', datetime.utcnow())
        app.updated_at = data.get('updated_at', datetime.utcnow())
        return app
    
    def validate(self) -> List[str]:
        """
        Validates the job application data and returns a list of any errors.
        This helps ensure data quality before saving to the database.
        """
        errors = []
        
        if not self.company or len(self.company.strip()) == 0:
            errors.append("Company name is required")
            
        if not self.position or len(self.position.strip()) == 0:
            errors.append("Position is required")
            
        valid_statuses = ['applied', 'interviewing', 'offered', 'rejected', 'accepted']
        if self.status not in valid_statuses:
            errors.append(f"Status must be one of: {', '.join(valid_statuses)}")
            
        return errors