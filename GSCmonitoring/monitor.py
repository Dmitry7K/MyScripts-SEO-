import os
import sys
import importlib.util

print("Current Working Directory:", os.getcwd())
print("Files in the directory:", os.listdir(os.getcwd()))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from check_tags import check_nofollow_noindex

# Использование абсолютного пути для импорта gsc_data_module
gsc_data_module_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'gsc_data_module.py')
spec = importlib.util.spec_from_file_location("gsc_data_module", gsc_data_module_path)
gsc_data_module = importlib.util.module_from_spec(spec)
sys.modules["gsc_data_module"] = gsc_data_module
spec.loader.exec_module(gsc_data_module)

get_gsc_data = gsc_data_module.get_gsc_data

def main():
    sites = [
        'https://example1.com',
        'https://example2.com'
    ]

    for site in sites:
        nofollow, noindex = check_nofollow_noindex(site)
        if nofollow or noindex:
            print(f'Warning: {site} has nofollow или noindex tags!')
        
        gsc_data = get_gsc_data(site)
        for row in gsc_data:
            print(f'{site} - {row}')

if __name__ == '__main__':
    main()