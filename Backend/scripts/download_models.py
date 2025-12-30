import os
import urllib.request
import zipfile
import shutil
from pathlib import Path

def download_and_extract_model():
    # Define paths
    home = Path.home()
    insightface_dir = home / ".insightface" / "models"
    model_name = "buffalo_sc"
    model_dir = insightface_dir / model_name
    
    # URL for buffalo_sc (MobileFaceNet)
    url = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_sc.zip"
    zip_path = insightface_dir / f"{model_name}.zip"

    print(f"Checking directories...")
    if not insightface_dir.exists():
        insightface_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created {insightface_dir}")

    if model_dir.exists():
        print(f"Model directory {model_dir} already exists.")
        # Check if files exist
        if (model_dir / "det_500m.onnx").exists() and (model_dir / "w600k_mbf.onnx").exists():
             print("Files seem to be present (checking for det_500m.onnx and w600k_mbf.onnx).")
             # Note: filenames might vary, buffalo_sc usually has det_500m.onnx and w600k_mbf.onnx (or 1k3d68 etc depending on version)
             # Let's just re-download to be sure if requested, or check generically.
             files = list(model_dir.glob("*.onnx"))
             if len(files) >= 2:
                 print(f"Found {len(files)} onnx files: {[f.name for f in files]}")
                 return

    print(f"Downloading {model_name} from {url}...")
    try:
        urllib.request.urlretrieve(url, zip_path)
        print("Download complete.")
    except Exception as e:
        print(f"Download failed: {e}")
        return

    print("Extracting...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(insightface_dir)
        print("Extraction complete.")
        
        # Cleanup
        os.remove(zip_path)
        print("Cleaned up zip file.")
        
        # Verify
        if model_dir.exists():
            files = list(model_dir.glob("*.onnx"))
            print(f"Success! Model files found in {model_dir}:")
            for f in files:
                print(f" - {f.name}")
        else:
            print("Warning: Model directory not found after extraction. Check zip content structure.")
            
    except Exception as e:
        print(f"Extraction failed: {e}")

if __name__ == "__main__":
    download_and_extract_model()
