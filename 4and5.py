from datetime import date
from typing import Annotated, Any, Optional,TypeVar,Union,Generic
import pydantic_core
from typing_extensions import TypeAliasType
from annotated_types import Gt,Len
from pydantic import BaseModel, ConfigDict, ValidationError, WrapValidator,Field,TypeAdapter
def default_on_error(v: Any, handler: Any) -> Any:
    """
    Intercepts partial JSON errors when fields go missing mid-stream,
    forcing the engine to use the field's predefined default instead.
    """
    try:
        return handler(v)
    except ValidationError as exc:

        if all(e['type'] == 'missing' for e in exc.errors()):
            print("\n⚠️   [Safety Net Triggered] Truncated nested stream detected. Defaulting field to None.")
            raise pydantic_core.PydanticUseDefault()
        raise


class NestedModel(BaseModel):
    x: int
    y: str

class UltimateJsonModel(BaseModel):
    model_config = ConfigDict(strict=True, cache_strings="keys")

    when: date
    where: tuple[int, int]

    nested: Annotated[Optional[NestedModel], WrapValidator(default_on_error)] = None


print("=== 1. TOPIC 1: STRICT BUILT-IN JSON PARSING ===")
json_data = '{"when": "1987-01-28", "where": [51, -1]}'
    
model_instance = UltimateJsonModel.model_validate_json(json_data)
print(f"Success via model_validate_json:\n  {repr(model_instance)}\n")

try:
        UltimateJsonModel.model_validate({'when': '1987-01-28', 'where': [51, -1]})
except ValidationError as e:
        print(f"Expected Failure via model_validate (dict):\n{e}\n")


print("=== 2. TOPIC 2 & 3: PARTIAL JSON PARSING & LLM OUTPUTS ===")
partial_stream = '{"when": "2026-07-10", "where": [12, 34], "nested": {"x": 5, "y":'

salvaged_dict = pydantic_core.from_json(partial_stream, allow_partial=True)
print(f"Salvaged Python Dict from Jiter: {salvaged_dict}")
    
    # FIX: Pass strict=False here so the dictionary parser can convert the string date safely
streaming_result = UltimateJsonModel.model_validate(salvaged_dict, strict=False)
print(f"Final Recovered Model: {repr(streaming_result)}\n")


print("=== 3. TOPIC 4: STRING CACHING VARIATIONS ===")
payload = '{"when": "2026-07-10", "where": [0, 0]}'
    
cache_all = pydantic_core.from_json(payload, cache_strings='all')
cache_disabled = pydantic_core.from_json(payload, cache_strings=False)
print(f"Direct parsed with cache_strings='all': {cache_all}")
print(f"Direct parsed with cache_strings=False: {cache_disabled}\n")

                                                        # Types #

PositiveIntField = Annotated[int,Field(gt=0)]

PositiveIntAnnotated = Annotated[int,Gt(0)]

field_adapter = TypeAdapter(PositiveIntField)

annotated_adapter = TypeAdapter(PositiveIntAnnotated)

print("Valid input (Field):", field_adapter.validate_python(1))
print("Valid input (Gt):", annotated_adapter.validate_python(42))

try:
     field_adapter.validate_python(-1)
except ValidationError as exc:
     print("\n[Error Caught] Field constraint failed:")
     print(exc)

try:
    annotated_adapter.validate_python(0)
except ValidationError as exc:
    print("\n[Error Caught] Gt constraint failed:")
    print(exc)


T = TypeVar("T")

ShortList =  Annotated[list[T],Len(max_length=4)]

PositiveList = list[Annotated[T, Gt(0)]]

int_list_adapter = TypeAdapter(ShortList[int])

print("Valid short list:", int_list_adapter.validate_python([1, 2, 3, 4]))

try:
    int_list_adapter.validate_python([1, 2, 3, 4, 5])
except ValidationError as exc:
    print("\n[Error Caught] ShortList validation failed (too many items):")
    print(exc)

float_list_adapter = TypeAdapter(PositiveList[float])

