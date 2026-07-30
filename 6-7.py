import re
from typing import Annotated, Any, Literal, Optional, Union
from pydantic import BaseModel, Field, Discriminator, Tag, TypeAdapter, AfterValidator, ValidationError,PydanticUserError

class TextMessage(BaseModel):
    body: str
    msg_type: Literal["text"] = "text"

class MediaMessage(BaseModel):
    media_url: str
    msg_type: Literal["media"] = "media"

def select_message_router(v:Any) -> Optional[str]:
    if isinstance(v,dict):
         if "body" in v:
           return "text"
         
         if "media_url" in v :
               return  "media"
         else:
             return None
    
    return "text" if hasattr(v, "body") else "media" if hasattr(v, "media_url") else None

class BroadcastChannel(BaseModel):
    payload: Annotated[Union[Annotated[TextMessage, Tag("text")],
            Annotated[MediaMessage, Tag("media")],],Discriminator(select_message_router)]
    
class GPSCoordinates(BaseModel):
    latitude: float
    longitude: float

def route_fleet_target(v: Any) -> Optional[str]:
    if isinstance(v,int):
        return "id"
    if isinstance(v, (dict, BaseModel)):
        return "coords"
    return None

class LogisticsDispatch(BaseModel):
    target_destination: Annotated[Union[Annotated[int, Tag("id")],
            Annotated[GPSCoordinates, Tag("coords")]
        ],Discriminator(route_fleet_target)]
    



class MarketingEmail(BaseModel):
    medium: Literal["email"]
    tier: Literal["marketing"]
    campaign_id: int

class InvoiceEmail(BaseModel):
    medium: Literal["email"]
    tier: Literal["invoice"]
    balance_due: float

class EmergencySMS(BaseModel):
    medium: Literal["sms"]
    phone_number: str


EmailCategoryUnion = Annotated[Union[MarketingEmail,InvoiceEmail],Discriminator("tier")]

GlobalAlertUnion = Annotated[Union[EmailCategoryUnion, EmergencySMS], Field(discriminator="medium")]

class AlertDispatcher(BaseModel):
    notification: GlobalAlertUnion


class ProcessingNode(BaseModel):
    step: Union[str, 'ProcessingNode']

def route_secure_pipeline(v: Any) -> Optional[str]:
    if isinstance(v, str):
        return "str"
    if isinstance(v, (dict, BaseModel)):
        return "model"
    return None

class ShieldedPipeline(BaseModel):
    step: Annotated[Union[Annotated[str, Tag("str")],
            Annotated['ShieldedPipeline', Tag('model')]],Discriminator(
            route_secure_pipeline,
            custom_error_type="corrupted_pipeline_node",
            custom_error_message="The execution node structure is severely corrupted or unreadable.",
            custom_error_context={"security_clearance": "level_3"})]

ValidatedIntegerSequence = Annotated[list[int], AfterValidator(lambda x: sorted(x))]
StringMetadataIndex = dict[str, str]

standalone_stream_adapter = TypeAdapter(
    Union[
        Annotated[ValidatedIntegerSequence, Tag("ValidatedIntegerSequenceVariant")],
        Annotated[StringMetadataIndex, Tag("StringMetadataIndexVariant")],
    ]
)


# =====================================================================
print("--- 1. Testing: Dual-Input Rule (Callable Discriminator) ---")
channel_event = BroadcastChannel.model_validate({'payload': {'media_url': 'https://cdn.io/asset.png'}})
print(f"Verified Object Assignment: {repr(channel_event.payload)}")
print(f"Verified Serialization Dump: {channel_event.model_dump()}\n")

print("--- 2. Testing: Mixed Primitive & Model Router ---")
id_dispatch = LogisticsDispatch.model_validate({'target_destination': 4004})
coords_dispatch = LogisticsDispatch.model_validate({'target_destination': {'latitude': 37.77, 'longitude': -122.41}})
print(f"Primitive ID Node Target:    {id_dispatch.target_destination}")
print(f"Structured Model Node Target: {coords_dispatch.target_destination}\n")

print("--- 3. Testing: Multi-Tiered Nested Discriminators ---")
alert_system = AlertDispatcher(notification={'medium': 'email', 'tier': 'invoice', 'balance_due': 1500.75}) #type:ignore
print(f"Chained Router Resolves To Target Struct: {alert_system.notification}\n")

print("--- 4. Testing: Standalone Union TypeAdapter Parsing ---")
standalone_dictionary = standalone_stream_adapter.validate_python({'region_code': 'US_EAST_01', 'status': 'healthy'})
print(f"TypeAdapter Inline Output: {standalone_dictionary}\n")

