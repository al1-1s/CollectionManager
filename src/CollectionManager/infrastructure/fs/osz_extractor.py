import shutil
import zipfile
from pathlib import Path

from src.CollectionManager.infrastructure.exceptions.fs import FileSystemError

class OszExtractor:
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.output_path.mkdir(parents=True, exist_ok=True)

    def extract(self, input_path: Path):
        if not zipfile.is_zipfile(input_path):
            raise FileSystemError(f"{input_path} is not a valid .osz file.", input_path)
        extracted_folder_name = self.output_path / input_path.stem
        with zipfile.ZipFile(input_path, 'r') as zip_ref:
            zip_ref.extractall(extracted_folder_name)
        
        # Return the path to the extracted folder (assuming it has the same name as the .osz file without extension)
        return extracted_folder_name
        
    
    def cleanup(self):
        # Remove extracted archives recursively so storyboard/video subfolders do not block cleanup.
        if not self.output_path.exists():
            return
        for item in self.output_path.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
