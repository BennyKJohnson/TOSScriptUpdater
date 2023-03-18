import xml.etree.ElementTree as ET
import os
import base64
import re
import urllib.request
import sys

def parse_ini_file(filename):
   with open(filename, 'r') as file:
        contents = file.readlines()
        config = {}
        for line in contents:
            line = line.strip()
            if line == '' or line.startswith('#'):
                continue
            else:
                key, value = line.split('=')
                config[key.strip()] = value.strip()
        return config

def get_relative_path(filename):
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    return os.path.join(script_dir, filename)

def download_file(url, save_directory):
    filename = os.path.basename(url)
    urllib.request.urlretrieve(url, os.path.join(save_directory, filename))
    return os.path.join(save_directory, filename)

def encode_as_base64(string):
    bytes_to_encode = string.encode('utf-8')
    encoded_bytes = base64.b64encode(bytes_to_encode)
    return encoded_bytes.decode('utf-8')

def find_cache_files(directory, filename_regex):
    filename_regex = re.compile(filename_regex)
    filepaths = []
    for file in os.listdir(directory):
        if filename_regex.match(file):
            filepath = os.path.join(directory, file)
            filepaths.append(filepath)

    return sorted(filepaths, key=lambda filepath: os.path.getsize(filepath), reverse=True)

def resolve_tos_cache_filepath(installation_directory, regex):
    tos_cache_filenames = find_cache_files(installation_directory, regex)
    print('No ThinkOrSwimCacheFileName specified. Found {} cache files in directory'.format(len(tos_cache_filenames)))
    if len(tos_cache_filenames) == 0:
        print('No cache files found. Are you sure your ThinkOrSwimInstallationDirectory is setup correctly?')
        sys.exit(1)
    for cache_filename in tos_cache_filenames:
        print('Found {} cache file'.format(cache_filename))
    return tos_cache_filenames[0]

def download_scripts(script_config, download_dir):
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    script_files = {}

    for script_name in script_config.keys():
        script_url = script_config[script_name]
        print('Downloading {} at {}...'.format(script_name, script_url))
        script_filename = download_file(script_url, download_dir)
        script_files[script_name] = script_filename

    return script_files

def is_valid_tos_cache(configXML):
    chart_entities_cache = configXML.find("./PROPERTIES_CACHE/CHART_ENTITIES_CACHE")
    entities_element = chart_entities_cache.find("ENTITIES")
    return entities_element is not None

config = parse_ini_file('config.ini')
script_config = parse_ini_file('scripts.ini')

tos_cache_filename = None
if config.get('ThinkOrSwimCacheFileName'):
    tos_cache_filename = config.get('ThinkOrSwimCacheFileName')
else:
    tos_cache_filename = resolve_tos_cache_filepath(config['ThinkOrSwimInstallationDirectory'], config['ThinkOrSwimCacheFileNameRegex']) 
print('Using cache file {}'.format(tos_cache_filename))

print('Found {} script entries'.format(len(script_config.keys())))
script_files = download_scripts(script_config, './DownloadedScripts')

config_xml = ET.parse(tos_cache_filename)
if not is_valid_tos_cache(config_xml):
    print('Cache file does not look valid. Unable to continue')
    sys.exit(1)

script_updates = []
for script_name in script_files.keys():
    script_element = config_xml.find(".//*[@NAME='{}']".format(script_name))
    if script_element is None:
        print('Failed to find script with name {}'.format(script_name))
        break
    with open(get_relative_path(script_files[script_name]), 'r') as script_file:
        script_contents = script_file.read()
        encoded_script_contents = encode_as_base64(script_contents)
        if script_element.get('CODE') == encoded_script_contents:
            print('No changes to script {}'.format(script_name))
        else:
            script_element.set('CODE', encoded_script_contents)
            script_updates.append(script_name)
            print('Updated contents of script {}', script_name)
        

if len(script_updates) > 0:
    config_xml.write(tos_cache_filename)
    print('Successfully updated {}'.format(tos_cache_filename))
else:
    print('No updates made to {}'.format(tos_cache_filename))
