import logging
from datetime import datetime
from typing import Any, Optional,Generic, TypeVar, Annotated
from pydantic import BaseModel, ConfigDict, ValidationError,Field,StringConstraints

# Setup basic logging to see model_post_init output
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ==========================================
# 1. DEMONSTRATING: model_rebuild()
# ==========================================

class Guild(BaseModel):
    guild_name: str
    leader: Optional['Player'] = None  

class Player(BaseModel):
    username: str
    level: int
    guild: Optional[Guild] = None

Guild.model_rebuild()


# ==========================================
# 2. DEMONSTRATING: The 3 Validation Modes
# ==========================================

class GameSession(BaseModel):
    session_id: int
    player_count: int
    started_at: datetime

print("--- 1. NATIVE PYTHON MODE ---")
python_data = {
    "session_id": 99,
    "player_count": 4,
    "started_at": datetime(2026, 7, 3, 12, 0, 0)
}
session_one = GameSession.model_validate(python_data)
print(f"Python validated successfully: ID={session_one.session_id}\n")


print("--- 2. RAW JSON MODE (Rust Powered) ---")
json_string = '{"session_id": 101, "player_count": "12", "started_at": "2026-07-03T15:30:00"}'
session_two = GameSession.model_validate_json(json_string)
print(f"JSON parsed directly via Rust: Player Count={session_two.player_count}\n")


print("--- 3. STRINGS MODE (Lax vs Strict) ---")
form_data = {
    "session_id": "555",
    "player_count": "3",
    "started_at": "2026-07-03"
}

session_three = GameSession.model_validate_strings(form_data)
print(f"Lax Strings parsed: Started At={session_three.started_at}")

try:
    print("\nAttempting strict validation on incomplete datetime string...")
    GameSession.model_validate_strings(form_data, strict=True)
except ValidationError as e:
    print("❌ Strict validation blocked it! Error details:")
    print(e)


# ==========================================
# APPENDED CONTENT: NEW TOPICS
# ==========================================

print("\n--- 4. CREATING MODELS WITHOUT VALIDATION (model_construct) ---")
# Let's pass bad data intentionally using model_construct()
trusted_but_broken_data = {"session_id": "Not An Int", "player_count": "Ten", "started_at": "No Date"}

constructed_session = GameSession.model_construct(None, **trusted_but_broken_data)
print("⚠️ Model force-constructed without crashing!")
print(f"Resulting data types: session_id={type(constructed_session.session_id)}, player_count={type(constructed_session.player_count)}")


print("\n--- 5. MODEL POST INITIALIZATION (model_post_init) ---")
class ManagedUser(BaseModel):
    id: int
    username: str

    # Safe alternative to defining a custom __init__
    def model_post_init(self, context: Any) -> None:
        logging.info("🚀 ManagedUser successfully loaded into memory! ID: %d, Name: %s", self.id, self.username)

# Triggering the post_init hook
user_profile = ManagedUser(id=777, username="alien_slayer")


print("\n--- 6. ERROR HANDLING & ACCUMULATION ---")
class ComplexModel(BaseModel):
    list_of_ints: list[int]
    a_float: float


# This data contains multiple mistakes across different fields
corrupt_payload = {
    'list_of_ints': ['1', 2, 'bad_value'], # 'bad_value' cannot convert to int
    'a_float': 'not a float',              # This text cannot convert to a float
}

try:
    ComplexModel(**corrupt_payload)
except ValidationError as e:
    print(f"❌ Pydantic caught {e.error_count()} errors in a single sweep! Details below:")
    print(e)



# 1. Database Class containing sensitive backend data
class RealWorldDatabaseUser:
    def __init__(self, user_id: int, username: str, hashed_password: str, is_admin: bool):
        self.user_id = user_id
        self.username = username
        self.hashed_password = hashed_password  # Sensitive field!
        self.is_admin = is_admin                # Sensitive field!

