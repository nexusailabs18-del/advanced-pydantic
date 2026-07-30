from dataclasses import dataclass as std_dataclass
from typing_extensions import TypedDict
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError, with_config,Field,SerializeAsAny,FieldSerializationInfo

class GlobalAPIModel(BaseModel):
    # This acts as the master blueprint. All children will inherit this.
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

class UserProfile(GlobalAPIModel):
    # Inherits str_strip_whitespace, but overrides 'extra' behavior
    model_config = ConfigDict(extra="ignore")
    username: str

print("--- 1. Testing: Inheritance & Merging ---")
# '   admin   ' is stripped. The forbidden extra field 'hacker_data' is ignored, not rejected.
user = UserProfile.model_validate({"username": "   admin   ", "hacker_data": "payload"})
print(f"Cleaned Username: '{user.username}'")
print(f"Merged Config State: {UserProfile.model_config}\n")


# =====================================================================
class SecureToken(BaseModel, frozen=True):
    # Using frozen=True as a class kwarg allows linters to catch mutations
    token_value: str

print("--- 2. Testing: Frozen Class Arguments ---")
token = SecureToken(token_value="abc-123")
try:
    token.token_value = "compromised-token" #type:ignore
except ValidationError as e:
    print(f"Caught Mutation Attempt on Frozen Model:\n{e}\n")


@with_config(ConfigDict(str_to_lower=True))
class NormalizerDict(TypedDict):
    search_query: str

print("--- 3. Testing: TypeAdapters & Decorators ---")
# Applying config to a TypeAdapter directly
adapter = TypeAdapter(list[str], config=ConfigDict(str_max_length=4))

try:
    adapter.validate_python(["ok", "too_long"])
except ValidationError as e:
    print(f"TypeAdapter Config Blocked Invalid Length: {e.error_count()} error(s)")


dict_adapter = TypeAdapter(NormalizerDict)
cleaned_dict = dict_adapter.validate_python({"search_query": "UPPERCASE_SEARCH"})
print(f"TypedDict Decorator Output: {cleaned_dict}\n")


class NestedPydanticModel(BaseModel):
    # Sovereign state: Has its own boundary, ignores parent configs
    tag: str

@std_dataclass
class NestedStdlibDataclass:
    # No boundary: Absorbs parent configs
    tag: str

class MasterPayload(BaseModel):
    model_config = ConfigDict(str_to_lower=True)
    
    pydantic_child: NestedPydanticModel
    stdlib_child: NestedStdlibDataclass

print("--- 4. Testing: Configuration Boundaries ---")
payload = MasterPayload(
    pydantic_child={"tag": "SHOUTING"},  # Will remain uppercase #type:ignore
    stdlib_child={"tag": "SHOUTING"}     # Will be forced lowercase by parent  #type:ignore
)

print(f"Pydantic Child (Ignored Parent): {payload.pydantic_child.tag}")
print(f"Stdlib Child   (Absorbed Parent): {payload.stdlib_child.tag}")

                                   # -------------Chapter 9 -------------------#

import pickle
from typing import Annotated, Any
from datetime import datetime
from pydantic import (
    BaseModel, 
    PlainSerializer, 
    WrapSerializer, 
    field_serializer, 
    model_serializer, 
    SerializerFunctionWrapHandler
)

CreditCardMask = Annotated[str,PlainSerializer(lambda v: f"****-****-****-{v[-4:]}" if len(v) >= 4 else "****", return_type=str)]

def format_currency(value: float, handler: SerializerFunctionWrapHandler) -> str:
    standard_output = handler(value)
    return f"${standard_output:.2f} USD"

CurrencyFloat = Annotated[float, WrapSerializer(format_currency)]

class PaymentDetails(BaseModel):
    card_number: CreditCardMask
    balance: CurrencyFloat
    # Using a tuple to demonstrate Python vs JSON serialization modes
    internal_codes: tuple[int, int]