print("Valid positive list:", float_list_adapter.validate_python([1.0, 5.5, 10.2]))

try:
    float_list_adapter.validate_python([1.0, -1.0, 3.4])
except ValidationError as exc:
    print("\n[Error Caught] PositiveList validation failed (negative value found):")
    print(exc)

ScoreInt =  TypeAliasType('ScoreInt',Annotated[int,Gt(0)])

T = TypeVar('T')

BoundedList = TypeAliasType('BoundedList',Annotated[list[T],Len(max_length=3)],
                            type_params=(T,))

FolderTree = TypeAliasType(
    'FolderTree',
    'Union[str, dict[str, FolderTree]]' #type:ignore
)

class SystemPayload(BaseModel):
     player_one_score :ScoreInt
     player_two_score :ScoreInt

     recent_actions : BoundedList[int]

     bonus_score: ScoreInt = Field(default=100)

print("--- Unified API JSON Schema ($defs) ---")
import json
print(json.dumps(SystemPayload.model_json_schema(), indent=2))

# Validate our recursive directory map tree structure
print("\n--- Validating Deep Recursive Data ---")
tree_adapter = TypeAdapter(FolderTree)
mock_hard_drive = {
    "usr": {
        "local": {
            "bin": "python3"
        }
    },
    "var": "log_file.txt"
}

validated_tree = tree_adapter.validate_python(mock_hard_drive)
print("Successfully parsed recursive folder structure without infinite loops!")


from dataclasses import dataclass
from typing import Annotated, Any, Callable, Union
from pydantic_core import CoreSchema, core_schema
from pydantic import (
    BaseModel,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    GetPydanticSchema,
    TypeAdapter,
    ValidationError,
)
from pydantic.json_schema import JsonSchemaValue

# =====================================================================
# STRATEGY 1: AS A METHOD ON A CUSTOM TYPE (Subclassing)
# Use case: When you own the class and want it to carry validation[cite: 1].
# =====================================================================

class Username(str):
     @classmethod
     def __get_pydantic_core_schema__(cls,source_type:Any,handler:GetCoreSchemaHandler) -> CoreSchema:
          return core_schema.no_info_after_validator_function(cls,handler(str))
     
username_adapter = TypeAdapter(Username)
resolved_username = username_adapter.validate_python('abc')

assert isinstance(resolved_username, Username)
assert resolved_username == 'abc'
print("✓ Strategy 1 (Custom Type Subclass) passed successfully.")

@dataclass(frozen=True)
class MyAfterValidator:
     func: Callable[[Any], Any]

     def __get_pydantic_core_schema__(self,source_type:Any,handler:GetCoreSchemaHandler) -> CoreSchema:
          return core_schema.no_info_after_validator_function(self.func, handler(source_type))
     
LowercaseString = Annotated[str,MyAfterValidator(str.lower)]

class ProfileModel(BaseModel):
    name: LowercaseString

# Practice verification
profile = ProfileModel(name='ABC')
assert profile.name == 'abc'
print("✓ Strategy 2 (Annotation Metadata Class) passed successfully.")


class ThirdPartyType:
    x: int
    def __init__(self):
        self.x = 0

class _ThirdPartyTypePydanticAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        
        # Converts an inbound raw integer into our complex object[cite: 1]
        def validate_from_int(value: int) -> ThirdPartyType:
            result = ThirdPartyType()
            result.x = value
            return result
            
        # Pipeline: Force an integer schema first, then send it to the factory function[cite: 1]
        from_int_schema = core_schema.chain_schema([
            core_schema.int_schema(),
            core_schema.no_info_plain_validator_function(validate_from_int),
        ])
        
        return core_schema.json_or_python_schema(
            json_schema=from_int_schema,
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ThirdPartyType),  # Rule A: Accept pre-made objects[cite: 1]
                from_int_schema,                                 # Rule B: Fallback to parsing raw integers[cite: 1]
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: instance.x                      # Rule C: Convert object back to integer on dump[cite: 1]
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        # Spoofs API docs so the external schema is documented purely as an integer[cite: 1]
        return handler(core_schema.int_schema())

