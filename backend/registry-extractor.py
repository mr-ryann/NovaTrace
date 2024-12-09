import pyewf
import pytsk3
import os
import json
import csv
import pandas as pd
from datetime import datetime
from Registry import Registry
from collections import Counter

class EWFImgInfo(pytsk3.Img_Info):
    def __init__(self, ewf_handle):
        self._ewf_handle = ewf_handle
        self._chunk_size = 32768  # Default chunk size
        super().__init__()

    def read(self, offset, size):
        """Read from EWF file with chunk-based error handling"""
        try:
            self._ewf_handle.seek(offset)
            data = b""
            remaining = size

            while remaining > 0:
                chunk_size = min(remaining, self._chunk_size)
                try:
                    chunk_data = self._ewf_handle.read(chunk_size)
                    if not chunk_data:
                        break
                    data += chunk_data
                    remaining -= len(chunk_data)
                except OSError as e:
                    print(f"Warning: Read error at offset {offset}: {str(e)}")
                    # Fill missing data with zeros
                    data += b"\x00" * remaining
                    break
                except Exception as e:
                    print(f"Error reading chunk at offset {offset}: {str(e)}")
                    raise

            return data

        except Exception as e:
            print(f"Critical read error at offset {offset}: {str(e)}")
            raise

    def get_size(self):
        try:
            return self._ewf_handle.get_media_size()
        except Exception as e:
            print(f"Error getting media size: {str(e)}")
            raise