class TransactionExport(BaseModel):
    receipt_id: str
    status: str
    payment: PaymentDetails

    @field_serializer("receipt_id","status",mode="plain")
    def uppercase_strings(self, value: str) -> str:
        return value.upper()
    
    @model_serializer(mode="wrap")
    def inject_export_metadata(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        # Let Pydantic generate the standard nested dictionary
        payload = handler(self)
        
        # Inject global audit metadata into the root of the dictionary
        payload['metadata'] = {
            'exported_at': datetime.now().isoformat(),
            'system_node': 'alpha-financial-01'
        }
        return payload
    

transaction = TransactionExport(
    receipt_id="tx_99abc",
    status="processed",
    payment=PaymentDetails(
        card_number="4111222233334444",
        balance=1500.5,
        internal_codes=(99, 102)
    )
)

print("--- 1. Standard Python Dictionary Dump ---")
# Notice: internal_codes remains a Python tuple ()
python_dump = transaction.model_dump()
print(python_dump)
print(f"Tuple Type Intact: {type(python_dump['payment']['internal_codes'])}\n")


print("--- 2. JSON-Compatible Dictionary Dump ---")
# Notice: internal_codes is forced into a JSON array []
json_mode_dump = transaction.model_dump(mode='json')
print(json_mode_dump)
print(f"Tuple Converted to List: {type(json_mode_dump['payment']['internal_codes'])}\n")


print("--- 3. Direct JSON String Dump ---")
# Fully stringified JSON payload ready for a network request
json_string = transaction.model_dump_json(indent=2)
print(json_string, "\n")


print("--- 4. Pickling Support ---")
# Freezing the object into binary cache
binary_cache = pickle.dumps(transaction)
print(f"Binary Cache Size: {len(binary_cache)} bytes")

# Restoring the object perfectly
restored_transaction = pickle.loads(binary_cache)
print(f"Restored Object Status: {restored_transaction.status}")


class BaseUser(BaseModel):
    username: str

class AdminUser(BaseUser):
    # This field exists ONLY on the subclass
    super_secret_key: str

class APIResponse(BaseModel):
    internal_db_id: int = Field(exclude=True)

    error_code: int = Field(default=0, exclude_if=lambda v: v == 0)

    system_logs: str

    standard_user: BaseUser

    dynamic_user: SerializeAsAny[BaseUser]

    optional_tag: str | None = None

    @field_serializer('system_logs', mode='plain')
    @classmethod
    def apply_rbac_redaction(cls, value: str, info: FieldSerializationInfo) -> str:
        # Check the runtime context dictionary passed during the dump
        user_role = info.context.get('role') if info.context else 'guest'
        
        if user_role != 'admin':
            return "*** LOGS REDACTED FOR NON-ADMINS ***"
        return value


admin_instance = AdminUser(username="root_admin", super_secret_key="alpha-tango-99")

# Constructing the payload. Note: 'optional_tag' is NOT provided (it remains unset).
response = APIResponse(
    internal_db_id=99921,
    error_code=0,          # Will be dropped by exclude_if
    system_logs="Server CPU at 99%. Node 4 failing.",
    standard_user=admin_instance,
    dynamic_user=admin_instance
)

print("--- 1. Standard Dump (Guest Context & Strict Polymorphism) ---")
guest_dump = response.model_dump(
    context={'role': 'guest'}, 
    exclude_unset=True  # Drops 'optional_tag' because we didn't explicitly set it
)
# Notice:
# - internal_db_id is gone
# - error_code is gone (exclude_if)
# - system_logs are REDACTED via context
# - standard_user stripped 'super_secret_key' (Security Guardrail)
# - dynamic_user KEPT 'super_secret_key' (SerializeAsAny)
print(guest_dump, "\n")


print("--- 2. Admin Context Dump ---")
admin_dump = response.model_dump(
    context={'role': 'admin'}, 
    exclude_unset=True
)
# Notice: system_logs are now visible
print(admin_dump, "\n")


print("--- 3. Granular Dictionary Exclusion ---")
# Surgical extraction: Exclude the 'dynamic_user' entirely, and drop the 
# 'username' from the 'standard_user' dictionary.
surgical_dump = response.model_dump(
    exclude={
        'dynamic_user': True, 
        'standard_user': {'username'}
    }
)
print(surgical_dump)
    

    
