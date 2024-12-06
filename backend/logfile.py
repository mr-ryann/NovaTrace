import pyewf
import pytsk3
import os
from datetime import datetime


# Define a custom class for handling EWF images with pytsk3
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


# Utility function to format timestamps
def format_timestamp(timestamp):
    """Convert timestamp to human-readable format."""
    if timestamp is None:
        return "N/A"
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


# Recursive function to extract logs
def extract_logs(file_entry, parent_path="/", output_dir="extracted_logs"):
    """Extract system logs and save them locally."""
    # Skip entries without metadata or size
    if not file_entry.info.meta or not file_entry.info.meta.size:
        return

    # Construct the full file path
    file_path = os.path.join(parent_path, file_entry.info.name.name.decode())

    # Handle directories
    if file_entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
        for sub_entry in file_entry.as_directory():
            if sub_entry.info.name.name not in [b".", b".."]:
                extract_logs(sub_entry, file_path, output_dir)
    else:
        # Handle files with log-related extensions
        log_file_name = file_entry.info.name.name.decode()
        if "log" in log_file_name.lower() or log_file_name.endswith((".evtx", ".log", ".txt")):
            print(f"Found log file: {file_path}")
            save_file_content(file_entry, file_path, output_dir)


# Save file content and metadata locally
def save_file_content(file_entry, file_path, output_dir):
    """Save file content locally with timestamps."""
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, os.path.basename(file_path.replace("/", "_")))

    # Extract timestamps
    created_time = format_timestamp(file_entry.info.meta.crtime)
    modified_time = format_timestamp(file_entry.info.meta.mtime)
    accessed_time = format_timestamp(file_entry.info.meta.atime)

    # Write file content to disk
    with open(output_file, "wb") as out_file:
        offset = 0
        size = 1024 * 1024  # Read in 1MB chunks
        while offset < file_entry.info.meta.size:
            data = file_entry.read_random(offset, size)
            if not data:
                break
            out_file.write(data)
            offset += len(data)

    # Save metadata to a separate file
    metadata_file = f"{output_file}_metadata.txt"
    with open(metadata_file, "w") as meta_file:
        meta_file.write(f"File Path: {file_path}\n")
        meta_file.write(f"Created Time: {created_time}\n")
        meta_file.write(f"Modified Time: {modified_time}\n")
        meta_file.write(f"Accessed Time: {accessed_time}\n")

    print(f"Saved: {output_file} (Metadata: {metadata_file})")


# Main script
if __name__ == "__main__":
    # Define the folder containing the split files
    split_files_directory = "/media/pranaash31/USB DISK/manjula/"

    # Collect all split files matching the naming pattern
    split_files = sorted(
        [os.path.join(split_files_directory, f) for f in os.listdir(split_files_directory)
         if f.startswith("manjula.") and f.endswith(tuple([f".s{i:02}" for i in range(1, 100)]))],
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

        # Extract logs from the file system
        print("Extracting logs from SMART image...")
        root_dir = fs.open_dir("/")
        for entry in root_dir:
            if entry.info.name.name not in [b".", b".."]:
                extract_logs(entry)

        print("Log extraction complete. Logs saved to 'extracted_logs' directory.")
    except Exception as e:
        print(f"An error occurred: {e}")
