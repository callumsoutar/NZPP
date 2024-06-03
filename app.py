import requests
import re

URL = 'https://www.ifis.airways.co.nz/script/briefing/met_briefing_proc.asp'
LOGIN_URL = 'https://www.ifis.airways.co.nz/secure/script/user_reg/login_proc.asp'
ACCEPTED_CODES = {'NZCH', 'NZCI', 'NZAA', 'NZDN', 'NZGS', 'NZHN', 'NZHK', 'NZNV', 'NZKK', 'NZMS', 'NZMF', 'NZNR', 'NZNS', 'NZNP', 'NZOU', 'NZOH', 'NZPM', 'NZPP', 'NZQN', 'NZRO', 'NZAP', 'NZTG', 'NZMO', 'NZTU', 'NZWF', 'NZWN', 'NZWS', 'NZWK', 'NZWU', 'NZWR', 'NZWP', 'NZWB'}
WEBHOOK_URL = 'https://hooks.zapier.com/hooks/catch/3742777/2y897ym/'

def scrape_metar_info(airport_codes):
    airport_codes = ' '.join([code for code in airport_codes if code in ACCEPTED_CODES])

    username = 'Callum'
    password = '21Everest'
    login_payload = {
        'UserName': username,
        'Password': password,
    }
    data_payload = {
        'METAR': 1,
        'MetLocations': airport_codes,
    }

    with requests.Session() as session:
        session.post(LOGIN_URL, data=login_payload)
        response = session.post(URL, data=data_payload)

    matches = re.finditer(r'(?:METAR |SPECI )(?P<METAR>(?P<CODE>\w{4}).*?)(?:<br/>|<h3>|=</span>|<br />)', response.text)

    metars = {}

    for match in matches:
        info = match.groupdict()
        metars[info['CODE'].upper()] = {'raw_text': info['METAR']}
    
    return metars

def parse_metar(metar):
    data = {}
    parts = metar.split()
    
    # Airport code
    data['airport'] = parts[0]

    # Date and time
    data['date'] = parts[1][:2]
    data['time'] = parts[1][2:6]

    # Wind
    wind = parts[3]
    if 'V' in wind:
        wind_dir, wind_var = wind.split('V')
        data['wind_direction'] = int(wind_dir[:3])
        data['wind_speed'] = int(wind_dir[3:5])
        data['variable_direction'] = int(wind_var[:3])
        data['variable_speed'] = int(wind_var[3:5])
    else:
        data['wind_direction'] = int(wind[:3])
        data['wind_speed'] = int(wind[3:5])

    # Visibility
    visibility_index = next((i for i, part in enumerate(parts) if part.isdigit() and len(part) == 4), None)
    if visibility_index is not None:
        data['visibility'] = int(parts[visibility_index])

    # Cloud data
    clouds = []
    ceiling = None
    for part in parts[5:]:
        if part.startswith(('FEW', 'SCT', 'BKN', 'OVC')):
            clouds.append(part)
            if part.startswith(('BKN', 'OVC')):
                cloud_base = int(part[3:6])
                if ceiling is None or cloud_base < ceiling:
                    ceiling = cloud_base
        elif part in ['NCD', 'SKC', 'SKY CLEAR']:
            clouds.append(part)
    data['clouds'] = clouds if clouds else ['NCD']
    data['ceiling'] = ceiling if ceiling is not None else None  # Set ceiling to None if not available

    # Temperature and dewpoint
    temp_dew = next(part for part in parts if '/' in part and len(part) == 5)
    temp, dew = temp_dew.split('/')
    data['temperature'] = int(temp)
    data['dewpoint'] = int(dew)

    # QNH
    qnh = next(part for part in parts if part.startswith('Q'))
    data['qnh'] = int(qnh[1:])

    return data

def send_to_webhook(data):
    response = requests.post(WEBHOOK_URL, json=data)
    return response.status_code

def render_metar_data(parsed_data):
    print("Parsed METAR data:")
    for key, value in parsed_data.items():
        print(f"{key}: {value}")

# Main function to scrape, parse, and send METAR data
def main(airport_codes):
    metar_results = scrape_metar_info(airport_codes)
    for airport_code, data in metar_results.items():
        parsed_data = parse_metar(data['raw_text'])
        render_metar_data(parsed_data)
        response_status = send_to_webhook(parsed_data)
        print("Webhook response status:", response_status)

# Example usage
airport_codes = ['NZPP']
main(airport_codes)
