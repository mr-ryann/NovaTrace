import pyewf
import pytsk3
import os
import json
from datetime import datetime
from statistics import mean, stdev
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


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
    """Convert a raw timestamp to human-readable format."""
    if timestamp is None or timestamp == 0:
        return "N/A"  # Handle null or zero timestamps
    try:
        return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except (OSError, ValueError):
        return "Invalid Timestamp"


def analyze_file(file_entry, parent_path="/"):
    """Analyze file and collect metadata."""
    try:
        # Check if meta and name are present
        if not file_entry.info.meta or not file_entry.info.name:
            return {}

        # Decode the file name safely
        file_name = file_entry.info.name.name.decode(errors='ignore')

        # Construct file data with validated size
        file_data = {
            "path": os.path.join(parent_path, file_name),
            "size": max(file_entry.info.meta.size, 0) if file_entry.info.meta.size else 0,  # Ensure size >= 0
            "created_time": format_timestamp(file_entry.info.meta.crtime),
            "modified_time": format_timestamp(file_entry.info.meta.mtime),
            "accessed_time": format_timestamp(file_entry.info.meta.atime),
            "type": "Directory" if file_entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR else "File"
        }
        return file_data
    except Exception as e:
        logging.error(f"Error analyzing file: {e}")
        return {}


def detect_anomalies(files_metadata, size_threshold=2):
    """Detect anomalies based on size and timestamp patterns."""
    logging.info("Detecting anomalies...")
    sizes = [file["size"] for file in files_metadata if file["type"] == "File" and file["size"] > 0]

    # Handle cases with insufficient data for anomaly detection
    if len(sizes) < 2:  # Need at least 2 data points for mean and stdev
        logging.warning("Insufficient valid file sizes for anomaly detection.")
        return []

    size_mean = mean(sizes)
    size_stdev = stdev(sizes)

    anomalies = []
    for file in files_metadata:
        try:
            # Check for size anomalies
            if file["type"] == "File" and abs(file["size"] - size_mean) > size_threshold * size_stdev:
                file["anomaly_reason"] = f"Unusual file size (mean={size_mean:.2f}, stdev={size_stdev:.2f})"
                anomalies.append(file)

            # Check for suspicious timestamps
            for timestamp_key in ["created_time", "modified_time"]:
                timestamp = file[timestamp_key]
                if timestamp != "N/A" and datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S') > datetime.utcnow():
                    file["anomaly_reason"] = f"Future {timestamp_key} detected"
                    anomalies.append(file)

            # Check for hidden files
            if os.path.basename(file["path"]).startswith("."):
                file["anomaly_reason"] = "anomaly detected"
                anomalies.append(file)

        except ValueError as ve:
            logging.warning(f"Invalid timestamp for file {file['path']}: {ve}")
            file["anomaly_reason"] = "Invalid timestamp format"
            anomalies.append(file)

    logging.info(f"Anomalies detected: {len(anomalies)}")
    return anomalies


def analyze_files(file_entry, parent_path="/", level=0, max_level=1, results=[]):
    """Recursively analyze files up to max_level."""
    try:
        if not file_entry.info.meta or not file_entry.info.meta.size:
            return

        file_data = analyze_file(file_entry, parent_path)
        if file_data:
            results.append(file_data)

        # If within the max_level, analyze subdirectories
        if level < max_level and file_entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
            for sub_entry in file_entry.as_directory():
                if sub_entry.info.name.name not in [b".", b".."]:
                    analyze_files(sub_entry, file_data["path"], level + 1, max_level, results)
    except Exception as e:
        logging.error(f"Error analyzing files: {e}")
    return results


def export_to_json(data, output_file):
    """Export analysis results to JSON."""
    try:
        with open(output_file, "w") as f:
            json.dump(data, f, indent=4)
        logging.info(f"Analysis results exported to {output_file}")
    except Exception as e:
        logging.error(f"Error exporting data to JSON: {e}")


# Define the folder containing the split files
split_files_directory = "/media/pranaash31/USB DISK/manjula/"

try:
    # Collect all split files
    split_files = sorted(
        [os.path.join(split_files_directory, f) for f in os.listdir(split_files_directory)
         if f.startswith("manjula.") and f.endswith(tuple([f".s{i:02}" for i in range(1, 100)]))],
        key=lambda x: x
    )

    if not split_files:
        logging.error("No SMART files found in the directory.")
        exit()

    logging.info(f"SMART files detected: {split_files}")

    # Open the SMART image using pyewf
    ewf_handle = pyewf.handle()
    ewf_handle.open(split_files)

    # Create a virtual raw image from the SMART files
    img_info = EWFImgInfo(ewf_handle)

    # Open the file system
    fs = pytsk3.FS_Info(img_info)

    # Start analysis
    logging.info(f"Analyzing SMART image...")
    analysis_results = []
    root_dir = fs.open_dir("/")
    for entry in root_dir:
        if entry.info.name.name not in [b".", b".."]:
            analyze_files(entry, level=0, max_level=2, results=analysis_results)

    # Detect anomalies
    anomalies = detect_anomalies(analysis_results)

    # Export results and anomalies
    export_to_json(analysis_results, "analysis_results.json")
    export_to_json(anomalies, "anomalies.json")

    logging.info(f"Analysis complete. Anomalies detected: {len(anomalies)}")
except Exception as e:
    logging.error(f"An error occurred: {e}")