# 2. Secure Pydantic Schema that cleans inputs and isolates public data
class UpgradedUserModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,  # Allows loading directly from database objects
        str_strip_whitespace=True, # Automatically trim spaces like " cyber_ninja " -> "cyber_ninja"
    )
    
    # ID must be positive and greater than zero
    user_id: int = Field(gt=0, description="The unique database identifier")
    
    # Username must be lowercase, alphanumeric, between 3 and 20 characters
    username: Annotated[
        str, 
        StringConstraints(
            to_lower=True, 
            min_length=3, 
            max_length=20, 
            pattern=r"^[a-z0-9_]+$"
        )
    ]

# ==========================================
# TESTING REAL-WORLD PRODUCTION CASES
# ==========================================

# Case A: Reading a safe record out of a Database Row
db_row = RealWorldDatabaseUser(
    user_id=1001, 
    username="  cyber_ninja  ", # Messy casing and extra spaces!
    hashed_password="scrypt$54321$secret_hash", 
    is_admin=False
)

# Validate and convert the DB row
clean_api_user = UpgradedUserModel.model_validate(db_row)

print("✅ SUCCESS: Database row safely extracted and normalized!")
print(f"Cleaned Username: '{clean_api_user.username}' (Spaces stripped, turned lowercase!)")
print(f"Serialized Output: {clean_api_user.model_dump()}")
# Notice that 'hashed_password' and 'is_admin' are safely dropped and hidden from the API!


# Case B: Catching Bad / Malicious Data coming from an incoming API call
print("\n--- TESTING API ERROR HANDLING ---")

bad_user_payloads = [
    {"user_id": -5, "username": "valid_name"},                 # Bug: Negative ID
    {"user_id": 102, "username": "lo"},                        # Bug: Too short
    {"user_id": 103, "username": "hacker$boy!"}                # Bug: Invalid characters
]

for idx, payload in enumerate(bad_user_payloads, 1):
    try:
        # Validating raw incoming input dictionary directly into our model
        UpgradedUserModel(**payload)
    except ValidationError as e:
        print(f"\n❌ Caught Validation Issue #{idx}:")
        for error in e.errors():
            print(f"   Field '{error['loc'][0]}': {error['msg']}")

print("\n--- 8. MODEL COPYING (Shallow vs Deep) ---")

class WeaponAsset(BaseModel):
    title: str
    power: int

class Hero(BaseModel):
    hero_name: str
    weapon: WeaponAsset

original_hero = Hero(hero_name="Vanguard", weapon=WeaponAsset(title="Laser Sword", power=50))

# SHALLOW COPY: Uses the same memory reference for nested items
shallow_hero = original_hero.model_copy(update={"hero_name": "Striker"})
# Changing the weapon power on the copy...
shallow_hero.weapon.power = 999
print(f"Shallow Copy Warning: Original power changed to {original_hero.weapon.power}!") 

# DEEP COPY: Keeps nested items completely separated in memory
original_hero.weapon.power = 50 # Resetting
deep_hero = original_hero.model_copy(deep=True, update={"hero_name": "Shadow"})
deep_hero.weapon.power = 999
print(f"Deep Copy Success: Original power safely stayed at {original_hero.weapon.power}!")


# ==========================================
# 9. DEMONSTRATING: Generic Models
# ==========================================
print("\n--- 9. GENERIC MODELS (API Envelopes) ---")

# Define our blank placeholder variable
T = TypeVar("T")

class InnerBox(BaseModel,Generic[T]):
    item: T

    @classmethod
    def model_parametrized_name(cls, params: tuple[type[Any], ...]) -> str:
        return f"{params[0].__name__.title()}Box"
    
class OuterBox(BaseModel,Generic[T]):
    outer_item : T 
    nested_box: InnerBox[T]
    
    @classmethod
    def model_parametrized_name(cls, params: tuple[type[Any], ...]) -> str:
        return  f"{params[0].__name__.title()}Box"
    
# =====================================================================
# TESTING OUR NESTED GENERICS
# =====================================================================

