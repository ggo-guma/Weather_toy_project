import os
import json
import datetime
import urllib.request
from collections import defaultdict

# 환경 변수에서 설정 가져오기
API_KEY = os.environ.get('API_KEY')
API_ENDPOINT = os.environ.get('API_ENDPOINT')
DEFAULT_NX = os.environ.get('DEFAULT_NX', '60')  # 서울 기본값
DEFAULT_NY = os.environ.get('DEFAULT_NY', '127') # 서울 기본값
DATA_TYPE = os.environ.get('DATA_TYPE', 'JSON')

# 상수 정의
FORECAST_HOURS = [2, 5, 8, 11, 14, 17, 20, 23]  # 예보 시간 정의
FORECAST_DAYS = 4  # 오늘부터 글피까지 (총 4일)

# 날씨 코드 상수
SKY_CODES = {
    '1': '맑음',
    '3': '구름많음',
    '4': '흐림'
}

PTY_CODES = {
    '0': '없음',
    '1': '비',
    '2': '비/눈',
    '3': '눈',
    '4': '소나기'
}

def get_current_date():
    """현재 날짜를 YYYYMMDD 형식으로 반환합니다."""
    now = datetime.datetime.now()
    return now.strftime('%Y%m%d')

def get_date_with_offset(days_offset):
    """지정된 일수만큼 이동한 날짜를 YYYYMMDD 형식으로 반환합니다."""
    now = datetime.datetime.now()
    target_date = now + datetime.timedelta(days=days_offset)
    return target_date.strftime('%Y%m%d')

def get_date_name(date_str):
    """날짜 문자열에 대해 오늘/내일/모레/글피 또는 월일 형식으로 반환합니다."""
    today = datetime.datetime.now()
    
    # 날짜 문자열을 datetime 객체로 변환
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y%m%d')
        
        # 날짜 차이 계산
        days_diff = (date_obj - today).days
        
        if days_diff == 0:
            return "오늘"
        elif days_diff == 1:
            return "내일"
        elif days_diff == 2:
            return "모레"
        elif days_diff == 3:
            return "글피"
        return date_obj.strftime('%m월 %d일')
    except ValueError:
        return date_str

def format_hour(hour_str):
    """HHMM 형식의 시간을 HH시 형식으로 변환합니다."""
    try:
        return f"{int(hour_str[:2])}시"
    except ValueError:
        return hour_str

def get_base_time():
    """
    API에 적합한 base_time을 생성합니다.
    예보는 보통 2:00, 5:00, 8:00, 11:00, 14:00, 17:00, 20:00, 23:00에 업데이트됩니다.
    가장 최근의 예보 시간을 반환합니다.
    """
    now = datetime.datetime.now()
    hour = now.hour
    
    # 가장 최근의 예보 시간 찾기
    available_hours = [h for h in FORECAST_HOURS if h <= hour]
    if available_hours:
        base_hour = max(available_hours)
        return now.strftime('%Y%m%d'), f"{base_hour:02}00"
    else:
        # 현재 시간이 가장 이른 예보 시간보다 이전인 경우, 전날의 마지막 예보 사용
        yesterday = now - datetime.timedelta(days=1)
        return yesterday.strftime('%Y%m%d'), '2300'

def try_multiple_base_times():
    """
    여러 기준 시간을 시도하여 데이터를 가져옵니다.
    """
    # 시도할 기준 시간 목록 (최신부터 이전 순으로)
    base_times_to_try = []
    
    # 현재 날짜와 기준 시간 가져오기
    current_date = get_current_date()
    now = datetime.datetime.now()
    
    # 오늘의 시간들
    for hour in reversed(FORECAST_HOURS):
        if hour <= now.hour:
            base_times_to_try.append((current_date, f"{hour:02}00"))
    
    # 어제의 마지막 시간 추가
    yesterday = (now - datetime.timedelta(days=1)).strftime('%Y%m%d')
    base_times_to_try.append((yesterday, "2300"))
    
    print(f"시도할 기준 시간 목록: {base_times_to_try}")
    
    for base_date, base_time in base_times_to_try:
        print(f"{base_date} {base_time} 기준 시간으로 데이터 조회 시도")
        
        params = {
            'url': API_ENDPOINT, 
            'serviceKey': API_KEY, 
            'pageNo': '1', 
            'numOfRows': '1000',
            'dataType': DATA_TYPE, 
            'base_date': base_date, 
            'base_time': base_time, 
            'nx': DEFAULT_NX, 
            'ny': DEFAULT_NY
        }
        
        result = forecast(params)
        if result and not result.get('error'):
            print(f"{base_date} {base_time} 기준 시간으로 데이터 조회 성공")
            return result
        
        print(f"{base_date} {base_time} 기준 시간으로 데이터 조회 실패, 다음 시간 시도")
    
    return {"error": "ALL_ATTEMPTS_FAILED", "message": "모든 기준 시간에 대한 데이터 조회 실패"}