PydanticThirdPartyType = Annotated[ThirdPartyType, _ThirdPartyTypePydanticAnnotation]

class ExternalIntegrationModel(BaseModel):
    third_party_field: PydanticThirdPartyType

model_from_int = ExternalIntegrationModel(third_party_field=5)  #type:ignore
assert isinstance(model_from_int.third_party_field, ThirdPartyType)
assert model_from_int.third_party_field.x == 5
assert model_from_int.model_dump() == {'third_party_field': 5}

# Practice verification: Passing a pre-instantiated object instance[cite: 1]
external_obj = ThirdPartyType()
external_obj.x = 99
model_from_obj = ExternalIntegrationModel(third_party_field=external_obj)
assert model_from_obj.third_party_field.x == 99
assert model_from_obj.model_dump() == {'third_party_field': 99}

# Practice verification: Ensuring bad inputs fail gracefully[cite: 1]
try:
    ExternalIntegrationModel(third_party_field='invalid_string') #type:ignore
except ValidationError:
    print("✓ Strategy 3 (Third-Party Type Wrapper) caught bad data successfully.")

# =====================================================================
# STRATEGY 4: REDUCING BOILERPLATE WITH GetPydanticSchema
# Use case: Quick inline transformations without building extra helper classes[cite: 1].
# =====================================================================

class InlineMultiplierModel(BaseModel):
    echo_word: Annotated[str,GetPydanticSchema(
            lambda target_type, handler: core_schema.no_info_after_validator_function(
                lambda text: text * 2, handler(target_type)
            )
        ),]
inline_test = InlineMultiplierModel(echo_word='Go')
assert inline_test.echo_word == 'GoGo'
print("✓ Strategy 4 (GetPydanticSchema Inline Lambda) passed successfully.")

print("\n🚀 All core schema custom practices executed flawlessly!")



class Aryan(str):
    @classmethod
    def __get_pydantic_core_schema__(
            cls,source_type:Any,handler:GetCoreSchemaHandler
    ) -> CoreSchema:
        
        return core_schema.no_info_after_validator_function(lambda v: cls(f"You are the biggest ARYAN - DEAR {v}"), 
            handler(str))

aryan_adapter = TypeAdapter(Aryan)
aryan = aryan_adapter.validate_python("Ridhan")

print(aryan)

class ThirdPartyTypeX:
    x: Any
    def __init__(self):
        self.x = 0

class Xxyz:
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: GetCoreSchemaHandler) -> CoreSchema:

        def validate_from_str(value: str) -> ThirdPartyTypeX:
    # Strip away text prefixes if they exist
           clean_number = int(value.replace("SCORE_", ""))
           result = ThirdPartyTypeX()
           result.x = clean_number
           return result

# You could add this new pipeline to your union_schema switches!
        
        # ✅ FIXED: Wrapped the schemas inside a list []
        from_str_pipeline = core_schema.chain_schema([
            core_schema.str_schema(),
            core_schema.no_info_plain_validator_function(validate_from_str)
        ])

        return core_schema.json_or_python_schema(
            json_schema=from_str_pipeline,
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ThirdPartyTypeX), 
                from_str_pipeline
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: f"SCORE_{instance.x}")
        )
    
    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(core_schema.int_schema())

# 3. Integration & Testing
PydanticThirdPartyTypey = Annotated[ThirdPartyTypeX, Xxyz]

class ExternalIntegrationyModel(BaseModel):
    third_party_field: PydanticThirdPartyTypey

# Running validation directly via the BaseModel!
model_from_inyt = ExternalIntegrationyModel(third_party_field="SCORE_8")  # type: ignore

# Let's inspect the resolved field object
print(f"Field Object Type: {type(model_from_inyt.third_party_field)}")
print(f"Extracted Value: {model_from_inyt.third_party_field.x}")
print(f"Serialized Output: {model_from_inyt.model_dump()}")

import re 

class PostgresEngine:
    def __init__(self, host: str, db_name: str):
        self.host = host
        self.db_name = db_name