# =====================================================================
# TESTING OUR NESTED GENERICS
# =====================================================================

# 1. SUCCESS TEST: Let's make an Integer Box (Everything must be an int)
print("\n--- Testing Perfect Integer Box ---")
good_int_box: OuterBox[int] = OuterBox[int](
    outer_item=10, 
    nested_box=InnerBox[int](item=20)
)
print(repr(good_int_box)) 
# Output will look beautiful: IntBox(outer_item=10, nested_box=IntBox(item=20))


# 2. SUCCESS TEST: Let's make a String Box (Everything must be a string)
print("\n--- Testing Perfect String Box ---")
good_str_box: OuterBox[str] = OuterBox[str](
    outer_item="Hello External World", 
    nested_box=InnerBox[str](item="Hello Internal World")
)
print(repr(good_str_box))
# Output: StrBox(outer_item='Hello External World', nested_box=StrBox(item='Hello Internal World'))


# 3. CRASH TEST: Let's try to mix them up on purpose!
print("\n--- Testing Mixed Types (Expected Error) ---")
try:
    # This WILL crash because we locked the outer box to [int], 
    # Pass a raw dict with a string value. 
    # Pylance won't complain about the dict, but Pydantic will still catch it at runtime!
    broken_box = OuterBox[int](
        outer_item=5, 
        nested_box={"item": "Boom"}  # type: ignore
    )
except ValidationError as e:
    print("Caught the validation error successfully! 🛡️")
    print(e)



print("\n--- Working with Generics as Real Classes ---")

# 1. Use it as a type inside a normal class
class Shipment(BaseModel):
    tracking_id: int
    package: OuterBox[str]  # Real class type usage

ship = Shipment(
    tracking_id=5555,
    package=OuterBox[str](outer_item="Box Tape", nested_box={"item": "Shoes"})  # type:ignore
)
print(f"Shipment loaded successfully: {ship.tracking_id}")


# 2. Make a permanent subclass out of it
class SteelIntBox(OuterBox[int]):
    material: str = "Steel"  # You can even add new normal fields!

# Use it completely normally without any brackets!
permanent_box = SteelIntBox(outer_item=100, nested_box={"item": 200})  #type:ignore
print(f"Permanent Class representation: {repr(permanent_box)}")
print(f"Isinstance check works naturally now: {isinstance(permanent_box, SteelIntBox)}") 

print("\n--- Working Naturally Without repr() ---")

# 1. Create your object normally
user_box = OuterBox[str](
    outer_item="Premium User", 
    nested_box={"item": "Secret Key"}  #type:ignore
)

# 2. Extract data directly using dot notation
print(f"Direct access result -> Outer item is: {user_box.outer_item}")
print(f"Direct access result -> Nested item is: {user_box.nested_box.item}")

# 3. Export to a clean dict for APIs or Databases
dictionary_data = user_box.model_dump()
print(f"Clean Python Dictionary: {dictionary_data}")

print("\n--- 11. SELF-REFERENCING MODELS (Recursive data) ---")

class Node(BaseModel):
    name: str
    sub_node : Optional["Node"] = None

Node.model_rebuild()

tree = Node(
    name="Root Folder",
    sub_node=Node(
        name="Documents Folder",
        sub_node=Node(name="Resume.pdf")
    )
)

print(f"Top Level: {tree.name}")
print(f"Second Level: {tree.sub_node.name}") # type:ignore
print(f"Deepest Level: {tree.sub_node.sub_node.name}") #type:ignore 


print(f"Recursive Dict: {tree.model_dump()}")


print("\n--- 12. UNPARAMETRIZED GENERICS (Fallback Rules) ---")
from pydantic.main import TupleGenerator
from typing_extensions import TypeVar as ExtTypeVar

T_any =  ExtTypeVar('T_any')
U_int= ExtTypeVar('U_int',bound=int)
V_str = ExtTypeVar('V_str',default=str)