def forecast(params):
    """
    날씨 API를 호출하고 응답을 반환합니다.
    """
    url = params.pop('url')
    
    try:
        encoded_params = '&'.join([f"{k}={v}" for k, v in params.items() if k != 'serviceKey'])
        full_url = f"{url}?serviceKey={params['serviceKey']}&{encoded_params}"
        print(f"요청 URL: {full_url}")
        
        with urllib.request.urlopen(full_url) as response:
            response_text = response.read().decode("utf-8")
            print(f"API 응답 상태 코드: {response.status}")
            
            json_data = json.loads(response_text)
            
            # 응답 헤더 정보 출력
            result_code = json_data['response']['header']['resultCode']
            result_msg = json_data['response']['header']['resultMsg']
            print(f"API 응답 결과 코드: {result_code}")
            print(f"API 응답 결과 메시지: {result_msg}")
            
            if result_code == '00':
                if 'body' in json_data['response'] and 'items' in json_data['response']['body']:
                    items = json_data['response']['body']['items']['item']
                    print(f"응답 데이터 항목 수: {len(items)}")
                    return json_data
                else:
                    print("응답에 데이터 항목이 없습니다.")
                    return {"error": "NO_ITEMS", "message": "응답에 데이터 항목이 없습니다."}
            elif result_code == '03':
                print("데이터가 없습니다. 기준 시간이나 날짜를 조정해 보세요.")
                return {"error": "NO_DATA", "message": "데이터가 없습니다. 다른 기준 시간을 시도해 보세요."}
            else:
                print(f"API 오류: 결과 코드 {result_code}, 메시지: {result_msg}")
                return {"error": result_code, "message": result_msg}
        
    except Exception as e:
        print(f"API 호출 중 오류 발생: {e}")
        import traceback
        print(f"상세 오류 정보: {traceback.format_exc()}")
        return {"error": "EXCEPTION", "message": str(e)}

def group_by_date(items):
    """날짜별로 예보 항목을 그룹화합니다."""
    date_grouped_data = {}
    for item in items:
        fcst_date = item['fcstDate']
        if fcst_date not in date_grouped_data:
            date_grouped_data[fcst_date] = []
        date_grouped_data[fcst_date].append(item)
    return date_grouped_data

def group_by_time(items):
    """시간별로 예보 항목을 그룹화합니다."""
    time_grouped_data = {}
    for item in items:
        fcst_time = item['fcstTime']
        if fcst_time not in time_grouped_data:
            time_grouped_data[fcst_time] = {}
        
        category = item['category']
        value = item['fcstValue']
        time_grouped_data[fcst_time][category] = value
    
    return time_grouped_data

def get_weather_icon(data):
    """날씨 데이터에 기반하여 적절한 아이콘 코드를 반환합니다."""
    pty = data.get('PTY', '0')
    sky = data.get('SKY', '1')
    
    # 강수 유형이 있으면 강수 유형에 따른 아이콘
    if pty != '0':
        return f"RAIN_{pty}"  # 비/눈/소나기 등 강수 유형
    
    # 강수가 없으면 하늘 상태에 따른 아이콘
    return f"SKY_{sky}"  # 맑음/구름많음/흐림