class RegistryExtractor:
    def __init__(self, image_directory):
        self.image_directory = image_directory
        self.current_source_path = None  # Track current source path
        self.disk_image_info = {
            'path': image_directory,
            'files': [],
            'total_size': 0,
            'creation_time': None,
            'access_time': None,
            'modification_time': None,
            'file_format': 'EWF',
            'segment_count': 0
        }
        self.target_paths = {
            'SYSTEM': {
                'base_paths': [
                    r'Windows/System32/config/SYSTEM',
                    r'WINDOWS/system32/config/system'
                ],
                'key_paths': [
                    r'ControlSet001\Services',
                    r'ControlSet001\Control\Session Manager\Memory Management',
                    r'ControlSet001\Control\ComputerName',
                    r'ControlSet001\Control\TimeZoneInformation',
                    r'Select'
                ]
            },
            'SOFTWARE': {
                'base_paths': [
                    r'Windows/System32/config/SOFTWARE',
                    r'WINDOWS/system32/config/software'
                ],
                'key_paths': [
                    r'Microsoft\Windows\CurrentVersion\Run',
                    r'Microsoft\Windows\CurrentVersion\RunOnce',
                    r'Microsoft\Windows NT\CurrentVersion',
                    r'Microsoft\Windows\CurrentVersion\Uninstall',
                    r'Microsoft\Windows\CurrentVersion\Internet Settings',
                    r'Policies\Microsoft\Windows\System',
                    r'Microsoft\Windows Defender'
                ]
            },
            'NTUSER': {
                'base_paths': ['Users/*/NTUSER.DAT'],
                'key_paths': [
                    r'Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU',
                    r'Software\Microsoft\Windows\CurrentVersion\Run',
                    r'Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\OpenSavePidlMRU',
                    r'Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs'
                ]
            }
        }
        self.output_data = []
        self.entry_limit = 350
        self.current_entries = 0
        self.key_frequency = Counter()
        self.operation_history = {}

    def collect_image_metadata(self, split_files):
        """Collect metadata about the disk image."""
        try:
            self.disk_image_info['files'] = split_files
            self.disk_image_info['segment_count'] = len(split_files)
            
            total_size = 0
            earliest_creation = None
            latest_access = None
            latest_modification = None
            
            for file_path in split_files:
                try:
                    stat_info = os.stat(file_path)
                    total_size += stat_info.st_size
                    
                    creation_time = datetime.fromtimestamp(stat_info.st_ctime)
                    access_time = datetime.fromtimestamp(stat_info.st_atime)
                    modification_time = datetime.fromtimestamp(stat_info.st_mtime)
                    
                    if earliest_creation is None or creation_time < earliest_creation:
                        earliest_creation = creation_time
                    if latest_access is None or access_time > latest_access:
                        latest_access = access_time
                    if latest_modification is None or modification_time > latest_modification:
                        latest_modification = modification_time
                        
                except Exception as e:
                    print(f"Error collecting metadata for {file_path}: {str(e)}")
                    
            self.disk_image_info['total_size'] = total_size
            self.disk_image_info['creation_time'] = earliest_creation.isoformat() if earliest_creation else None
            self.disk_image_info['access_time'] = latest_access.isoformat() if latest_access else None
            self.disk_image_info['modification_time'] = latest_modification.isoformat() if latest_modification else None
            
            print("Disk Image Information:")
            print(f"Total Size: {total_size / (1024*1024*1024):.2f} GB")
            print(f"Segments: {len(split_files)}")
            print(f"Creation Time: {earliest_creation}")
            print(f"Last Access: {latest_access}")
            print(f"Last Modified: {latest_modification}")
            
        except Exception as e:
            print(f"Error collecting image metadata: {str(e)}")
            
    def save_image_metadata(self, output_dir):
        """Save disk image metadata to a JSON file."""
        try:
            metadata_file = os.path.join(output_dir, 'disk_image_metadata.json')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.disk_image_info, f, indent=2, ensure_ascii=False)
            print(f"Saved disk image metadata to {metadata_file}")
        except Exception as e:
            print(f"Error saving image metadata: {str(e)}")

    def get_split_files(self):
        """Get and verify split image files with better error handling."""
        try:
            # First, find all potential split files
            all_files = os.listdir(self.image_directory)
            split_files = []
            
            # Look for .Exx files
            for i in range(1, 100):  # Increased range for more split files
                extension = f'.E{i:02d}'
                current_files = [
                    os.path.join(self.image_directory, f)
                    for f in all_files
                    if f.endswith(extension)
                ]
                if not current_files and i == 1:
                    print(f"Warning: No files found with extension {extension}")
                    continue
                elif not current_files:
                    break
                
                # Verify each file is readable
                for file_path in current_files:
                    try:
                        with open(file_path, 'rb') as f:
                            f.read(1024)  # Try reading first 1KB
                        split_files.append(file_path)
                        print(f"Added split file: {file_path}")
                    except Exception as e:
                        print(f"Warning: Split file {file_path} exists but is not readable: {str(e)}")
            
            if not split_files:
                print("Error: No valid split files found")
                return []
            
            print(f"Found {len(split_files)} valid split files")
            return sorted(split_files)
            
        except Exception as e:
            print(f"Error enumerating split files: {str(e)}")
            return []

    def verify_registry_paths(self, fs):
        """Verify registry paths exist and are accessible."""
        working_paths = {}
        for hive_name, path_variations in self.target_paths.items():
            if hive_name == 'NTUSER':
                continue
            for path in path_variations['base_paths']:
                try:
                    fs.open(path)
                    working_paths[hive_name] = path
                    print(f"Found valid registry path: {path}")
                    break
                except Exception as e:
                    print(f"Path {path} not accessible: {str(e)}")
                    continue
        return working_paths

    def detect_operation_type(self, key):
        """Detect the type of operation based on key metadata"""
        try:
            last_write_time = key.timestamp()
            current_time = datetime.now()
            time_diff = (current_time - last_write_time).total_seconds()
            
            # Basic heuristics for operation detection
            if time_diff < 3600:  # Within last hour
                return 'RECENT_MODIFICATION'
            elif any(v.value_type() == Registry.RegBin for v in key.values()):
                return 'BINARY_OPERATION'
            elif any('.exe' in str(v.value()).lower() for v in key.values()):
                return 'EXECUTABLE_OPERATION'
            else:
                return 'READ_OPERATION'
        except:
            return 'UNKNOWN_OPERATION'

    def safe_decode(self, byte_string):
        """Safely decode byte strings with multiple encodings."""
        if not isinstance(byte_string, bytes):
            return str(byte_string)
        
        encodings = ['utf-8', 'utf-16', 'ascii', 'iso-8859-1']
        for encoding in encodings:
            try:
                return byte_string.decode(encoding)
            except UnicodeDecodeError:
                continue
        return byte_string.hex()

    def extract_registry_key(self, registry, key_path):
        """Extract data from a registry key with error handling."""
        if self.current_entries >= self.entry_limit:
            return None

        try:
            if key_path.startswith('ROOT\\'):
                key_path = key_path[5:]
            
            try:
                key = registry.open(key_path)
            except Registry.RegistryKeyNotFoundException:
                key = registry.open(key_path.replace('/', '\\'))

            # Update frequency counter
            self.key_frequency[key_path] += 1
            
            # Detect operation
            operation_type = self.detect_operation_type(key)
            
            key_data = {
                'path': key_path,
                'last_written': key.timestamp().isoformat(),
                'values': {},
                'subkeys': [],
                'key_name': self.safe_decode(key.name()),
                'key_depth': len(key_path.split('\\')),
                'operation_type': operation_type,
                'frequency': self.key_frequency[key_path],
                'source_path': self.current_source_path  # Add source path
            }
            
            for value in key.values():
                try:
                    value_name = self.safe_decode(value.name()) if value.name() else "(Default)"
                    value_data = value.value()
                    
                    if value.value_type() == Registry.RegSZ or \
                       value.value_type() == Registry.RegExpandSZ:
                        value_data = self.safe_decode(value_data)
                    elif value.value_type() == Registry.RegBin:
                        value_data = value_data.hex()
                    else:
                        value_data = str(value_data)

                    key_data['values'][value_name] = {
                        'type': value.value_type_str(),
                        'value': value_data
                    }
                except Exception as e:
                    print(f"Error processing value in key {key_path}: {str(e)}")
                    continue
            
            for subkey in key.subkeys():
                try:
                    key_data['subkeys'].append(self.safe_decode(subkey.name()))
                except Exception as e:
                    print(f"Error processing subkey in {key_path}: {str(e)}")
                    continue

            self.current_entries += 1
            return key_data

        except Exception as e:
            print(f"Error extracting registry key {key_path}: {str(e)}")
            return None

    def extract_hive(self, fs, hive_path, hive_name, output_dir):
        """Extract and process a registry hive."""
        try:
            print(f"Processing hive: {hive_path}")
            self.current_source_path = hive_path  # Set the current source path
            f = fs.open(hive_path)
            outfile = os.path.join(output_dir, f"{hive_name}.hive")
            
            with open(outfile, 'wb') as out:
                chunk_size = 1024 * 1024
                total_size = f.info.meta.size
                offset = 0
                while offset < total_size:
                    size = min(chunk_size, total_size - offset)
                    data = f.read_random(offset, size)
                    out.write(data)
                    offset += size
            
            registry = Registry.Registry(outfile)
            root = registry.root()
            
            hive_type = 'NTUSER' if hive_name.startswith('NTUSER') else hive_name
            print(f"Processing hive type: {hive_type}")

            if hive_type in self.target_paths:
                for key_path in self.target_paths[hive_type]['key_paths']:
                    try:
                        key = registry.open(key_path)
                        self.recursive_key_extraction(registry, key, key_path)
                    except Exception as e:
                        print(f"Error processing key path {key_path}: {str(e)}")
                        continue
            
            for entry in self.output_data:
                if 'hive' not in entry:
                    entry['hive'] = hive_name
                    
        except Exception as e:
            print(f"Error processing hive {hive_path}: {str(e)}")

    def recursive_key_extraction(self, registry, key, prefix='', max_depth=2):
        """Recursively extract registry keys with depth limit."""
        if self.current_entries >= self.entry_limit:
            return

        try:
            current_key_data = self.extract_registry_key(registry, prefix if prefix else '\\')
            if current_key_data:
                self.output_data.append(current_key_data)

            if max_depth > 0:
                for subkey in key.subkeys():
                    try:
                        subkey_name = self.safe_decode(subkey.name())
                        new_prefix = f"{prefix}/{subkey_name}" if prefix else subkey_name
                        
                        if any(target in new_prefix for target in 
                              self.target_paths[current_key_data.get('hive', '')].get('key_paths', [])):
                            self.recursive_key_extraction(registry, subkey, new_prefix, max_depth - 1)
                    except Exception as e:
                        print(f"Error in recursive extraction for {new_prefix}: {str(e)}")
                        continue
        except Exception as e:
            print(f"Error in recursive extraction: {str(e)}")

    def clean_data(self, input_file, output_file):
        """Clean and preprocess the registry data for ML."""
        try:
            # Read the raw CSV
            df = pd.read_csv(input_file)
            
            # Data cleaning steps
            cleaned_df = df.copy()
            
            # 1. Handle missing values
            cleaned_df = cleaned_df.fillna({
                'hive': 'UNKNOWN',
                'value_count': 0,
                'subkey_count': 0,
                'has_binary': False,
                'has_executable': False,
                'key_depth': 0,
                'frequency': 1
            })
            
            # 2. Convert boolean columns to integers
            cleaned_df['has_binary'] = cleaned_df['has_binary'].astype(int)
            cleaned_df['has_executable'] = cleaned_df['has_executable'].astype(int)
            
            # 3. Convert timestamps to Unix timestamps for ML
            cleaned_df['last_written'] = pd.to_datetime(cleaned_df['last_written']).astype(int) // 10**9
            
            # 4. Encode categorical variables
            cleaned_df['hive'] = pd.Categorical(cleaned_df['hive']).codes
            cleaned_df['operation_type'] = pd.Categorical(cleaned_df['operation_type']).codes
            
            # 5. Create value_type features
            value_types = set()
            for types in cleaned_df['value_types'].str.split(','):
                if isinstance(types, list):
                    value_types.update(types)
            
            for vtype in value_types:
                if vtype and pd.notna(vtype):
                    cleaned_df[f'has_{vtype.lower()}'] = cleaned_df['value_types'].str.contains(vtype).astype(int)
            
            # 6. Drop original value_types column
            cleaned_df = cleaned_df.drop('value_types', axis=1)
            
            # 7. Handle path column - create feature for path depth
            cleaned_df['path_depth'] = cleaned_df['path'].str.count('\\') + 1
            
            # 8. Remove or encode the path column
            cleaned_df = cleaned_df.drop('path', axis=1)
            
            # 9. Remove any remaining non-numeric columns
            numeric_df = cleaned_df.select_dtypes(include=['int64', 'float64'])
            
            # Save cleaned data
            numeric_df.to_csv(output_file, index=False)
            
        except Exception as e:
            print(f"Error in data cleaning: {str(e)}")

    def extract_to_csv(self, output_dir):
        """Extract registry data to CSV files."""
        os.makedirs(output_dir, exist_ok=True)
        raw_output = os.path.join(output_dir, 'registry_raw.csv')
        cleaned_output = os.path.join(output_dir, 'registry_cleaned.csv')
        
        try:
            # Write raw CSV
            with open(raw_output, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Add image source information as metadata rows
                writer.writerow(['# Image Source Information'])
                writer.writerow(['# Path:', self.disk_image_info['path']])
                writer.writerow(['# Total Size:', f"{self.disk_image_info['total_size'] / (1024*1024*1024):.2f} GB"])
                writer.writerow(['# Segments:', self.disk_image_info['segment_count']])
                writer.writerow(['# Creation Time:', self.disk_image_info['creation_time']])
                writer.writerow(['# Last Modified:', self.disk_image_info['modification_time']])
                writer.writerow([])  # Empty row for separation
                
                # Write the actual data headers
                writer.writerow([
                    'hive', 'path', 'source_path', 'last_written', 'value_count', 
                    'subkey_count', 'has_binary', 'has_executable', 
                    'key_depth', 'value_types', 'operation_type', 'frequency',
                    'image_source'  # Add image source column
                ])
                
                for entry in self.output_data:
                    if 'error' not in entry:
                        has_binary = any(
                            v['type'] == 'REG_BINARY' 
                            for v in entry['values'].values()
                        )
                        has_executable = any(
                            '.exe' in str(v['value']).lower() 
                            for v in entry['values'].values()
                        )
                        value_types = ','.join(set(
                            v['type'] for v in entry['values'].values()
                        ))
                        
                        writer.writerow([
                            entry.get('hive', 'UNKNOWN'),
                            entry['path'],
                            entry.get('source_path', 'UNKNOWN'),
                            entry['last_written'],
                            len(entry['values']),
                            len(entry['subkeys']),
                            has_binary,
                            has_executable,
                            entry['key_depth'],
                            value_types,
                            entry['operation_type'],
                            entry['frequency'],
                            self.image_directory  # Add image source
                        ])
            
            # Clean and process the data
            self.clean_data(raw_output, cleaned_output)
            print(f"Successfully created raw CSV at {raw_output}")
            print(f"Successfully created cleaned CSV at {cleaned_output}")
            
        except Exception as e:
            print(f"Error in CSV extraction: {str(e)}")

    def process_image(self):
        """Process the disk image and extract registry information."""
        ewf_handle = None
        try:
            # Get and verify split files
            split_files = self.get_split_files()
            
            if not split_files:
                print("Error: No valid split files found to process")
                return

            # Collect and save image metadata
            print("Collecting disk image metadata...")
            self.collect_image_metadata(split_files)

            print("Opening EWF handle...")
            ewf_handle = pyewf.handle()
            ewf_handle.open(split_files)
            
            print("Creating image info...")
            img_info = EWFImgInfo(ewf_handle)
            
            print("Opening filesystem...")
            fs = pytsk3.FS_Info(img_info)

            print("Creating output directory...")
            output_dir = "registry-entries"
            os.makedirs(output_dir, exist_ok=True)

            print("Verifying registry paths...")
            working_paths = self.verify_registry_paths(fs)
            
            if working_paths:
                print("Processing registry hives...")
                for hive_name, hive_path in working_paths.items():
                    print(f"Extracting hive: {hive_name}")
                    self.extract_hive(fs, hive_path, hive_name, output_dir)

                try:
                    print("Processing user profiles...")
                    users_dir = fs.open_dir('Users')
                    for user_entry in users_dir:
                        if user_entry.info.name.name not in [b".", b".."]:
                            try:
                                user_name = self.safe_decode(user_entry.info.name.name)
                                ntuser_path = f"Users/{user_name}/NTUSER.DAT"
                                print(f"Processing NTUSER.DAT for user: {user_name}")
                                self.extract_hive(fs, ntuser_path, f"NTUSER_{user_name}", output_dir)
                            except Exception as e:
                                print(f"Error processing user {user_name}: {str(e)}")
                                continue
                except Exception as e:
                    print(f"Error processing users directory: {str(e)}")

                if self.output_data:
                    print("Creating output files...")
                    self.extract_to_csv(output_dir)
                    
                    # Save full JSON data
                    json_path = os.path.join(output_dir, 'registry_full.json')
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(self.output_data, f, indent=2, ensure_ascii=False)
                    print(f"Created full JSON output at {json_path}")

                print("Processing complete!")
            else:
                print("No valid registry paths found to process")

        except Exception as e:
            print(f"Critical error during image processing: {str(e)}")
        finally:
            if ewf_handle:
                print("Closing EWF handle...")
                ewf_handle.close()

def main():
    """Main function to run the registry extractor."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract and analyze registry from EWF disk images')
    parser.add_argument('image_directory', help='Directory containing the .Exx split files')
    parser.add_argument('--output', '-o', default='registry-entries',
                      help='Output directory for extracted data (default: registry-entries)')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.image_directory):
        print(f"Error: Directory not found: {args.image_directory}")
        return
    
    print(f"Processing image files from: {args.image_directory}")
    print(f"Output will be saved to: {args.output}")
    
    extractor = RegistryExtractor('E:\.exx files')
    extractor.process_image()
    print("Extraction process completed. Check the output directory for results.")