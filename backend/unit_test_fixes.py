import sys
import json
import os

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    from design_intelligence import compose_project_context, build_design_brief
    from design_api import _resolve_theme_lock_dna, _derive_design_dna
except ImportError as e:
    print(f"Import failed: {e}")
    print(f"Current sys.path: {sys.path}")
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
    dna_normal = _resolve_theme_lock_dna("Product: BenchSheet", None, None)
    assert "palette" in dna_normal
    assert dna_normal["palette"] != {}
    print(f"✓ Normal DNA (no direction) returns palette: {dna_normal['palette'].get('name')}")

    # Case 2: With direction
    # My fix: If direction is present, it returns an empty palette to let the AI be free
    dna_override = _resolve_theme_lock_dna("Product: BenchSheet", None, None, direction="Red theme")
    assert dna_override == {"palette": {}}
    print("✓ Override DNA (with direction) returns empty palette (AI freedom)")

def test_light_theme_logic():
    print("\nTesting light theme logic in _derive_design_dna...")
    
    # Case 1: Force light theme
    dna_light = _derive_design_dna("Product: TestApp", theme_preference="light")
    print(f"  Light theme palette: {dna_light['palette'].get('name')} (bg: {dna_light['palette'].get('bg')})")
    assert dna_light["palette"]["bg"].lower().startswith("#f")  # Light bg should start with #f...
    
    # Case 2: Auto pick light theme from context
    ctx_light = "Product: TestApp\nTheme Preference: light"
    dna_auto_light = _derive_design_dna(ctx_light, theme_preference="auto")
    assert dna_auto_light["palette"]["bg"].lower().startswith("#f")
    print("✓ _derive_design_dna correctly identifies and applies light theme preference")

def test_build_design_brief_query_dilution():
    print("\nTesting build_design_brief query construction...")
    
    # Verify the function runs and handles direction.
    ctx = "Product: TestApp\nDescription: A test app\nCDO Design Recommendations: Use GREEN"
    brief = build_design_brief(ctx, direction="Blue theme")
    
    # Check if direction is present in the brief
    assert brief["direction"] == "Blue theme"
    print("✓ build_design_brief accepts and processes direction")

if __name__ == "__main__":
    try:
        test_compose_project_context()
        test_resolve_theme_lock_dna()
        test_light_theme_logic()
        test_build_design_brief_query_dilution()
        print("\nAll unit tests PASSED!")
    except AssertionError as e:
        print(f"\nTest FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