class MySQLEngine:
    def __init__(self, host: str, db_name: str):
        self.host = host
        self.db_name = db_name
# 1. THE ADVANCED GENERIC CONTAINER
EngineType = TypeVar('EngineType')


class MongoDBEngine:
    # 🌟 MongoDB needs an extra argument: 'hi'!
    def __init__(self, host: str, db_name: str, hi: str):
        self.host = host
        self.db_name = db_name
        self.hi = hi


from pydantic import ValidationInfo
from typing_extensions import get_args, get_origin

class DatabaseProfile(Generic[EngineType]):
    def __init__(self, connection_name: str, engine: EngineType):
        self.connection_name = connection_name  # Dynamically sourced from field name!
        self.engine = engine                    # Dynamically validated generic type!

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        
        # Concept 1: Extract the inner generic argument (e.g., PostgresEngine)
        origin = get_origin(source_type)
        if origin is None:
            inner_type = Any
        else:   
            inner_type = get_args(source_type)[0]

        # Generate the blueprint for the inner type dynamically!
        inner_engine_schema = handler.generate_schema(inner_type)

        # Concept 2: The Bridge Function that captures field names and values
        def validate_database_url(value: str, info: ValidationInfo) -> DatabaseProfile[Any]:
            # Clean regex string matching any protocol, host, db_name, and optional ?query parameters
            pattern = r"\w+://([^/]+)/([^?]+)(?:\?(.+))?"
            match = re.match(pattern, value)
            if not match:
                raise ValueError("Invalid Database URL format!")
            
            # ✅ FIX 1: Safely extract the three matching parts from the URL
            host, db_name, extra = match.groups()
            
            init_args = {"host": host, "db_name": db_name}
            
            # Extract additional key-value query parameters dynamically if they exist
            if extra and "=" in extra:
                key, val = extra.split("=")
                init_args[key] = val
            
            # ✅ FIX 2: Simplified assignment expression without complex static type combinations
            engine_instance = inner_type(**init_args)  #type:ignore
            
            f_name = info.field_name if info.field_name is not None else "default_profile"
            return cls(connection_name=f_name, engine=engine_instance)
        # Build a chain pipeline using with_info to pass the context metadata
        from_str_pipeline = core_schema.chain_schema([
            core_schema.str_schema(),
            core_schema.with_info_after_validator_function(validate_database_url,core_schema.str_schema())
        ])

        return core_schema.json_or_python_schema(
            json_schema=from_str_pipeline,
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(cls),
                from_str_pipeline
            ])
        )
    
class MultiDbSettings(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    
    # We pass different types into the exact same container class!
    postgres_node: DatabaseProfile[PostgresEngine]
    mysql_node: DatabaseProfile[MySQLEngine]
    mongodb_node: DatabaseProfile[MongoDBEngine] #


# 4. RUNNING THE CODE
config = MultiDbSettings(
    postgres_node="postgresql://localhost:5432/prod_db", # type: ignore
    mysql_node="mysql://127.0.0.1:3306/analytics_db",#type:ignore
        mongodb_node="mongodb://localhost:27017/nosql_db?hi=world"    # type: ignore
)

# 🖥️ VERIFYING OUTPUT
print(f"--- Node 1 ---")
print(f"Field Name:  {config.postgres_node.connection_name}")
print(f"Engine Type: {type(config.postgres_node.engine).__name__}")
print(f"Host Target: {config.postgres_node.engine.host}")

print(f"\n--- Node 2 ---")
print(f"Field Name:  {config.mysql_node.connection_name}")
print(f"Engine Type: {type(config.mysql_node.engine).__name__}")
print(f"Host Target: {config.mysql_node.engine.host}")

print(f"--- Node 3: MongoDB ---")
print(f"Field:      {config.mongodb_node.connection_name}")
print(f"Engine:     {type(config.mongodb_node.engine).__name__}")
print(f"Host:       {config.mongodb_node.engine.host}")
print(f"Extra 'hi': {config.mongodb_node.engine.hi}")

                               # ✨💖👑  T H E   E N D  👑💖✨ #






         