def calculate_hourly_forecast(time_grouped_data):
    """각 시간별 예보 요약 데이터를 계산합니다."""
    hourly_forecast = []
    
    for time_str, data in sorted(time_grouped_data.items()):
        # 필요한 데이터 추출
        hour = format_hour(time_str)
        temp = data.get('T1H', data.get('TMP', 'N/A'))  # 기온
        rain_prob = data.get('POP', '0')  # 강수확률
        rain_type = PTY_CODES.get(data.get('PTY', '0'), '없음')  # 강수유형
        sky_state = SKY_CODES.get(data.get('SKY', '1'), '맑음')  # 하늘상태
        humidity = data.get('REH', 'N/A')  # 습도
        wind_speed = data.get('WSD', 'N/A')  # 풍속
        
        # 아이콘 결정
        icon = get_weather_icon(data)
        
        # 시간별 예보 데이터 구성
        hourly_data = {
            'hour': hour,
            'temperature': f"{temp}°C",
            'rain_probability': f"{rain_prob}%",
            'rain_type': rain_type,
            'sky_state': sky_state,
            'humidity': f"{humidity}%",
            'wind_speed': f"{wind_speed}m/s",
            'icon': icon
        }
        
        hourly_forecast.append(hourly_data)
    
    return hourly_forecast

def calculate_daily_summary(time_grouped_data):
    """일별 요약 데이터를 계산합니다."""
    summary = {
        'min_temp': None, 
        'max_temp': None, 
        'max_pop': 0,
        'pty_count': defaultdict(int),
        'sky_states': defaultdict(int)
    }
    
    for time_data in time_grouped_data.values():
        # 강수확률 처리
        if 'POP' in time_data:
            try:
                pop = int(time_data['POP'])
                if pop > summary['max_pop']:
                    summary['max_pop'] = pop
            except ValueError:
                pass
        
        # 하늘상태 처리
        if 'SKY' in time_data:
            sky = time_data['SKY']
            summary['sky_states'][sky] += 1
        
        # 강수유형 처리
        if 'PTY' in time_data:
            pty = time_data['PTY']
            if pty != '0':  # 비/눈 등 강수가 있는 경우만 카운트
                summary['pty_count'][pty] += 1
        
        # 최저/최고 기온 처리
        if 'TMN' in time_data:
            summary['min_temp'] = time_data['TMN']
        if 'TMX' in time_data:
            summary['max_temp'] = time_data['TMX']
        
        # 기온 정보가 없으면 시간별 기온에서 추출
        if 'TMP' in time_data:
            try:
                temp = float(time_data['TMP'])
                if summary['min_temp'] is None or temp < float(summary['min_temp']):
                    summary['min_temp'] = str(temp)
                if summary['max_temp'] is None or temp > float(summary['max_temp']):
                    summary['max_temp'] = str(temp)
            except (ValueError, TypeError):
                pass
    
    # 대표 날씨 상태 계산
    if summary['pty_count']:
        # 강수 있는 경우, 가장 빈번한 강수유형을 대표로
        most_common_pty = max(summary['pty_count'].items(), key=lambda x: x[1])[0]
        summary['main_weather'] = PTY_CODES.get(most_common_pty, '강수')
        summary['icon'] = f"RAIN_{most_common_pty}"
    elif summary['sky_states']:
        # 강수 없는 경우, 가장 빈번한 하늘상태를 대표로
        most_common_sky = max(summary['sky_states'].items(), key=lambda x: x[1])[0]
        summary['main_weather'] = SKY_CODES.get(most_common_sky, '맑음')
        summary['icon'] = f"SKY_{most_common_sky}"
    else:
        summary['main_weather'] = '데이터 없음'
        summary['icon'] = 'UNKNOWN'
    
    return summary

def process_forecast_data(json_data):
    """
    예보 데이터를 처리하여 날짜별 및 시간별 정보를 구성합니다.
    """
    items = json_data['response']['body']['items']['item']
    
    # 날짜별 그룹화
    date_grouped_data = group_by_date(items)
    
    result = {
        'current_date': get_current_date(),
        'today': None,
        'daily_forecast': [],
        'hourly_forecast': []
    }
    
    # 오늘 날짜
    today = get_current_date()
    
    # 날짜별 처리
    for date_str, date_items in sorted(date_grouped_data.items()):
        time_grouped_data = group_by_time(date_items)
        date_name = get_date_name(date_str)
        
        # 일별 요약 계산
        summary = calculate_daily_summary(time_grouped_data)
        
        # 일별 예보 정보 구성
        daily_data = {
            'date': date_str,
            'date_name': date_name,
            'min_temp': summary['min_temp'],
            'max_temp': summary['max_temp'],
            'main_weather': summary['main_weather'],
            'max_rain_probability': f"{summary['max_pop']}%",
            'icon': summary['icon']
        }
        
        result['daily_forecast'].append(daily_data)
        
        # 오늘 데이터인 경우 시간별 예보도 계산
        if date_str == today:
            result['today'] = daily_data
            result['hourly_forecast'] = calculate_hourly_forecast(time_grouped_data)
    
    return result

