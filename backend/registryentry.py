import pyewf
import pytsk3
import os
from datetime import datetime


class EWFImgInfo(pytsk3.Img_Info):
    """Custom Img_Info class for pytsk3 to read from pyewf."""

    def __init__(self, ewf_handle):
        self._ewf_handle = ewf_handle
        super().__init__()

    def read(self, offset, size):
        self._ewf_handle.seek(offset)
        return self._ewf_handle.read(size)

    def get_size(self):
        return self._ewf_handle.get_media_size()


def format_timestamp(timestamp):
    """Convert timestamp to human-readable format."""
    if timestamp is None:
        return "N/A"
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def extract_registry_entries(file_entry, parent_path="/", output_dir="extracted_registry"):
    """Extract registry files and save them locally."""
    if not file_entry.info.meta or not file_entry.info.meta.size:
        return

    # Construct the file path
    file_path = os.path.join(parent_path, file_entry.info.name.name.decode())

    # If directory, process contents recursively
    if file_entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
        for sub_entry in file_entry.as_directory():
            if sub_entry.info.name.name not in [b".", b".."]:
                extract_registry_entries(sub_entry, file_path, output_dir)
    else:
        registry_file_name = file_entry.info.name.name.decode().lower()
        if registry_file_name in ["ntuser.dat", "system", "software", "sam", "security"]:
            print(f"Found registry file: {file_path}")
            save_registry_file(file_entry, file_path, output_dir)


def save_registry_file(file_entry, file_path, output_dir):
    """Save registry file locally."""
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, os.path.basename(file_path.replace("/", "_")))

    try:
        with open(output_file, "wb") as out_file:
            offset = 0
            size = 1024 * 1024  # 1MB chunks
            while offset < file_entry.info.meta.size:
                data = file_entry.read_random(offset, size)
                if not data:
                    break
                out_file.write(data)
                offset += len(data)

        print(f"Saved registry file: {output_file}")
    except Exception as e:
        print(f"Error saving registry file {file_path}: {e}")


# Define the folder containing the split files
split_files_directory = "/home/pranaash31/techotrace/dfir/diskfile/manjula/"

# Collect all split files that start with "manjula." and end with .sXX
split_files = sorted(
    [os.path.join(split_files_directory, f) for f in os.listdir(split_files_directory) if f.startswith("manjula.") and f.endswith(tuple([f".s{i:02}" for i in range(1, 100)]))],
    key=lambda x: x
)

if not split_files:
    print("No SMART files found in the directory.")
    exit()

print(f"SMART files detected: {split_files}")

try:
    # Open the SMART image using pyewf
    ewf_handle = pyewf.handle()
    ewf_handle.open(split_files)

    # Create a virtual raw image from the SMART files
    img_info = EWFImgInfo(ewf_handle)

    # Open the file system
    fs = pytsk3.FS_Info(img_info)

    # Extract registry entries from the root directory
    print(f"Extracting registry entries from SMART image...")
    root_dir = fs.open_dir("/")
    for entry in root_dir:
        if entry.info.name.name not in [b".", b".."]:
            extract_registry_entries(entry)

    print(f"Registry extraction complete. Files saved in 'extracted_registry' directory.")
except Exception as e:
    print(f"An error occurred: {e}")
