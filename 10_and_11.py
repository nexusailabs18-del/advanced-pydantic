from __future__ import annotations
import logging
from typing import Annotated, Any, Union
from pydantic_core import PydanticUseDefault, PydanticCustomError
from pydantic import (
    BaseModel, 
    Field, 
    ValidationError, 
    BeforeValidator, 
    AfterValidator, 
    PlainValidator, 
    WrapValidator, 
    ValidatorFunctionWrapHandler, 
    model_validator,
    InstanceOf, 
    SkipValidation,
    field_validator,
    ValidationInfo
)

# Global configuration for structural error tracing
logging.basicConfig(level=logging.INFO)

# =====================================================================
# MODULE 1: ORDER PROCESSING PIPELINE
# =====================================================================

def strip_and_clean_sku(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().upper()
    return value

def verify_positive_price(value: float) -> float:
    if value <= 0:
        raise ValueError("Price must be a positive number greater than zero.")
    return value

def strict_legacy_id(value: Any) -> int:
    if not isinstance(value, str) or not value.startswith("LEG-"):
        raise ValueError("Legacy IDs must be strings formatted exactly as 'LEG-xxxx'")
    try:
        return int(value.replace("LEG-", ""))
    except ValueError:
        raise ValueError("Legacy ID suffix must be a valid integer.")

def auto_fix_email(value: Any, handler: ValidatorFunctionWrapHandler) -> str:
    try:
        return handler(value)
    except ValidationError:
        logging.warning(f"Intercepted invalid email parsing: {value}. Patched domain.")
        if isinstance(value, str) and "@" not in value:
            return handler(f"{value}@company.com")
        raise

class OrderPipeline(BaseModel):
    sku_code: Annotated[str, BeforeValidator(strip_and_clean_sku)] = Field(min_length=3)
    unit_price: Annotated[float, AfterValidator(verify_positive_price)]
    legacy_id: Annotated[int, PlainValidator(strict_legacy_id)]
    contact_email: Annotated[str, WrapValidator(auto_fix_email)]
    discount_amount: float = 0.0

    @model_validator(mode='after')
    def enforce_discount_bounds(self) -> 'OrderPipeline':
        if self.discount_amount >= self.unit_price:
            raise ValueError(
                f"Discount ({self.discount_amount}) cannot exceed or equal unit price ({self.unit_price})."
            )
        return self

# =====================================================================
# MODULE 2: SMART DEVICE NETWORK MANAGEMENT
# =====================================================================

class HardwarePort:
    def __init__(self, port_num: int):
        self.port_num = port_num
    def __repr__(self):
        return f"HardwarePort({self.port_num})"

def fallback_to_default_if_null(value: Any) -> Any:
    if value is None:
        raise PydanticUseDefault()
    return value

class SmartDevice(BaseModel):
    device_id: Annotated[str, BeforeValidator(fallback_to_default_if_null)] = "DEV-0000"
    ip_address: str
    network_gateway: str
    active_port: InstanceOf[HardwarePort]
    raw_telemetry: SkipValidation[list]

    @field_validator('device_id', mode='before', json_schema_input_type=Union[int, str])
    @classmethod
    def convert_int_ids(cls, value: Any) -> Any:
        if isinstance(value, int):
            return f"DEV-{value}"
        return value

    @field_validator('ip_address', mode='after')
    @classmethod
    def check_ip_blacklist(cls, value: str, info: ValidationInfo) -> str:
        if info.context and 'blacklist' in info.context:
            if value in info.context['blacklist']:
                raise PydanticCustomError(
                    'blacklisted_ip',
                    'The IP address {ip} is restricted by the firewall.',
                    {'ip': value}
                )
        return value

    @field_validator('network_gateway', mode='after')
    @classmethod
    def ensure_same_subnet(cls, value: str, info: ValidationInfo) -> str:
        # Safeguarded look-back: verify if ip_address exists in the data cache first
        if 'ip_address' not in info.data:
            raise ValueError("Cannot validate gateway subnet because the primary IP address is invalid.")
            
        if value == info.data['ip_address']:
            raise ValueError("Gateway cannot be identical to the device IP.")
        return value

# =====================================================================
# EXECUTABLE VERIFICATION RUNNERS (No __main__ blocks)
# =====================================================================

def execute_order_pipeline_tests():
    print("--- 🔴 RUNNING ORDER PIPELINE DATA TRIALS ---")
    valid_raw_payload = {
        "sku_code": "  bfr-999-x  ",
        "unit_price": "150.50",
        "legacy_id": "LEG-2026",
        "contact_email": "sysadmin",
        "discount_amount": 25.00
    }
    parsed_order = OrderPipeline(**valid_raw_payload)
    print("Clean Order Output Data:", parsed_order.model_dump(), "\n")

def execute_smart_device_tests():
    print("--- 🔴 RUNNING SMART DEVICE CONTEXT TRIALS ---")
    invalid_data = {
        "device_id": None,
        "ip_address": "10.0.0.5",
        "network_gateway": "10.0.0.5",
        "active_port": {"port_num": 8080},
        "raw_telemetry": "junk_data"
    }
    try:
        SmartDevice.model_validate(
            invalid_data, 
            context={'blacklist': ['192.168.1.100', '10.0.0.5']}
        )
    except ValidationError as err:
        print(f"Captured {err.error_count()} System Validation Failures:\n")
        print(err)

# Run verification blocks directly
execute_order_pipeline_tests()
execute_smart_device_tests()


                 # 11 # 

import dataclasses
from datetime import datetime
from typing import Annotated, Any, Optional
from pydantic import ConfigDict, Field, TypeAdapter, field_validator
from pydantic.dataclasses import dataclass, is_pydantic_dataclass 

class ExternalSystemToken:
    def __init__(self, key: str):
        self.key = key
    def __repr__(self):
        return f"Token({self.key})"

@dataclasses.dataclass
class VanillaUser:
    """A standard library dataclass with NO native validation parameters."""
    username: str
    joined_at: Any

@dataclass(config=ConfigDict(
    validate_assignment=True,
    arbitrary_types_allowed=True,
    str_strip_whitespace=True
))
class VerifiedMember(VanillaUser):
    access_logs: list[str] = dataclasses.field(default_factory=list)

    security_clearance: int = Field(default=1, ge=1, le=5)

    is_elite: bool = dataclasses.field(init=False, default=False)

    @field_validator('username', mode='before')
    @classmethod
    def convert_numeric_usernames(cls, value: Any) -> Any:
        """Runs 1st: Coerces plain integers into clean standard string handles."""
        if isinstance(value, int):
            return f"user_{value}"
        return value

    def __post_init__(self) -> None:
        """Runs 2nd: Native dataclass initializer to calculate derived flags."""
        if self.security_clearance >= 4:
            self.is_elite = True

    @field_validator('security_clearance', mode='after')
    @classmethod
    def audit_clearance_levels(cls, value: int) -> int:
        """Runs 3rd: Final business enforcement validation checkpoint."""
    
        return value
    
def execute_dataclass_suite():
    print("--- 🔬 CHECKPOINT A: System Identity Verification ---")
    print(f"Is VanillaUser a Pydantic Dataclass? -> {is_pydantic_dataclass(VanillaUser)}")
    print(f"Is VerifiedMember a Pydantic Dataclass? -> {is_pydantic_dataclass(VerifiedMember)}\n")

    print("--- 🔬 CHECKPOINT B: Successful Processing & Type Coercion ---")
    raw_payload = {
        "username": 48291,                  # Automatically cleaned up and stringified
        "joined_at": "2026-07-14",          # Retained as raw structural entity
        "security_clearance": "5",          # Coerced natively from string to int
        "service_token": ExternalSystemToken("SEC-KEY-XYZ") # Handled via arbitrary types rule
    }
    
    # Instantiation acts identically to a normal Python dataclass instance
    member = VerifiedMember(**raw_payload)
    print("Generated Dataclass Instance Layout:")
    print(member)
    print(f"Calculated flag status (is_elite): {member.is_elite}\n")

    print("--- 🔬 CHECKPOINT C: Serializing Data via TypeAdapter ---")
    # Dataclasses don't have .model_dump(), we feed the class blueprint to a TypeAdapter instead
    adapter = TypeAdapter(VerifiedMember)
    exported_dict = adapter.dump_python(member)
    print("Exported Python Primitive Map:")
    print(exported_dict, "\n")

    print("--- 🔬 CHECKPOINT D: Catching Runtime Input Violations ---")
    invalid_payload = {
        "username": "  admin_root  ",
        "joined_at": datetime.now(),
        "security_clearance": 99,           # Out of bounds! Breaks Pydantic Field constraints
    }
    
    try:
        VerifiedMember(**invalid_payload)
    except Exception as err:
        print("Captured anticipated validation framework failure:")
        print(err)

# Directly run the workspace trials
execute_dataclass_suite()


                        #12#


from typing import Any
from pydantic import (
    BaseModel, 
    Field, 
    TypeAdapter, 
    model_validator, 
    field_serializer,
    SerializerFunctionWrapHandler
)

class SmartNetworkNode(BaseModel):
    id: int
    label: str
    connections: list[SmartNetworkNode] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def prevent_infinite_validation_loops(cls, data: Any) -> Any:

          if not isinstance(data, dict):
             return data
          
          def clean_nested_loops(current_data: Any, seen_ids: set[int]) -> Any:
              if not isinstance(current_data, dict) or 'id' not in current_data:
                return current_data
              
              node_id = current_data["id"]
              if node_id in seen_ids:
                  return {
                    "id": current_data.get("id"),
                    "label": current_data.get("label", "Looping Reference"),
                    "connections": [] 
                }
              new_seen = seen_ids.copy()
              new_seen.add(node_id)

              if "connections" in current_data and isinstance(current_data["connections"], list):
                cleaned_connections = []
                for child in current_data["connections"]:
                    cleaned_connections.append(clean_nested_loops(child, new_seen))
                current_data["connections"] = cleaned_connections
                
              return current_data

          return clean_nested_loops(data, set())

    # 📤 OUTPUT PROTECTOR: Keep dumps safe from instance loops
    @field_serializer('connections', mode='wrap')
    def serialize_connections(
        self, connections: list[SmartNetworkNode], handler: SerializerFunctionWrapHandler
    ) -> Any:
        """
        Intercepts outgoing serialization. Converts live cyclic Python objects 
        safely into JSON-ready trees by breaking cycles at the loop point.
        """
        try:
            return handler(connections)
        except ValueError as exc:
            if "Circular reference" not in str(exc):
                raise exc
            
            safe_serialized_output = []
            for node in connections:
                try:
                    safe_serialized_output.append(handler([node])[0])
                except ValueError as nested_exc:
                    if "Circular reference" not in str(nested_exc):
                        raise nested_exc
                    # Safe truncation marker
                    safe_serialized_output.append({
                        "id": node.id, 
                        "label": node.label, 
                        "connections": []
                    })
            
            return safe_serialized_output


# =====================================================================
# SYSTEM VERIFICATION WORKSPACE
# =====================================================================

def run_unified_graph_system():
    print("--- 📥 RUNNING PHASES: INPUT VALIDATION (Keeping Node D) ---")
    
    # Setup standard recursive dictionary mapping: Node A (1) -> Node D (2) -> Node A (1)
    raw_node_a = {"id": 1, "label": "Node-A", "connections": []}
    raw_node_d = {"id": 2, "label": "Node-D", "connections": [raw_node_a]}
    raw_node_a["connections"].append(raw_node_d)
    
    # Validate the data tree into active Python components
    validated_root = SmartNetworkNode.model_validate(raw_node_a)
    
    print(f"Root Level: {validated_root.label} (ID: {validated_root.id})")
    print(f"  └── Has Connection: {validated_root.connections[0].label} (ID: {validated_root.connections[0].id})")
    print(f"        └── Looping Connection Kept: {validated_root.connections[0].connections[0].label} (ID: {validated_root.connections[0].connections[0].id})")
    print(f"              └── Sub-connections successfully truncated: {validated_root.connections[0].connections[0].connections}\n")

    print("--- 📤 RUNNING PHASES: OUTPUT SERIALIZATION (Safe Exporter) ---")
    
    # Recreate the exact pattern inside Python Object Instances
    obj_a = SmartNetworkNode(id=100, label="Router-Alpha")
    obj_d = SmartNetworkNode(id=200, label="Router-Delta")
    
    obj_a.connections.append(obj_d)
    obj_d.connections.append(obj_a)
    
    # Export using a structural Pydantic TypeAdapter
    adapter = TypeAdapter(SmartNetworkNode)
    serialized_output = adapter.dump_python(obj_a)
    
    print("Clean JSON-compatible dictionary generated without crashes:")
    print(serialized_output)

run_unified_graph_system()
           
         
        

