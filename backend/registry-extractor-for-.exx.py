import pyewf
import pytsk3
import os
import json
import csv
from datetime import datetime
from Registry import Registry

class EWFImgInfo(pytsk3.Img_Info):
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
        self.registry_paths = {
            'SYSTEM': r'Windows/System32/config/SYSTEM',
            'SOFTWARE': r'Windows/System32/config/SOFTWARE',
            'SAM': r'Windows/System32/config/SAM',
            'SECURITY': r'Windows/System32/config/SECURITY',
            'NTUSER': 'Users/*/NTUSER.DAT'  # Added NTUSER.DAT
        }
        self.output_data = []

    def get_split_files(self):
        """Collect all split files (E01-E16) from the directory."""
        split_files = []
        for i in range(1, 17):  # E01 to E16
            extension = f'.E{i:02d}'  # Creates .E01, .E02, etc.
            matching_files = [os.path.join(self.image_directory, f) 
                            for f in os.listdir(self.image_directory) 
                            if f.endswith(extension)]
            if matching_files:
                split_files.extend(matching_files)
        
        # Sort the files to ensure proper order
        split_files.sort()
        return split_files

    def extract_registry_key(self, registry, key_path):
        try:
            key = registry.open(key_path)
            key_data = {
                'path': key_path,
                'last_written': key.timestamp().isoformat(),
                'values': {},
                'subkeys': []
            }
            
            # Extract values
            for value in key.values():
                try:
                    key_data['values'][value.name()] = {
                        'type': value.value_type_str(),
                        'value': str(value.value())
                    }
                except Exception as ve:
                    key_data['values'][value.name()] = {
                        'type': 'ERROR',
                        'value': f'Error reading value: {str(ve)}'
                    }
            
            # Get subkey names
            for subkey in key.subkeys():
                key_data['subkeys'].append(subkey.name())
            
            return key_data
        except Exception as e:
            return {'error': str(e), 'path': key_path}

    def recursive_key_extraction(self, registry, key, prefix=''):
        try:
            for subkey in key.subkeys():
                current_path = f"{prefix}/{subkey.name()}" if prefix else subkey.name()
                key_data = self.extract_registry_key(registry, current_path)
                self.output_data.append(key_data)
                self.recursive_key_extraction(registry, subkey, current_path)
        except Exception as e:
            print(f"Error processing key {prefix}: {str(e)}")

    def extract_to_csv(self, output_file):
        print(f"Saving data to {output_file}...")
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['hive', 'path', 'last_written', 'value_count', 'subkey_count', 
                           'has_binary', 'has_executable', 'path_depth', 'value_types'])
            
            for entry in self.output_data:
                if 'error' not in entry:
                    path_depth = len(entry['path'].split('/'))
                    has_binary = any(v['type'] == 'REG_BINARY' for v in entry['values'].values())
                    has_executable = any('.exe' in str(v['value']).lower() 
                                      for v in entry['values'].values())
                    value_types = ','.join(set(v['type'] for v in entry['values'].values()))
                    
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

    def process_image(self):
        # Get all split files
        split_files = self.get_split_files()
        if not split_files:
            raise Exception("No E01-E16 files found in the specified directory")

        print(f"Found {len(split_files)} split files: {split_files}")

        try:
            # Open the E01 image and its segments
            ewf_handle = pyewf.handle()
            ewf_handle.open(split_files)
            
            print(f"Successfully opened EWF image with size: {ewf_handle.get_media_size()} bytes")
            
            img_info = EWFImgInfo(ewf_handle)
            fs = pytsk3.FS_Info(img_info)

            # Create output directory
            output_dir = "extracted_registry"
            os.makedirs(output_dir, exist_ok=True)

            # Extract each registry hive
            for hive_name, hive_path in self.registry_paths.items():
                try:
                    if '*' in hive_path:  # Handle NTUSER.DAT files
                        # Search for user directories
                        users_dir = fs.open_dir('Users')
                        for user_entry in users_dir:
                            if user_entry.info.name.name in [b".", b".."]:
                                continue
                            try:
                                user_name = user_entry.info.name.name.decode()
                                ntuser_path = f"Users/{user_name}/NTUSER.DAT"
                                self.extract_hive(fs, ntuser_path, f"NTUSER_{user_name}", output_dir)
                            except Exception as ue:
                                print(f"Error processing NTUSER.DAT for {user_name}: {str(ue)}")
                    else:
                        self.extract_hive(fs, hive_path, hive_name, output_dir)
                                
                except Exception as e:
                    print(f"Error processing {hive_name}: {str(e)}")

            # Save the extracted data
            self.extract_to_csv(os.path.join(output_dir, 'registry_features.csv'))
            
            with open(os.path.join(output_dir, 'registry_full.json'), 'w', encoding='utf-8') as f:
                json.dump(self.output_data, f, indent=2, ensure_ascii=False)

            print(f"Extraction complete. Output saved to {output_dir}/")

        except Exception as e:
            print(f"Error processing image: {str(e)}")
        finally:
            if 'ewf_handle' in locals():
                ewf_handle.close()

    def extract_hive(self, fs, hive_path, hive_name, output_dir):
        """Extract and process a single registry hive."""
        print(f"Processing {hive_name} hive from {hive_path}")
        try:
            f = fs.open(hive_path)
            outfile = os.path.join(output_dir, f"{hive_name}.hive")
            
            # Save the registry hive
            with open(outfile, 'wb') as out:
                out.write(f.read_random(0, f.info.meta.size))
            
            # Parse the registry hive
            registry = Registry.Registry(outfile)
            
            # Add hive name to all entries from this hive
            original_len = len(self.output_data)
            self.recursive_key_extraction(registry, registry.root())
            for entry in self.output_data[original_len:]:
                entry['hive'] = hive_name
                
            print(f"Successfully processed {hive_name}")
            
        except Exception as e:
            print(f"Error extracting {hive_name} from {hive_path}: {str(e)}")

def main():
    # Get the directory path from user input
    image_directory = r"E:\.exx files"
    
    # Validate directory
    if not os.path.isdir(image_directory):
        print("Error: Invalid directory path")
        return
        
    print(f"Processing files from directory: {image_directory}")
    
    try:
        extractor = RegistryExtractor(image_directory)
        extractor.process_image()
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
