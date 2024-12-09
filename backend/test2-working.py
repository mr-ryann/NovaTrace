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

    def safe_decode(self, byte_string):
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
        split_files = []
        for i in range(1, 17):
            extension = f'.E{i:02d}'
            matching_files = [
                os.path.join(self.image_directory, f) 
                for f in os.listdir(self.image_directory) 
                if f.endswith(extension)
            ]
            split_files.extend(matching_files)
        return sorted(split_files)

    def verify_registry_paths(self, fs):
        working_paths = {}
        for hive_name, path_variations in self.target_paths.items():
            if hive_name == 'NTUSER':
                continue
            for path in path_variations['base_paths']:
                try:
                    fs.open(path)
                    working_paths[hive_name] = path
                    break
                except:
                    continue
        return working_paths

    def extract_registry_key(self, registry, key_path):
        if self.current_entries >= self.entry_limit:
            return None

        try:
            if key_path.startswith('ROOT\\'):
                key_path = key_path[5:]
            
            try:
                key = registry.open(key_path)
            except Registry.RegistryKeyNotFoundException:
                key = registry.open(key_path.replace('/', '\\'))

            key_data = {
                'path': key_path,
                'last_written': key.timestamp().isoformat(),
                'values': {},
                'subkeys': [],
                'key_name': self.safe_decode(key.name())
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
                except:
                    continue
            
            for subkey in key.subkeys():
                try:
                    key_data['subkeys'].append(self.safe_decode(subkey.name()))
                except:
                    continue

            self.current_entries += 1
            return key_data

        except:
            return None

    def recursive_key_extraction(self, registry, key, prefix='', max_depth=2):
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
                    except:
                        continue
        except:
            pass

    def extract_hive(self, fs, hive_path, hive_name, output_dir):
        try:
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

            if hive_type in self.target_paths:
                for key_path in self.target_paths[hive_type]['key_paths']:
                    try:
                        key = registry.open(key_path)
                        self.recursive_key_extraction(registry, key, key_path)
                    except:
                        continue
            
            for entry in self.output_data:
                if 'hive' not in entry:
                    entry['hive'] = hive_name
                    
        except:
            pass

    def extract_to_csv(self, output_file):
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
        except:
            pass

    def process_image(self):
        try:
            split_files = self.get_split_files()
            if not split_files:
                return

            ewf_handle = pyewf.handle()
            ewf_handle.open(split_files)
            img_info = EWFImgInfo(ewf_handle)
            fs = pytsk3.FS_Info(img_info)

            output_dir = "extracted_registry"
            os.makedirs(output_dir, exist_ok=True)

            working_paths = self.verify_registry_paths(fs)
            
            if working_paths:
                for hive_name, hive_path in working_paths.items():
                    self.extract_hive(fs, hive_path, hive_name, output_dir)

                try:
                    users_dir = fs.open_dir('Users')
                    for user_entry in users_dir:
                        if user_entry.info.name.name not in [b".", b".."]:
                            try:
                                user_name = self.safe_decode(user_entry.info.name.name)
                                ntuser_path = f"Users/{user_name}/NTUSER.DAT"
                                self.extract_hive(fs, ntuser_path, f"NTUSER_{user_name}", output_dir)
                            except:
                                continue
                except:
                    pass

                if self.output_data:
                    self.extract_to_csv(os.path.join(output_dir, 'registry_features.csv'))
                    with open(os.path.join(output_dir, 'registry_full.json'), 'w', encoding='utf-8') as f:
                        json.dump(self.output_data, f, indent=2, ensure_ascii=False)

        finally:
            if 'ewf_handle' in locals():
                ewf_handle.close()

def main():
    image_directory = "E:\.exx files"
    if not os.path.isdir(image_directory):
        print("Error: Invalid directory path")
        return
    
    extractor = RegistryExtractor(image_directory)
    extractor.process_image()
    print("Extraction complete. Check the 'extracted_registry' directory for output files.")

if __name__ == "__main__":
    main()
