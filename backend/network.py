import pyewf
import pytsk3
import os
from datetime import datetime

# Custom Img_Info class for pytsk3 to read from pyewf
class EWFImgInfo(pytsk3.Img_Info):
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


def list_files_with_timestamps(file_entry, parent_path="/"):
    """List files or directories recursively, with timestamps."""
    if not file_entry.info.meta:
        return

    # Construct the file path
    file_path = os.path.join(parent_path, file_entry.info.name.name.decode())

    # Get file timestamps
    created_time = format_timestamp(file_entry.info.meta.crtime)
    modified_time = format_timestamp(file_entry.info.meta.mtime)
    accessed_time = format_timestamp(file_entry.info.meta.atime)

    # Print the file or directory with timestamps
    if file_entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
        print(f"Directory: {file_path}")
    else:
        print(f"File: {file_path}")
        print(f"  Created: {created_time}")
        print(f"  Modified: {modified_time}")
        print(f"  Accessed: {accessed_time}")
    
    # If directory, list its contents
    if file_entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
        for sub_entry in file_entry.as_directory():
            if sub_entry.info.name.name not in [b".", b".."]:
                list_files_with_timestamps(sub_entry, file_path)


def detect_network_anomalies(packet_data):
    """Detect network anomalies and display source IPs with timestamps."""
    anomaly_count = 0
    total_count = len(packet_data)

    for packet in packet_data:
        src_ip = packet.get("src_ip")
        dest_ip = packet.get("dest_ip")
        src_port = packet.get("src_port")
        dest_port = packet.get("dest_port")
        timestamp = packet.get("timestamp")

        print(f"Source IP: {src_ip}, Destination IP: {dest_ip}")
        print(f"  Source Port: {src_port}, Destination Port: {dest_port}")
        print(f"  Timestamp: {format_timestamp(timestamp)}")

        # Detect anomalies
        if src_ip != dest_ip:
            anomaly_count += 1  # IP mismatch
        elif dest_port not in [80, 443, 22]:
            anomaly_count += 1  # Unusual port scanning behavior
        elif timestamp is None:
            anomaly_count += 1  # Missing timestamp

    # Calculate anomaly percentage
    if total_count > 0:
        anomaly_percentage = (anomaly_count / total_count) * 100
    else:
        anomaly_percentage = 0

    return anomaly_percentage


def load_network_logs_from_image(fs):
    """Extract network-related data (mocked here)."""
    network_data = []

    # Assuming there is a file with network logs (e.g., PCAP or CSV)
    for file_entry in fs.open_dir("/"):
        if file_entry.info.name.name.endswith(b".pcap") or file_entry.info.name.name.endswith(b".log"):
            file_path = os.path.join("/", file_entry.info.name.name.decode())
            print(f"Found network log file: {file_path}")

            # Mocking some packet data here for demonstration
            network_data.append({
                "src_ip": "192.168.1.1",
                "dest_ip": "192.168.1.2",
                "src_port": 12345,
                "dest_port": 80,
                "timestamp": datetime.now().timestamp()
            })
            network_data.append({
                "src_ip": "192.168.1.2",
                "dest_ip": "192.168.1.3",
                "src_port": 12346,
                "dest_port": 443,
                "timestamp": datetime.now().timestamp()
            })
    
    return network_data


def main():
    # Path to the folder containing the split files
    split_files_directory = "/home/pranaash31/techotrace/dfir/diskfile/manjula/"

    # Collect all split files starting with "manjula." and ending with .sXX
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

        # List files and directories recursively from the root directory
        print(f"Listing files from SMART image...")
        root_dir = fs.open_dir("/")
        for entry in root_dir:
            if entry.info.name.name not in [b".", b".."]:
                list_files_with_timestamps(entry)

        print(f"Listing complete.")
        
        # Load network logs from the SMART image
        print("Extracting network log data...")
        network_data = load_network_logs_from_image(fs)

        # Perform network anomaly detection
        anomaly_percentage = detect_network_anomalies(network_data)
        print(f"Anomaly percentage detected in network traffic: {anomaly_percentage:.2f}%")
        
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