print("--- 5. Testing: Verbose Standard Failures vs Engineered Custom Exceptions ---")
print("[Standard Recursive Union Trace Output]:")
try:
    ProcessingNode.model_validate({'step': {'step': {'step': False}}})
except ValidationError as error:
    print(f"Unmanaged Error Rows Emitted: {error.error_count()}")

print("\n[Engineered Core Discriminator Error Block Output]:")
try:
    ShieldedPipeline.model_validate({'step': {'step': {'step': False}}})
except ValidationError as custom_error:
    print(custom_error)

print("\n--- 6. Testing: Structural Variant Tagging Error Readout ---")
try:
    standalone_stream_adapter.validate_python(['non_parseable_string'])
except ValidationError as tag_error:
    print(tag_error)


                                   # -------------Chapter 7 -------------------# Thala for a reason 🕶️


from pydantic import BaseModel, Field, AliasPath, AliasChoices, AliasGenerator, ConfigDict, ValidationError

class LegacyIntegrationPayload(BaseModel):
    primary_developer:str = Field(validation_alias=AliasPath("contributors", 0))
    service_id:int = Field(validation_alias=AliasChoices("service_id", "srv_id"))
    deployment_region:str = Field(validation_alias=AliasChoices("system_region",AliasPath("tracking", "geo_zone")))
    
ingested_data = LegacyIntegrationPayload.model_validate({
    "contributors": ["Alice Engineer", "Bob Dev"],
    "srv_id": 9011,
    "tracking": {"geo_zone": "us-east-1"}
})


print(f"Extracted Developer: {ingested_data.primary_developer}")
print(f"Resolved Service ID: {ingested_data.service_id}")
print(f"Resolved Region:     {ingested_data.deployment_region}\n")


# =====================================================================
# 2. AUTOMATED ALIAS GENERATION & CONTROLLING PRECEDENCE
# =====================================================================

class TelemetryNode(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(validation_alias=lambda field: field.upper(),   
            serialization_alias=lambda field: field.lower()))
    
    node_status: str
    uptime_seconds: int
    
    # Precedence Overriding: Forces explicit override to remain intact via Priority 2
    assigned_cluster: str = Field(alias="CLUSTER_NODE_ID", alias_priority=2)
    
    # Yield Override: Explicitly commands generator to wipe out this alias via Priority 1
    hardware_version: str = Field(alias="ignored_legacy_tag", alias_priority=1)


telemetry = TelemetryNode.model_validate({
    "NODE_STATUS": "operational",
    "UPTIME_SECONDS": 86400,
    "CLUSTER_NODE_ID": "us-cluster-alpha",  # Respects priority 2
    "HARDWARE_VERSION": "v4.2"             # Respects priority 1 (Overridden to uppercase)
})


print(f"Serialized Output Matrix:")
print(telemetry.model_dump(by_alias=True), "\n")

class StrictAPIContract(BaseModel):
      client_identifier: str = Field(validation_alias="client_id",serialization_alias="clientID")
      model_config = ConfigDict(
        validate_by_alias=True,
        validate_by_name=True,      # Ingests using 'client_identifier' OR 'client_id'
        serialize_by_alias=False    # Standard model_dump defaults to standard attribute name
    )
      
print("--- 3. Testing: Execution Policy Boundaries ---")

# Scenario A: Validating via standard Python attribute name (Enabled by validate_by_name)
contract_by_name = StrictAPIContract.model_validate({"client_identifier": "PROD-99"})
print(f"Ingested by core property name: {contract_by_name.client_identifier}")

# Scenario B: Validating via the target validation alias
contract_by_alias = StrictAPIContract.model_validate({"client_id": "PROD-99"})
print(f"Ingested by verification alias:  {contract_by_alias.client_identifier}")

# Scenario C: Evaluating Model-Level Dump vs Runtime Dump Override
print(f"Default model dump output (serialize_by_alias=False):")
print(contract_by_alias.model_dump())

print(f"Runtime override dump output (by_alias=True):")
print(contract_by_alias.model_dump(by_alias=True), "\n")


print("--- 4. Testing: Error Guardrails ---")
try:
    class BrokenConfigurationModel(BaseModel):
        invalid_field: str = Field(validation_alias="invalid_alias")
        # CRITICAL TRAP: Cannot shut down both validation pathways completely
        model_config = ConfigDict(validate_by_alias=False, validate_by_name=False)
except PydanticUserError as error: 
    print(f"Caught expected Pydantic Configuration Exception: {error}")


                               # ✨💖👑  T H E   E N D  👑💖✨ #


