import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Any
from pydantic import BaseModel, ConfigDict, Field, GetCoreSchemaHandler
from pydantic.fields import FieldInfo
from pydantic.json_schema import SkipJsonSchema
from pydantic_core import core_schema


def uppercase_generator(field_name: str, _field_info: FieldInfo) -> str:
    return field_name.upper()


def remove_defaults_modifier(schema_dict: dict[str, Any]) -> None:
    """Modifies the generated schema in-place by removing fallback values."""
    if "default" in schema_dict:
        schema_dict.pop("default")

@dataclass
class TitleCasedText:
    raw_text: str

    @classmethod
    def __get_pydantic_core_schema__(  # Fix: Must have double underscores on BOTH ends
        cls, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        assert source is TitleCasedText
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls._serialize,
                info_arg=False,
                return_schema=core_schema.str_schema(),
            ),
        )

    @staticmethod
    def _validate(value: str) -> "TitleCasedText":
        if not isinstance(value, str):
            raise ValueError("Input must be a valid string primitive")
        return TitleCasedText(raw_text=value.title())

    @staticmethod
    def _serialize(value: "TitleCasedText") -> str:
        return value.raw_text


# =====================================================================
# 3. ANNOTATED TYPES & MODELS
# =====================================================================
class ProductModel(BaseModel):
    product_id: int = Field(field_title_generator=uppercase_generator)
    product_name: str = Field(
        title="Custom Name",
        description="The commercial title of the item",
        examples=["Wireless Mouse"],
    )

    serial_code: str = Field(
        json_schema_extra={
            "title": "Secret Serial",
            "description": "Internal identifier tag",
            "examples": ["SN-2026-XYZ"],
        }
    )
    price: Decimal = Decimal("19.99")


# Reusable Type Alias with custom JSON schema metadata
CustomMetadataInt = Annotated[
    int,
    Field(json_schema_extra={"type": "integer", "format": "int64", "examples": [100, 200]})
]


class APIResponseBlueprint(BaseModel):
    # Global model configuration
    model_config = ConfigDict(
        title="MasterResponseSchema",
        json_schema_extra={"status_codes": [200, 201, 400]},
    )

    # A: Uses our custom dunder-validated type
    formatted_headline: TitleCasedText

    # B: Field applying programmatic schema reduction via a callable modifier
    retry_attempts: int = Field(default=3, json_schema_extra=remove_defaults_modifier)

    # C: Explicit type schema modification via our Annotated alias
    transaction_id: CustomMetadataInt

    # D: Field completely skipped from public documentation exposure
    internal_routing_hash: SkipJsonSchema[str] = "ROUTE-0x71-99"


# =====================================================================
# 4. VERIFICATION & RUNTIME EXECUTION
# =====================================================================
if __name__ == "__main__":
    # --- PART 1: Run ProductModel Schema Exports ---
    print("--- PRODUCT VALIDATION SCHEMA ---")
    print(json.dumps(ProductModel.model_json_schema(mode="validation"), indent=2))
    print("\n" + "=" * 50 + "\n")

    print("--- PRODUCT SERIALIZATION SCHEMA ---")
    print(json.dumps(ProductModel.model_json_schema(mode="serialization"), indent=2))
    print("\n" + "=" * 50 + "\n")

    # --- PART 2: Validate and Run Master BluePrint ---
    instance = APIResponseBlueprint(
    formatted_headline="hello python backend world",  # type: ignore
    transaction_id=12345
)

    print("--- PARSED INSTANCE DATA ---")
    print(instance)
    print("\n--- SERIALIZED EXPORT ---")
    print(instance.model_dump(mode="json"))
    print("\n" + "=" * 50 + "\n")

    print("--- CUSTOM GENERATED JSON SCHEMA ---")
    master_schema = APIResponseBlueprint.model_json_schema()
    print(json.dumps(master_schema, indent=2))


import json
from typing import Callable, Optional
from pydantic import BaseModel, Field
from pydantic_core import PydanticOmit, core_schema
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue, models_json_schema

class ProductionSchemaEngine(GenerateJsonSchema):
    """A customized Pydantic schema generation engine built to handle 

    complex runtime conditions and preserve exact dictionary key formatting.
    """
    def handle_invalid_for_json_schema(self, schema: core_schema.CoreSchema, error_info: str) -> JsonSchemaValue:
        raise PydanticOmit
    
    def sort(self, value: JsonSchemaValue, parent_key: str | None = None) -> JsonSchemaValue:
        return value
    
    

def default_callback_logic():
    return True

class ConfigurationProfile(BaseModel):
    meta_tags: str = Field(
        json_schema_extra={"z_index": 9, "alpha_code": "A1", "status": "active"}
    )
    # This live callable would normally cause a validation crash during export
    runtime_callback: Callable = default_callback_logic

class ExecutionPayload(BaseModel):
    payload_id: int
    associated_profile: ConfigurationProfile

if __name__ =="__main__":
    print("--- 1. SINGLE MODEL ISOLATED COMPILATION ---")

    isolated_schema = ConfigurationProfile.model_json_schema(schema_generator=ProductionSchemaEngine,mode="validation")
    print(json.dumps(isolated_schema,indent=2))

    print("\n" + "="*50 + "\n")

    print("--- 2. GLOBAL TOP-LEVEL MULTI-MODEL BUNDLE ---")
    # Bundle multiple unrelated or deeply linked models into one target definitions map
    _, multi_model_map = models_json_schema(
        models=[(ExecutionPayload, "validation"), (ConfigurationProfile, "validation")],
        title="Enterprise API Schema Blueprint",
        schema_generator=ProductionSchemaEngine
    )
    print(json.dumps(multi_model_map, indent=2))

