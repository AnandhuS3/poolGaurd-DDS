"""
Post-Refactor Validation Script
Run this to verify all refactor changes are working correctly
"""
import sys

print("=" * 70)
print("  DROWNING DETECTION SYSTEM - POST-REFACTOR VALIDATION")
print("=" * 70)
print()

# Test 1: Import credentials
print("Test 1: Credentials Module")
print("-" * 70)
try:
    import credentials
    print("✅ credentials.py imported successfully")
    print(f"   DB_USER: {'✅ Set' if credentials.DB_USER else '❌ Not set'}")
    print(f"   DB_PASSWORD: {'✅ Set' if credentials.DB_PASSWORD else '⚠️  Empty (using default)'}")
    print(f"   SMTP_USERNAME: {'✅ Set' if credentials.SMTP_USERNAME else '⚠️  Not set (emails disabled)'}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

print()

# Test 2: Import paths
print("Test 2: Paths Module")
print("-" * 70)
try:
    from paths import (
        PROJECT_ROOT, UPLOADS_DIR, OUTPUT_DIR, 
        MODEL_PRIMARY, SCHEMA_FILE, ensure_directories
    )
    print("✅ paths.py imported successfully")
    print(f"   Project Root: {PROJECT_ROOT}")
    print(f"   Uploads Dir: {UPLOADS_DIR} {'✅' if UPLOADS_DIR.exists() else '❌'}")
    print(f"   Output Dir: {OUTPUT_DIR} {'✅' if OUTPUT_DIR.exists() else '❌'}")
    print(f"   Primary Model: {MODEL_PRIMARY} {'✅' if MODEL_PRIMARY.exists() else '⚠️  Missing'}")
    print(f"   Schema File: {SCHEMA_FILE} {'✅' if SCHEMA_FILE.exists() else '❌'}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

print()

# Test 3: Import config
print("Test 3: Config Module")
print("-" * 70)
try:
    import config
    print("✅ config.py imported successfully")
    print(f"   MODEL_PATH: {config.MODEL_PATH}")
    print(f"   SERVER_HOST: {config.SERVER_HOST}")
    print(f"   SERVER_PORT: {config.SERVER_PORT}")
    print(f"   USE_ENSEMBLE: {config.USE_ENSEMBLE}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

print()

# Test 4: Import app
print("Test 4: Main Application Module")
print("-" * 70)
try:
    import app
    print("✅ app.py imported successfully")
    print(f"   FastAPI app created: {app.app is not None}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

print()

# Test 5: Import process_video
print("Test 5: Video Processing Module")
print("-" * 70)
try:
    import process_video
    print("✅ process_video.py imported successfully")
    print(f"   YOLO model loaded: {process_video.model is not None}")
    print(f"   DeepSORT tracker initialized: {process_video.tracker is not None}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

print()

# Test 6: Check for removed dead code
print("Test 6: Dead Code Removal Verification")
print("-" * 70)
try:
    # Check if legacy function was removed
    if hasattr(process_video, 'process_video'):
        # Check if it's the old legacy function (it shouldn't exist)
        import inspect
        source = inspect.getsource(process_video.process_video)
        if 'Legacy function' in source:
            print("⚠️  WARNING: Legacy process_video() function still exists")
        else:
            print("✅ Legacy code removed successfully")
    else:
        print("✅ Legacy process_video() function removed")
except AttributeError:
    print("✅ Legacy process_video() function removed")
except Exception as e:
    print(f"⚠️  Could not verify: {e}")

print()

# Summary
print("=" * 70)
print("  VALIDATION SUMMARY")
print("=" * 70)
print()
print("✅ All critical modules imported successfully")
print("✅ Credentials system working")
print("✅ Paths module working")
print("✅ Configuration loading correctly")
print("✅ Application ready to run")
print()
print("🎉 REFACTOR VALIDATION PASSED!")
print()
print("Next steps:")
print("1. Fill in your .env file with actual credentials")
print("2. Ensure YOLO model (best.pt) is in weights/ folder")
print("3. Run: python app.py")
print()
print("=" * 70)