class FallbackModel(BaseModel,Generic[T_any,U_int,V_str]):
    t: T_any
    u: U_int
    v: V_str

fallback_success = FallbackModel(t="I can be anything", u=100, v="Using default string")
print(f"Fallback Success Object: {fallback_success.model_dump()}")


# 2. CRASH TEST: Violating the hidden fallback rules
print("\n--- Testing Fallback Violations (Expected Error) ---")
try:
    FallbackModel(
        t="Still fine here", 
        u="Not an Integer",  #type:ignore
        v=12345             
    )
except ValidationError as exc:
    print("Caught fallback validation errors successfully! 🛡️")
    print(exc)

print("\n--- 17. UNPARAMETRIZED SERIALIZATION & DATA RETENTION ---")

from pydantic import SerializeAsAny,model_validator
from typing_extensions import TypeVar as ExtTypeVar,Self

# 1. Base details structure
class ErrorDetails(BaseModel):
    foo: str

# 2. A custom subclass that adds an extra field ('bar')
class MyErrorDetails(ErrorDetails):
    bar: str

ErrorDataBound = ExtTypeVar("ErrorDataBound",bound=ErrorDetails)
ErrorDataDefault = ExtTypeVar('ErrorDataDefault', default=ErrorDetails)

class ErrorWithBound(BaseModel, Generic[ErrorDataBound]):
    message: str
    details: ErrorDataBound

class ErrorWithDefault(BaseModel, Generic[ErrorDataDefault]):
    message: str
    details: ErrorDataDefault

class ErrorWithSerializeAsAny(BaseModel, Generic[ErrorDataDefault]):
    message: str
    details: SerializeAsAny[ErrorDataDefault]

bound_error = ErrorWithBound(
    message="We just had an error",
    details=MyErrorDetails(foo="var", bar="var2")
)
print(f"Upper Bound Dump (Retains 'bar'): {bound_error.model_dump()}")


# --- TEST B: The Default Type Slicing ---
# Left unparametrized, so Pydantic forces ErrorDetails serialization rules. 'bar' is DELETED!
default_error = ErrorWithDefault(
    message="We just had an error",
    details=MyErrorDetails(foo="var", bar="var2")
)
print(f"Default Type Dump (Loses 'bar'): {default_error.model_dump()}")


# --- TEST C: Using SerializeAsAny to Save the Data ---
# Using SerializeAsAny tells the engine to stop stripping out subclass attributes!
fixed_error = ErrorWithSerializeAsAny(
    message="We just had an error",
    details=MyErrorDetails(foo="var", bar="baz")
)
print(f"SerializeAsAny Dump (Preserves 'bar'): {fixed_error.model_dump()}")


print("\n--- 18. NESTED REVALIDATION & VALIDATOR DOUBLE-TRIGGERING ---")

T = TypeVar("T")

class GenericModel(BaseModel,Generic[T]):
    a:T

    @classmethod
    def model_parametrized_name(cls, params: tuple[type[Any], ...]) -> str:
         return f"{params[0].__name__.title()}Test"
    

    # This completely replaces the model_validator block!
    def model_post_init(self, __context: Any) -> None:
        print("   🔍 [Post Init Hook] Guaranteed to run exactly ONCE!")
    
    # @model_validator(mode="after")
    # def validate_after(self)  ->Self:
    #     print("   🔍 [Validator Hook] Running 2 times...")
    #     return self

class ParentModel(BaseModel, Generic[T]):
    inner: GenericModel[T]  

# 2. Use model_validate with a raw dictionary, passing an [int] where [Any] is expected
raw_data = {
    "inner": GenericModel[int](a=1)
}

# This wrapper parsing is what forces Pydantic to run the validator twice!
m = ParentModel.model_validate(raw_data)

print(f"Final Model Representation: {repr(m)}")

error_unparam = ErrorWithBound(
    message='We just had an error',
    details=MyErrorDetails(foo='var', bar='var2')
)

