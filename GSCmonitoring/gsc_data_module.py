from gsc_auth import authenticate_gsc

def get_gsc_data(site_url):
    service = authenticate_gsc()
    
    request = {
        'startDate': '2023-01-01',
        'endDate': '2023-12-31',
        'dimensions': ['query'],
        'rowLimit': 10
    }
    
    response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
    return response.get('rows', [])

if __name__ == '__main__':
    site_url = 'https://example.com'
    data = get_gsc_data(site_url)
    for row in data:
        print(row)