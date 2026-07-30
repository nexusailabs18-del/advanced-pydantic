from pydantic import BaseModel, Field, ValidationError, AliasChoices
from pydantic.dataclasses import dataclass
from dataclasses import InitVar


print("--- TESTING DEFAULTS & MEMORY BLOCKS ---")


class SystemConfig(BaseModel):
    port:int = Field(default="8080",validate_default=True)
    cluster_nodes : list[str] = ["node_alpha"]  #type:ignore

config_instance = SystemConfig()
assert config_instance.port == 8080

another_config = SystemConfig()
config_instance.cluster_nodes.append("node_beta")

assert "node_beta" not in another_config.cluster_nodes

print("✅ Defaults validated and mutable memory arrays perfectly isolated.")

print("\n--- TESTING ALIAS PRECEDENCE HIERARCHY ---")

class DataPayload(BaseModel):
    secret_key : str = Field(alias="key",validation_alias=AliasChoices("key", "X-API-KEY"),serialization_alias='my_field')

m= DataPayload(key="hiithere")

print(m.model_dump(by_alias=True))

incoming_request = {"X-API-KEY": "super_secret_token_abc123"}

processed_payload = DataPayload.model_validate(incoming_request)

assert processed_payload.secret_key == "super_secret_token_abc123"
print("✅ Precedence verified: validation_alias took absolute input priority.")
print("\n--- TESTING FIELD INSPECTION ---")

class MetaModel(BaseModel):
    hardcoded_field :int = Field(gt=5,description="A strict metadata matrics")

field_metadata = MetaModel.model_fields["hardcoded_field"]

print(f" -> Field Type Blueprint: {field_metadata.annotation}")
print(f" -> Field Constraints: {field_metadata.metadata}")

assert field_metadata.annotation == int
print("✅ Field inspection extracted successfully from the model class metadata registry.")

from pydantic import BaseModel, Field, ValidationError

class TightSecurityUser(BaseModel):
    # This MUST be a real string. No conversions.
    api_key: str = Field(strict=True)
    # This can be an integer OR a string that looks like an integer.
    age: int = Field(strict=False)

# --- CASE 1: This passes ---
# 'api_key' is a real string. 'age' is a string but strict=False allows it to convert to 42.
good_user = TightSecurityUser(api_key="KEY_123", age="42") #type:ignore
print(good_user.age)  # Output: 42 (It was converted into a real int!)

# --- CASE 2: This crashes ---
try:
    # We passed an integer (12345) to a strict string field!
    broken_user = TightSecurityUser(api_key=12345, age=25) #type:ignore
except ValidationError as e:
    print("❌ Blocked by strict=True!")

class Account(BaseModel):
    username: str = Field(repr=True)  # Shows up when printed
    password:str = Field(repr=False)

user = Account(username="neon_knight",password="SuperSecretPassword123")
print(user)

print(user.password) 


from pydantic import Field
from pydantic.dataclasses import dataclass

from pydantic import Field
from pydantic.dataclasses import dataclass

@dataclass
class GameWeapon:
    weapon_name: str
    rarity_multiplier: float = Field(init_var=True)
    base_damage: int = Field(kw_only=True)

# FIX: Explicitly name rarity_multiplier
sword = GameWeapon("Excalibur", rarity_multiplier=2.5, base_damage=100)

print(sword)


from typing import Annotated, Literal, Union,Any
import warnings
from pydantic import BaseModel, Discriminator, Field, Tag, ValidationError,EmailStr,computed_field
from pydantic_extra_types.phone_numbers import PhoneNumber

print("--- TESTING POLYMORPHIC DISCRIMINATOR ---")

class EmailNotification(BaseModel):
    delivery_channel:Literal['email']
    email_address: EmailStr

class SMSNotification(BaseModel):
    sms_kind: Literal['sms']
    phone_number: PhoneNumber

def notification_router(data: Any) -> str | None: 
    if isinstance(data, dict):
        # If neither key exists, dict.get returns None cleanly
        return data.get('delivery_channel', data.get('sms_kind'))
        
    # For objects, safely fetch or return None
    return getattr(data, 'delivery_channel', getattr(data, 'sms_kind', None))

class AlertManager(BaseModel):
    payload:Union[
        Annotated[EmailNotification,Tag('email')],
        Annotated[SMSNotification,Tag('sms')]] = Field(discriminator=Discriminator(notification_router))
    
email_data = {"payload": {"delivery_channel": "email", "email_address": "dev@test.com"}}
# Payload 2 uses 'sms_kind'
sms_data = {"payload": {"sms_kind": "sms", "phone_number": "+917355521452"}}

instance_email = AlertManager.model_validate(email_data)
instance_sms = AlertManager.model_validate(sms_data)

assert isinstance(instance_email.payload,EmailNotification)
assert isinstance(instance_sms.payload, SMSNotification)
print("✅ Discriminator Success: Correctly routed payloads with mismatched structural keys!")

print("\n--- TESTING FIELD-LEVEL IMMUTABILITY ---")

class DatabaseRecord(BaseModel):
    record_id: int = Field(frozen=True)  # Strictly Immutably Locked
    entry_data: str                      # Fully Mutable

record = DatabaseRecord(record_id=9901, entry_data="Initial State Cluster Alpha")

# This is fine: Modifying an unfrozen field works seamlessly
record.entry_data = "Updated State Cluster Beta"
assert record.entry_data == "Updated State Cluster Beta"

# This will crash: Modifying a frozen field throws a clear ValidationError
try:
    record.record_id = 5555
except ValidationError as e:
    print("❌ Mutation Blocked Successfully! Pydantic Engine caught the violation:")


print("--- 🎓 THE FINAL PYDANTIC FIELD CAPSTONE 🎓 ---")


class RetailProduct(BaseModel):
    product_name:str
    wholesale_cost:float=Field(exclude=True)
    legacy_sku:str=Field(default="UKNOWN",
                         deprecated="🚨 'legacy_sku' is being removed in v2.0! Use 'product_name' instead.")
    
    @computed_field
    @property
    def retail_price(self) -> float:
        # A simple 50% markup calculation
        return self.wholesale_cost * 1.50

laptop = RetailProduct(product_name="ProBook 2026", wholesale_cost=1000.0, legacy_sku="SKU-9921")
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    old_id = laptop.legacy_sku 
    print(f"⚠️    Caught Warning: {w[-1].message}")

api_payload = laptop.model_dump()

print("\n📦   Final API Export Payload:")
print(api_payload)

assert "wholesale_cost" not in api_payload
# Verify Computed Field worked
assert api_payload["retail_price"]== 1500.0

print("\n✅ Success! Cost was hidden, warnings fired, and retail price was dynamically calculated!")

                                  # ✨💖👑  T H E   E N D  👑💖✨ #




    