# This assert will now pass cleanly!
assert error_unparam.model_dump() == {
    'message': 'We just had an error',
    'details': {
        'foo': 'var',
        'bar': 'var2', 
    },
}
print("✅ Assertion Passed: Case 1A (Unparametrized Upper Bound with SerializeAsAny retained extra child fields)")

TBound = TypeVar("TBound")
TNoBound = TypeVar("TNoBound")

class IntValue(BaseModel):
    value: int

class ItemBound(BaseModel, Generic[TBound]):
    item: TBound

class ItemNoBound(BaseModel, Generic[TNoBound]):
    item: TNoBound

item_bound_inferred = ItemBound(item=IntValue(value=3))
item_bound_explicit = ItemBound[IntValue](item=IntValue(value=3)) #type:ignore
item_no_bound_inferred = ItemNoBound(item=IntValue(value=3))
item_no_bound_explicit = ItemNoBound[IntValue](item=IntValue(value=3))

expected_permutation_dump = {'item': {'value': 3}}

# Asserting that every single permutation resolves to the exact same clean dictionary layout
assert item_bound_inferred.model_dump() == expected_permutation_dump
assert item_bound_explicit.model_dump() == expected_permutation_dump
assert item_no_bound_inferred.model_dump() == expected_permutation_dump
assert item_no_bound_explicit.model_dump() == expected_permutation_dump
print("✅ Assertion Passed: Case 2 (All 4 combination permutations outputted identical dictionary keys)")

ErrorDataDefaultT = ExtTypeVar('ErrorDataDefaultT', default=ErrorDetails)

class ErrorWithDefaultx(BaseModel, Generic[ErrorDataDefaultT]):
    message: str
    details: ErrorDataDefaultT

class SerializeAsAnyError(BaseModel, Generic[ErrorDataDefaultT]):
    message: str
    details: SerializeAsAny[ErrorDataDefaultT]

    

error_with_default = ErrorWithDefault(
    message='We just had an error',
    details=MyErrorDetails(foo='var', bar='var2'),
)

assert error_with_default.model_dump() == {
    'message': 'We just had an error',
    'details': {
        'foo': 'var', # ❌ 'bar' is cut out entirely by the default schema blueprint!
    },
}
print("✅ Assertion Passed: Case 3A (Default type variables automatically filter/slice child data)")

error_with_override = SerializeAsAnyError(
    message='We just had an error',
    details=MyErrorDetails(foo='var', bar='baz'),
)
assert error_with_override.model_dump() == {
    'message': 'We just had an error',
    'details': {
        'foo': 'var',
        'bar': 'baz', # 🛡️ Saved! SerializeAsAny safely guarded the dynamic properties.
    },
}
print("✅ Assertion Passed: Case 3B (SerializeAsAny successfully preserved out-of-spec attributes)")


print("\n--- 19. RUNNING COMPLETE DYNAMIC CONFIGURATION LIFE CYCLE ---")

from pydantic import BaseModel, ConfigDict, ValidationError, create_model, field_validator

class SystemUser(BaseModel):
    """The static parent blueprint providing the foundational fields."""
    username : str
    tier : str = "standard"

    def get_display_name(self) -> str:
        return f"@{self.username}"
    
def verify_clean_tag(cls, value: str) -> str:
    # 1. FIXED: Added () to properly invoke the string method.
    # 2. FIXED: Swapped .isalnum() for a check that permits underscores/dashes for tags
    if not value.replace("_", "").isalnum():
        raise ValueError("System tags must be completely alphanumeric!")
    
    return value.lower()

validation_reigstery = {
    "tag_cleanliness_validator" : field_validator('system_tag')(verify_clean_tag)
}

global_security_panel = ConfigDict(
    extra='forbid',
    str_strip_whitespace=True,
    frozen=True
)

EnterpriseUser = create_model(
    "EnterpriseUser",
    system_tag = (str, ...),
    company_id = (int, ...), # FIXED: Changed from str to int to match your input data layout
    __base__=SystemUser,
    __validators__=validation_reigstery,
    __config__=global_security_panel,
    __module__=__name__
)

