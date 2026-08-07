import os
import sys
import subprocess
import glob

def main():
    print("=" * 60)
    print("             AutoMail Test Suite Runner")
    print("=" * 60)
    
    # Locate all test files in the tests/ directory
    test_files = glob.glob(os.path.join("tests", "test_*.py"))
    
    if not test_files:
        print("No test files found in the 'tests/' directory.")
        sys.exit(1)
        
    print(f"Found {len(test_files)} test suite(s) to run:")
    for tf in test_files:
        print(f" - {tf}")
    print("=" * 60)
    
    results = {}
    
    for tf in test_files:
        # Convert path to module format, e.g., tests.test_generic
        module_name = tf.replace(os.sep, ".").replace(".py", "")
        print(f"\nRunning test suite: {module_name} ...")
        print("-" * 60)
        
        try:
            # Run the test suite as a module in a separate process
            result = subprocess.run(
                [sys.executable, "-m", module_name],
                check=False
            )
            
            if result.returncode == 0:
                results[module_name] = "PASSED"
                print(f"\n[OK] {module_name} completed successfully.")
            else:
                results[module_name] = f"FAILED (exit code {result.returncode})"
                print(f"\n[ERROR] {module_name} failed.")
        except Exception as e:
            results[module_name] = f"CRASHED ({str(e)})"
            print(f"\n[CRASH] {module_name} raised an exception: {e}")
            
    print("\n" + "=" * 60)
    print("                     Test Summary")
    print("=" * 60)
    
    all_passed = True
    for module, status in results.items():
        print(f"{module:<35} : {status}")
        if "PASSED" not in status:
            all_passed = False
            
    print("=" * 60)
    if all_passed:
        print("All test suites completed successfully!")
        sys.exit(0)
    else:
        print("Some test suites failed. Review the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
