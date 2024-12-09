import pyewf
import pytsk3
import os
import json
import csv
from datetime import datetime
from Registry import Registry
import traceback
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('registry_extractor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

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

class RegistryExtractor:
    def __init__(self, image_directory):
        self.image_directory = image_directory
        # Try different path variations for registry hives
        self.registry_paths = {
            'SYSTEM': [
                r'Windows/System32/config/SYSTEM',
                r'WINDOWS/system32/config/system',
                r'windows/system32/config/system'
            ],
            'SOFTWARE': [
                r'Windows/System32/config/SOFTWARE',
                r'WINDOWS/system32/config/software',
                r'windows/system32/config/software'
            ],
            'SAM': [
                r'Windows/System32/config/SAM',
                r'WINDOWS/system32/config/sam',
                r'windows/system32/config/sam'
            ],
            'SECURITY': [
                r'Windows/System32/config/SECURITY',
                r'WINDOWS/system32/config/security',
                r'windows/system32/config/security'
            ],
            'NTUSER': ['Users/*/NTUSER.DAT', 'Documents and Settings/*/NTUSER.DAT']
        }
        self.output_data = []

    def safe_decode(self, byte_string):
        """Safely decode byte strings, trying multiple encodings."""
        if not isinstance(byte_string, bytes):
            return str(byte_string)
        
        encodings = ['utf-8', 'utf-16', 'ascii', 'iso-8859-1']
        for encoding in encodings:
            try:
                return byte_string.decode(encoding)
            except UnicodeDecodeError:
                continue
        return byte_string.hex()

    def get_split_files(self):
        """Collect all split files (E01-E16) from the directory."""
        logging.info(f"Searching for split files in {self.image_directory}")
        split_files = []
        
        try:
            for i in range(1, 17):
                extension = f'.E{i:02d}'
                matching_files = [
                    os.path.join(self.image_directory, f) 
                    for f in os.listdir(self.image_directory) 
                    if f.endswith(extension)
                ]
                split_files.extend(matching_files)
            
            split_files.sort()
            logging.info(f"Found {len(split_files)} split files")
            for f in split_files:
                logging.debug(f"Found file: {f}")
            
            return split_files
        except Exception as e:
            logging.error(f"Error finding split files: {str(e)}")
            raise

    def verify_registry_paths(self, fs):
        """Verify existence of registry hives and find working paths."""
        logging.info("Verifying registry paths...")
        working_paths = {}
        
        for hive_name, path_variations in self.registry_paths.items():
            if hive_name == 'NTUSER':  # Skip NTUSER verification as it uses wildcards
                continue
                
            for path in path_variations:
                try:
                    f = fs.open(path)
                    working_paths[hive_name] = path
                    logging.info(f"✓ Found {hive_name} at {path}")
                    break
                except Exception as e:
                    logging.debug(f"Could not find {hive_name} at {path}: {str(e)}")
        
        return working_paths

    def verify_hive_integrity(self, hive_path):
        """Verify if the registry hive file is valid and accessible."""
        try:
            with open(hive_path, 'rb') as f:
                # Check registry file signature (regf)
                signature = f.read(4)
                if signature != b'regf':
                    logging.error(f"Invalid registry file signature in {hive_path}")
                    return False
                
                # Check file size
                f.seek(0, 2)  # Seek to end
                size = f.tell()
                if size < 512:  # Registry files should be at least 512 bytes
                    logging.error(f"Registry file too small: {size} bytes")
                    return False
                    
            return True
        except Exception as e:
            logging.error(f"Error verifying hive {hive_path}: {str(e)}")
            return False

    def extract_registry_key(self, registry, key_path):
        """Extract data from a single registry key."""
        logging.debug(f"Extracting key: {key_path}")
        try:
            # Remove 'ROOT\' if present in the path
            if key_path.startswith('ROOT\\'):
                key_path = key_path[5:]
            
            # Try to open the key directly
            try:
                key = registry.open(key_path)
            except Registry.RegistryKeyNotFoundException:
                # If direct path fails, try with different separators
                alt_path = key_path.replace('/', '\\')
                key = registry.open(alt_path)

            key_data = {
                'path': key_path,
                'last_written': key.timestamp().isoformat(),
                'values': {},
                'subkeys': [],
                'key_name': self.safe_decode(key.name())
            }
            
            # Extract values with error handling for each value
            for value in key.values():
                try:
                    value_name = self.safe_decode(value.name()) if value.name() else "(Default)"
                    value_data = value.value()
                    # Handle binary data specially
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
                except Exception as ve:
                    logging.warning(f"Error reading value in {key_path}: {str(ve)}")
                    continue
            
            # Get subkey names
            for subkey in key.subkeys():
                try:
                    subkey_name = self.safe_decode(subkey.name())
                    key_data['subkeys'].append(subkey_name)
                except Exception as se:
                    logging.warning(f"Error processing subkey: {str(se)}")
                    continue
            
            return key_data
        except Registry.RegistryKeyNotFoundException:
            logging.warning(f"Registry key not found: {key_path}")
            return {'error': 'Key not found', 'path': key_path}
        except Exception as e:
            logging.error(f"Error extracting key {key_path}: {str(e)}")
            return {'error': str(e), 'path': key_path}

    def recursive_key_extraction(self, registry, key, prefix=''):
        """Recursively extract all keys and their data."""
        try:
            current_key_data = self.extract_registry_key(registry, prefix if prefix else '\\')
            if 'error' not in current_key_data:
                self.output_data.append(current_key_data)
            
            for subkey in key.subkeys():
                try:
                    subkey_name = self.safe_decode(subkey.name())
                    new_prefix = f"{prefix}/{subkey_name}" if prefix else subkey_name
                    self.recursive_key_extraction(registry, subkey, new_prefix)
                except Exception as se:
                    logging.warning(f"Error in recursive extraction: {str(se)}")
                    continue
        except Exception as e:
            logging.error(f"Error processing keys at {prefix}: {str(e)}")

    def extract_hive(self, fs, hive_path, hive_name, output_dir):
        """Extract and process a single registry hive."""
        logging.info(f"\nProcessing {hive_name} hive from {hive_path}")
        
        try:
            f = fs.open(hive_path)
            outfile = os.path.join(output_dir, f"{hive_name}.hive")
            
            # Extract hive file in chunks
            chunk_size = 1024 * 1024  # 1MB chunks
            total_size = f.info.meta.size
            offset = 0
            
            with open(outfile, 'wb') as out:
                while offset < total_size:
                    size = min(chunk_size, total_size - offset)
                    data = f.read_random(offset, size)
                    out.write(data)
                    offset += size
            
            # Verify hive integrity
            if not self.verify_hive_integrity(outfile):
                logging.error(f"Extracted hive file {outfile} appears to be corrupted")
                return
                
            logging.info(f"Saved hive to {outfile}")
            
            # Parse registry hive
            registry = Registry.Registry(outfile)
            root = registry.root()
            
            # Log hive information
            logging.info(f"Successfully opened registry hive: {hive_name}")
            logging.info(f"Root key name: {self.safe_decode(root.name())}")
            logging.info(f"Last written timestamp: {root.timestamp()}")
            
            # Extract keys
            original_len = len(self.output_data)
            self.recursive_key_extraction(registry, root)
            
            # Mark entries with hive name
            new_entries = len(self.output_data) - original_len
            for entry in self.output_data[original_len:]:
                entry['hive'] = hive_name
            
            logging.info(f"Processed {new_entries} keys from {hive_name}")
            
        except Exception as e:
            logging.error(f"Error extracting {hive_name}: {str(e)}")
            logging.debug(traceback.format_exc())

    def extract_to_csv(self, output_file):
        """Save extracted registry data to CSV format."""
        logging.info(f"Saving data to {output_file}")
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'hive', 'path', 'last_written', 'value_count', 
                    'subkey_count', 'has_binary', 'has_executable', 
                    'path_depth', 'value_types'
                ])
                
                for entry in self.output_data:
                    if 'error' not in entry:
                        path_depth = len(entry['path'].split('/'))
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
                            entry['last_written'],
                            len(entry['values']),
                            len(entry['subkeys']),
                            has_binary,
                            has_executable,
                            path_depth,
                            value_types
                        ])
            
            logging.info(f"Successfully saved CSV file")
        except Exception as e:
            logging.error(f"Error saving CSV: {str(e)}")

    def process_image(self):
        """Main method to process the E01 image and extract registry data."""
        try:
            # Get split files
            split_files = self.get_split_files()
            if not split_files:
                raise Exception("No E01-E16 files found")

            # Open EWF image
            ewf_handle = pyewf.handle()
            ewf_handle.open(split_files)
            logging.info(f"Opened EWF image: {ewf_handle.get_media_size()} bytes")
            
            # Create filesystem object
            img_info = EWFImgInfo(ewf_handle)
            fs = pytsk3.FS_Info(img_info)

            # Create output directory
            output_dir = "extracted_registry"
            os.makedirs(output_dir, exist_ok=True)

            # Verify and get working registry paths
            working_paths = self.verify_registry_paths(fs)
            
            if not working_paths:
                logging.error("No registry hives found in standard locations!")
                return
            
            # Extract regular hives
            for hive_name, hive_path in working_paths.items():
                self.extract_hive(fs, hive_path, hive_name, output_dir)

            # Extract NTUSER.DAT files
            try:
                users_dir = fs.open_dir('Users')
                for user_entry in users_dir:
                    if user_entry.info.name.name in [b".", b".."]:
                        continue
                    try:
                        user_name = self.safe_decode(user_entry.info.name.name)
                        ntuser_path = f"Users/{user_name}/NTUSER.DAT"
                        self.extract_hive(fs, ntuser_path, f"NTUSER_{user_name}", output_dir)
                    except Exception as ue:
                        logging.warning(f"Error processing NTUSER.DAT for {user_name}: {str(ue)}")
            except Exception as e:
                logging.warning(f"Error processing user directories: {str(e)}")

            # Check extracted hives
            logging.info("\nExtracted Registry Hives:")
            for hive_file in os.listdir(output_dir):
                if hive_file.endswith('.hive'):
                    full_path = os.path.join(output_dir, hive_file)
                    size = os.path.getsize(full_path)
                    logging.info(f"Hive file: {hive_file}, Size: {size:,} bytes")

            # Save extracted data
            if self.output_data:
                self.extract_to_csv(os.path.join(output_dir, 'registry_features.csv'))
                
                # Save full JSON data
                json_path = os.path.join(output_dir, 'registry_full.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(self.output_data, f, indent=2, ensure_ascii=False)
                
                logging.info(f"Extraction complete. Files saved to {output_dir}/")
                logging.info(f"Total registry keys extracted: {len(self.output_data)}")
            else:
                logging.warning("No registry data was extracted!")

        except Exception as e:
            logging.error(f"Error processing image: {str(e)}")
            logging.debug(traceback.format_exc())
        finally:
            if 'ewf_handle' in locals():
                ewf_handle.close()

    def print_statistics(self):
        """Print statistics about extracted registry data."""
        if not self.output_data:
            logging.info("No statistics available - no data extracted")
            return

        hive_counts = {}
        value_types = set()
        total_values = 0
        total_subkeys = 0
        executable_refs = 0

        for entry in self.output_data:
            if 'error' not in entry:
                hive = entry.get('hive', 'UNKNOWN')
                hive_counts[hive] = hive_counts.get(hive, 0) + 1
                
                values = entry.get('values', {})
                total_values += len(values)
                value_types.update(v['type'] for v in values.values())
                
                total_subkeys += len(entry.get('subkeys', []))
                
                # Count executable references
                executable_refs += any('.exe' in str(v['value']).lower() 
                                    for v in values.values())

        logging.info("\nRegistry Extraction Statistics:")
        logging.info("-" * 30)
        logging.info(f"Total keys processed: {len(self.output_data)}")
        logging.info(f"Total values found: {total_values}")
        logging.info(f"Total subkeys found: {total_subkeys}")
        logging.info(f"Keys referencing executables: {executable_refs}")
        logging.info("\nKeys per hive:")
        for hive, count in hive_counts.items():
            logging.info(f"  {hive}: {count}")
        logging.info("\nValue types found:")
        for vtype in sorted(value_types):
            logging.info(f"  {vtype}")

def main():
    """Main function to run the registry extractor."""
    print("\nRegistry Extractor for E01 Images")
    print("=" * 35)
    
    try:
        # Get input directory
        image_directory = 'E:\.exx files'
        
        if not os.path.isdir(image_directory):
            print("Error: Invalid directory path")
            return
        
        print(f"\nProcessing files from directory: {image_directory}")
        print("Check registry_extractor.log for detailed progress information.")
        print("\nExtracting registry data (this may take a while)...")
        
        # Create and run extractor
        extractor = RegistryExtractor(image_directory)
        extractor.process_image()
        
        # Print statistics
        extractor.print_statistics()
        
        print("\nExtraction complete!")
        print("Check the 'extracted_registry' directory for output files:")
        print("  - registry_features.csv: Structured data for analysis")
        print("  - registry_full.json: Complete registry data")
        print("  - Individual .hive files for each registry hive")
        
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        logging.critical(f"Fatal error: {str(e)}")
        logging.debug(traceback.format_exc())
        print("\nCheck registry_extractor.log for error details")

if __name__ == "__main__":
    main()