def lambda_handler(event, context):
    """
    AWS Lambda 핸들러 함수
    """
    try:
        print("날씨 예보 데이터 수집 시작")
        
        # HTTP 요청 헤더에 대한 CORS 처리
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # 모든 도메인에서 접근 허용. 필요시 변경
            'Access-Control-Allow-Methods': 'GET,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key'
        }
        
        # API Gateway의 OPTIONS 메서드 처리 (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({})
            }
        
        # 여러 시간 시도하여 데이터 가져오기
        api_result = try_multiple_base_times()
        
        if api_result.get('error'):
            return {
                'statusCode': 500, 
                'headers': headers,
                'body': json.dumps({
                    'error': True,
                    'message': f'날씨 데이터를 가져오지 못했습니다: {api_result.get("message")}'
                }, ensure_ascii=False)
            }
        
        # 예보 데이터 처리
        forecast_data = process_forecast_data(api_result)
        
        # Grafana에서 쉽게 시각화할 수 있는 형식으로 데이터 변환
        visualization_data = prepare_visualization_data(forecast_data)
        
        return {
            'statusCode': 200, 
            'headers': headers,
            'body': json.dumps({
                'error': False,
                'data': forecast_data,
                'visualization': visualization_data
            }, ensure_ascii=False)
        }
    except Exception as e:
        print(f"Lambda 실행 중 오류 발생: {e}")
        import traceback
        print(f"상세 오류 정보: {traceback.format_exc()}")
        return {
            'statusCode': 500, 
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': True,
                'message': f'오류 발생: {str(e)}'
            }, ensure_ascii=False)
        }

def prepare_visualization_data(forecast_data):
    """
    Grafana 시각화에 적합한 형식으로 데이터를 변환합니다.
    """
    # 시간별 온도 데이터
    temperature_series = []
    # 시간별 강수확률 데이터
    rain_prob_series = []
    # 시간별 습도 데이터
    humidity_series = []
    
    for hourly in forecast_data.get('hourly_forecast', []):
        # 시간 파싱
        hour = hourly.get('hour', '').replace('시', '')
        try:
            hour_int = int(hour)
            # 온도 파싱
            temp = hourly.get('temperature', '0°C').replace('°C', '')
            temp_float = float(temp)
            # 강수확률 파싱
            rain_prob = hourly.get('rain_probability', '0%').replace('%', '')
            rain_prob_float = float(rain_prob)
            # 습도 파싱
            humidity = hourly.get('humidity', '0%').replace('%', '')
            humidity_float = float(humidity)
            
            # 시리즈 데이터 추가
            temperature_series.append({
                'time': hour_int,
                'value': temp_float,
                'type': 'temperature'
            })
            rain_prob_series.append({
                'time': hour_int,
                'value': rain_prob_float,
                'type': 'rain_probability'
            })
            humidity_series.append({
                'time': hour_int,
                'value': humidity_float,
                'type': 'humidity'
            })
        except (ValueError, TypeError):
            continue
    
    # 일별 온도 범위 데이터
    daily_temp_series = []
    for daily in forecast_data.get('daily_forecast', []):
        try:
            date_name = daily.get('date_name', '')
            min_temp = float(daily.get('min_temp', '0').replace('°C', ''))
            max_temp = float(daily.get('max_temp', '0').replace('°C', ''))
            
            daily_temp_series.append({
                'date': date_name,
                'min_temp': min_temp,
                'max_temp': max_temp,
                'weather': daily.get('main_weather', '')
            })
        except (ValueError, TypeError, AttributeError):
            continue
    
    return {
        'temperature_by_hour': temperature_series,
        'rain_probability_by_hour': rain_prob_series,
        'humidity_by_hour': humidity_series,
        'temperature_by_day': daily_temp_series
    }