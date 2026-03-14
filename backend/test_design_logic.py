import sys
from unittest.mock import MagicMock

# 1. Mock heavy modules BEFORE any local imports
mock_modules = [
    "fastapi", "sqlalchemy", "sqlalchemy.orm", "pydantic", 
    "litellm", "inngest", "inngest_client", "auth", 
    "models", "model_resolver", "design_fallbacks"
]
for mod in mock_modules:
    sys.modules[mod] = MagicMock()

# 2. Add current dir to path
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# 3. Now import the functions to test
try:
    from design_intelligence import compose_project_context, build_design_brief
    from design_api import _resolve_theme_lock_dna, _derive_design_dna
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test_compose_project_context():
    print("Testing compose_project_context...")
    ctx = compose_project_context(
        product_name="TestApp",
        description="Testing context",
        direction="Modern Minimalist",
        reference_images=["http://example.com/img1.jpg"]
    )
    assert "New Design Direction: Modern Minimalist" in ctx
    assert "Reference Images Provided: 1 images" in ctx
    print("✓ compose_project_context includes direction and image count")

def test_resolve_theme_lock_dna():
    print("\nTesting _resolve_theme_lock_dna...")
    # Case 1: No direction
    # Mocking _derive_design_dna return value inside _resolve_theme_lock_dna is tricky 
    # if it's imported nearby, but here it's fine.
    dna_normal = _resolve_theme_lock_dna("Product: BenchSheet", None, None)
    assert "palette" in dna_normal
    print(f"✓ Normal DNA (no direction) returns palette")

    # Case 2: With direction
    dna_override = _resolve_theme_lock_dna("Product: BenchSheet", None, None, direction="Red theme")
    assert dna_override == {"palette": {}}
    print("✓ Override DNA (with direction) returns empty palette (AI freedom)")

def test_light_theme_logic():
    print("\nTesting light theme logic in _derive_design_dna...")
    
    # Case 1: Force light theme
    dna_light = _derive_design_dna("Product: TestApp", theme_preference="light")
    assert dna_light["palette"]["bg"].lower().startswith("#f")
    
    # Case 2: Auto pick light theme from context
    ctx_light = "Product: TestApp\nTheme Preference: light"
    dna_auto_light = _derive_design_dna(ctx_light, theme_preference="auto")
    assert dna_auto_light["palette"]["bg"].lower().startswith("#f")
    print("✓ _derive_design_dna correctly applies light theme preference")

if __name__ == "__main__":
    try:
        test_compose_project_context()
        test_resolve_theme_lock_dna()
        test_light_theme_logic()
        print("\nAll logic tests PASSED!")
    except AssertionError as e:
        print(f"\nTest FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