print(f"Successfully manufactured dynamic class: {EnterpriseUser}")
print(f"Compiled schema field list: {list(EnterpriseUser.model_fields.keys())}")


user_instance = EnterpriseUser(
    username="alice_jones",
    system_tag="  admin_core  ",  #type:ignore
    company_id=101     #type:ignore
)

assert user_instance.username == "alice_jones"
assert user_instance.get_display_name() == "@alice_jones"

assert user_instance.system_tag == "admin_core"   #type:ignore
assert user_instance.company_id == 101    # FIXED: Now strictly passes integer comparisons! #type:ignore
print("✅ Assertion Passed: __base__, __validators__, and string stripping settings verified.")

try:
    EnterpriseUser(username="bob", system_tag="valid", company_id=1234,hacker_field="malicious_payload")   #type:ignore
    raise RuntimeError("Security Failure: Allowed an unlisted field past the guard!")
except ValidationError as e:
    assert "Extra inputs are not permitted" in e.errors()[0]['msg']
    print(" -> Correctly blocked unexpected extra input field fields.")

# 2. Try to pass a bad value (Blocked by __validators__)
try:
    EnterpriseUser(username="bob", system_tag="invalid_tag!!!",company_id=1234)  #type:ignore   
    raise RuntimeError("Security Failure: Allowed an illegal symbol past the validator!")
except ValidationError as e:
    # FIXED: This assert will now properly fire because the validator method executes!
    assert "System tags must be completely alphanumeric!" in e.errors()[0]['msg']
    print(" -> Correctly caught and rejected bad data values via custom logic.")

# 3. Try to overwrite an attribute (Blocked by frozen=True in __config__)
try:
    user_instance.company_id = 555 #type:ignore
    raise RuntimeError("Security Failure: Allowed a frozen object field to be altered!")
except ValidationError as e:
    assert "Instance is frozen" in e.errors()[0]['msg']
    print(" -> Correctly blocked active field mutation on the frozen model.")

print("✅ Assertion Passed: All security controls and constraints are operating flawlessly together!")


print("\n--- 20. EXECUTING ROOTMODEL PARADIGMS ---")

from pydantic import RootModel

PetsList = RootModel[list[str]]
PetsMap = RootModel[dict[str,str]]

list_instance = PetsList(['dog', 'cat'])
map_instance = PetsMap({'Otis': 'dog', 'Milo': 'cat'})

# Verify data is tucked into the .root attribute
assert list_instance.root == ['dog', 'cat']
assert map_instance.root == {'Otis': 'dog', 'Milo': 'cat'}

# Verify serialization strips out Pydantic wrappers entirely
assert list_instance.model_dump_json() == '["dog","cat"]'
assert map_instance.model_dump_json() == '{"Otis":"dog","Milo":"cat"}'
print("✅ Assertion Passed: Approach 1 (Clean array and dict serialization).")

class IterablePets(RootModel):
    root: list[str]

    def __iter__(self):
        return iter(self.root)
    
    def __getitem__(self, root):
        return self.root[root]
    
iterable_instance = IterablePets.model_validate(['dog', 'cat'])

assert iterable_instance[0] == 'dog'

assert[pet for pet in iterable_instance]  == ['dog', 'cat']

print("✅ Assertion Passed: Approach 2 (Dunder methods bypassed .root access).")

class DescribedPets(RootModel[list[str]]):
    def describe(self) ->str:
        return f'Pets: {", ".join(self.root)}'
    
custom_method_instance = DescribedPets.model_validate(['dog', 'cat'])

assert custom_method_instance.describe() == "Pets: dog, cat"

print("✅ Assertion Passed: Approach 3 (Custom methods evaluate inner roots cleanly).") 


print("\n---21 RUNNING MODEL ARCHITECTURE LIFE CYCLE ---")

