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
        self.target_paths = {
            'SYSTEM': [
                r'Windows/System32/config/SYSTEM',
                r'WINDOWS/system32/config/system'
            ],
            'SOFTWARE': [
                r'Windows/System32/config/SOFTWARE',
                r'WINDOWS/system32/config/software'
            ],
            'SAM': [
                r'Windows/System32/config/SAM',
                r'WINDOWS/system32/config/sam'
            ],
            'SECURITY': [
                r'Windows/System32/config/SECURITY',
                r'WINDOWS/system32/config/security'
            ],
            'NTUSER': ['Users/*/NTUSER.DAT']
        }
        self.output_data = []

    def safe_decode(self, byte_string):
        if not isinstance(byte_string, bytes):
            return str(byte_string)
        try:
            return byte_string.decode('utf-8')
        except:
            try:
                return byte_string.decode('utf-16')
            except:
                return byte_string.hex()

    def get_split_files(self):
        split_files = []
        for i in range(1, 17):
            extension = f'.E{i:02d}'
            matching_files = [os.path.join(self.image_directory, f) 
                            for f in os.listdir(self.image_directory) 
                            if f.endswith(extension)]
            split_files.extend(matching_files)
        return sorted(split_files)

    def verify_registry_paths(self, fs):
        working_paths = {}
        for hive_name, paths in self.target_paths.items():
            if hive_name != 'NTUSER':
                for path in paths:
                    try:
                        fs.open(path)
                        working_paths[hive_name] = path
                        break
                    except:
                        continue
        return working_paths

    def extract_registry_key(self, registry, key_path, hive_name):
        try:
            key = registry.open(key_path.replace('/', '\\'))
            key_data = {
                'path': key_path,
                'last_written': key.timestamp().isoformat(),
                'values': {},
                'subkeys': [],
                'hive': hive_name
            }
            
            for value in key.values():
                try:
                    value_name = self.safe_decode(value.name()) if value.name() else "(Default)"
                    value_data = value.value()
                    if isinstance(value_data, bytes):
                        value_data = value_data.hex()
                    key_data['values'][value_name] = {
                        'type': value.value_type_str(),
                        'value': str(value_data)
                    }
                except:
                    continue

            for subkey in key.subkeys():
                try:
                    key_data['subkeys'].append(self.safe_decode(subkey.name()))
                except:
                    continue

            return key_data
        except:
            return None

    def recursive_key_extraction(self, registry, key, prefix, hive_name):
        try:
            key_data = self.extract_registry_key(registry, prefix, hive_name)
            if key_data:
                self.output_data.append(key_data)
                for subkey_name in key_data['subkeys']:
                    try:
                        subkey = registry.open(f"{prefix}\\{subkey_name}")
                        self.recursive_key_extraction(registry, subkey, 
                                                   f"{prefix}/{subkey_name}", 
                                                   hive_name)
                    except:
                        continue
        except:
            pass

    def process_image(self):
        try:
            split_files = self.get_split_files()
            if not split_files:
                print("No E01-E16 files found")
                return

            ewf_handle = pyewf.handle()
            ewf_handle.open(split_files)
            img_info = EWFImgInfo(ewf_handle)
            fs = pytsk3.FS_Info(img_info)
            
            output_dir = "extracted_registry"
            os.makedirs(output_dir, exist_ok=True)

            working_paths = self.verify_registry_paths(fs)
            
            for hive_name, hive_path in working_paths.items():
                try:
                    f = fs.open(hive_path)
                    outfile = os.path.join(output_dir, f"{hive_name}.hive")
                    
                    with open(outfile, 'wb') as out:
                        out.write(f.read_random(0, f.info.meta.size))
                    
                    registry = Registry.Registry(outfile)
                    self.recursive_key_extraction(registry, registry.root(), "", hive_name)
                except:
                    continue

            # Extract NTUSER.DAT files
            try:
                users_dir = fs.open_dir('Users')
                for user_entry in users_dir:
                    if user_entry.info.name.name not in [b".", b".."]:
                        try:
                            user_name = self.safe_decode(user_entry.info.name.name)
                            ntuser_path = f"Users/{user_name}/NTUSER.DAT"
                            f = fs.open(ntuser_path)
                            outfile = os.path.join(output_dir, f"NTUSER_{user_name}.hive")
                            
                            with open(outfile, 'wb') as out:
                                out.write(f.read_random(0, f.info.meta.size))
                            
                            registry = Registry.Registry(outfile)
                            self.recursive_key_extraction(registry, registry.root(), "", f"NTUSER_{user_name}")
                        except:
                            continue
            except:
                pass

            if self.output_data:
                # Save to CSV
                csv_path = os.path.join(output_dir, 'registry_features.csv')
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['hive', 'path', 'last_written', 'value_count', 
                                   'subkey_count', 'has_binary', 'has_executable', 
                                   'path_depth', 'value_types'])
                    for entry in self.output_data:
                        writer.writerow([
                            entry['hive'],
                            entry['path'],
                            entry['last_written'],
                            len(entry['values']),
                            len(entry['subkeys']),
                            any(v['type'] == 'REG_BINARY' for v in entry['values'].values()),
                            any('.exe' in str(v['value']).lower() for v in entry['values'].values()),
                            len(entry['path'].split('/')),
                            ','.join(set(v['type'] for v in entry['values'].values()))
                        ])

                # Save to JSON
                json_path = os.path.join(output_dir, 'registry_full.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(self.output_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            if 'ewf_handle' in locals():
                ewf_handle.close()

def main():
    image_directory = 'E:\.exx files'
    if not os.path.isdir(image_directory):
        print("Error: Invalid directory path")
        return
    
    print("Processing files...")
    extractor = RegistryExtractor(image_directory)
    extractor.process_image()
    print("Complete. Check extracted_registry directory for output files.")

if __name__ == "__main__":
    main()
