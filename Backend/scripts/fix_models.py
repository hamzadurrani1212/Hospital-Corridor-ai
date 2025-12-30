import os
import shutil
from pathlib import Path

def fix_model_structure():
    home = Path.home()
    insightface_dir = home / ".insightface" / "models"
    target_dir = insightface_dir / "buffalo_sc"
    
    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Checking directory: {insightface_dir}")
    
    # Expected files for buffalo_sc
    expected_files = ["det_500m.onnx", "w600k_mbf.onnx", "1k3d68.onnx", "2d106det.onnx"]
    
    # Find any ONNX files in the root models dir and move them
    moved_count = 0
    if insightface_dir.exists():
        for item in insightface_dir.iterdir():
            if item.is_file() and item.suffix == ".onnx":
                print(f"Moving {item.name} to {target_dir}")
                shutil.move(str(item), str(target_dir / item.name))
                moved_count += 1
            elif item.is_dir() and item.name == "buffalo_sc":
                print("scaning buffalo_sc folder...")
                for subitem in item.iterdir():
                     print(f" - Found inside buffalo_sc: {subitem.name}")

    print(f"Moved {moved_count} files to {target_dir}")
    
    # Verify
    if target_dir.exists():
        files = list(target_dir.glob("*.onnx"))
        print(f"Final content of {target_dir}:")
        for f in files:
            print(f" - {f.name}")
            
    # Also check if there are other folders like 'buffalo_l' or similar that might have been created
    print("All folders in models:")
    for item in insightface_dir.iterdir():
        if item.is_dir():
            print(f" [DIR] {item.name}")

if __name__ == "__main__":
    fix_model_structure()
