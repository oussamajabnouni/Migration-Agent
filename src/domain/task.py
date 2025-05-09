from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class Task:
    """
    Represents a single task in the migration plan.
    """
    id: str
    description: str
    status: str = "todo"  
    depends_on: List[str] = field(default_factory=list)
    notes: Optional[str] = None 
    raw_lines: List[str] = field(default_factory=list) 

    def __post_init__(self):
        
        if self.description:
            self.description = self.description.strip()

    def __repr__(self):
        return f"Task(id='{self.id}', description='{self.description[:30]}...', status='{self.status}', depends_on={self.depends_on})"
