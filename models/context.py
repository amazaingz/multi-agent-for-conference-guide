from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum
import random
import string

class OrderStatus(str, Enum):
    NEED_PAY='need_pay'
    SHIPPED='shipped'
    COMPLETE='complete'
    CANCELLED='cancelled'


class CustomerServiceAgentContext(BaseModel):
    """Context for airline customer service agents."""
    customer_name: Optional[str] = None
    customer_id: Optional[int] = None
    order_number: Optional[str] = None
    #status: created, pending, deliverying, complete, close
    status: Optional[OrderStatus] = None
    descriptions: Optional[List[Dict[str,Any]]] = []

    def update_descriptions(self, message: Dict[str,Any]):
        self.descriptions.append(message)
    

def create_initial_context() -> CustomerServiceAgentContext:
    ctx = CustomerServiceAgentContext()
    #ctx.order_number = str(random.randint(100000000, 999999999))
    return ctx

def set_customer_name(c_name:str, ctx:CustomerServiceAgentContext):
    ctx.customer_name = c_name
    ctx.customer_id=random.randint(1000000, 9999999)

def set_order_status(status:str, ctx:CustomerServiceAgentContext):
    ctx.status = status

def generate_order_number(ctx:CustomerServiceAgentContext):
    """Generate a random order number."""
    #return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    ctx.order_number = str(random.randint(100000000, 999999999))
    return ctx