import abc
from typing import ClassVar
from pydantic import BaseModel, ConfigDict, ValidationError

class ConcreteAbstarctModel(BaseModel,abc.ABC):
    a: int
    b: int = 2
    c: int = 1
    
    @abc.abstractmethod
    def mandatory_action(self) -> str:
        pass

class FinalSecuredUser(ConcreteAbstarctModel):
    model_config = ConfigDict(frozen=True)

    user_meta: dict
    
    # Class Variable (Excludes itself from data schemas entirely)
    SYSTEM_VERSION: ClassVar[str] = "v2.13"

    def mandatory_action(self) -> str:
        return f"Executing system task for version {self.SYSTEM_VERSION}"
    
instance = FinalSecuredUser(c=99, a=10, user_meta={"role": "admin"})

ordered_keys = list(instance.model_dump().keys())

assert ordered_keys == ['a', 'b', 'c', 'user_meta']
print("✅ Assertion Passed: Sequential field ordering preserved beautifully.")

assert "SYSTEM_VERSION" not in instance.model_dump()
assert FinalSecuredUser.SYSTEM_VERSION == "v2.13"
print("✅ Assertion Passed: ClassVar successfully bypassed instance processing hooks.")

# Verify top-level assignment blocks modifications
try:
    instance.a = 20
    raise RuntimeError("Security Failure: Frozen model top-level field was overwritten!")
except ValidationError as e:
    assert "Instance is frozen" in e.errors()[0]['msg']
    print(" -> Correctly blocked direct mutation modifications on frozen fields.")

# The Catch: Mutating the contents of the nested dictionary variable bypasses protection!
instance.user_meta["role"] = "compromised"
assert instance.user_meta["role"] == "compromised"
print("✅ Assertion Passed: Faux immutability edge-cases validated cleanly.")


print("\n--- 22 [last] RUNNING PRIVATE FIELD & COMPONENT EXTENSION TESTS ---")

import inspect
from random import randint
from typing import Any
from pydantic import BaseModel, Field, PrivateAttr

class HighlyConfiguredPet(BaseModel):
    id :int
    name:str
    species :str  = Field(alias="animal_type")


    _internal_id: int = PrivateAttr(default_factory=lambda: randint(1000, 9999))
    _tracking_flag: str = PrivateAttr()

    def model_post_init(self, context: Any) -> None:
        """Runs immediately after Pydantic structural validation completes."""
        self._tracking_flag = f"TRACK-{self.id}"

pet =  HighlyConfiguredPet(id=42,name="Bones", animal_type="dog")


assert pet._tracking_flag == "TRACK-42"
assert 1000 <= pet._internal_id <= 9999
assert "_internal_id" not in pet.model_dump()
print("✅ Assertion Passed: Private attributes isolated from serialization and schema maps.")

generated_sig = str(inspect.signature(HighlyConfiguredPet))
print(f"Generated Signature: {generated_sig}")

assert "animal_type" in generated_sig
assert "species" not in generated_sig
print("✅ Assertion Passed: Runtime signature engine honored field aliases correctly.")

matched_name = None
match pet:
    case HighlyConfiguredPet(species='dog',name=dog_name):
        matched_name = dog_name
    case _:
        raise RuntimeError("Matching Failure: Couldn't structurally unpack Pet schema!")
assert matched_name == "Bones"
print("✅ Assertion Passed: Structural pattern matching successfully evaluated schema state.")

class MemoryBoundaryTracker(BaseModel):
    items_list: list[int]

original_array = [10, 20, 30]
boundary_model = MemoryBoundaryTracker(items_list=original_array)

assert boundary_model.items_list == original_array
assert id(boundary_model.items_list) != id(original_array)

print("✅ Assertion Passed: Incoming mutable objects copied cleanly during initialization.")

print("\n🚀 All advanced Pydantic documentation cycles have successfully completed execution!")

                               # ✨💖👑  T H E   E N D  👑💖✨ #




    


