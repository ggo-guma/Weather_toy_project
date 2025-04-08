import boto3
import json

def lambda_handler(event, context):
    try:
        # 디버깅을 위한 입력 데이터 로깅
        print("Step Functions에서 전달받은 데이터:", json.dumps(event, ensure_ascii=False))
        
        # 데이터 구조 처리
        forecast_data = None
        
        # 1. event가 첫 번째 Lambda의 응답 구조를 가지고 있는 경우
        if isinstance(event, dict):
            if 'statusCode' in event and 'body' in event:
                # body가 문자열인 경우 파싱
                if isinstance(event['body'], str):
                    body_data = json.loads(event['body'])
                    if 'data' in body_data and not body_data.get('error', False):
                        forecast_data = body_data['data']
                # body가 딕셔너리인 경우 직접 접근
                elif isinstance(event['body'], dict) and 'data' in event['body']:
                    forecast_data = event['body']['data']
            # 2. event 자체에 forecast_data가 있는 경우
            elif 'forecast_data' in event:
                forecast_data = event['forecast_data']
            # 3. event가 바로 필요한 데이터 구조인 경우
            elif 'daily_forecast' in event and 'hourly_forecast' in event:
                forecast_data = event
        
        # 유효한 forecast_data가 없으면 오류 반환
        if not forecast_data or 'daily_forecast' not in forecast_data or 'hourly_forecast' not in forecast_data:
            print("유효한 날씨 데이터 구조를 찾을 수 없습니다:", json.dumps(event, ensure_ascii=False))
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': True,
                    'message': '유효한 날씨 데이터가 없습니다.'
                }, ensure_ascii=False)
            }
            
        print("처리할 forecast_data:", json.dumps(forecast_data, ensure_ascii=False))
        
        # 비 예측 여부 초기값 False로 설정
        rain_expected = False
        rain_details = []
        
        # 일별 예보에서 비 확인
        print("일별 예보에서 비 확인 시작")
        for daily in forecast_data['daily_forecast']:
            if 'icon' in daily and daily['icon'].startswith('RAIN_'):
                rain_expected = True
                rain_details.append(f"{daily['date_name']} {daily['main_weather']}가 예상됩니다")
                print(f"비 예보 감지: {daily['date_name']}에 {daily['main_weather']}")
        
        # 오늘 시간별 예보에서 비 확인
        print("시간별 예보에서 비 확인 시작")
        for hourly in forecast_data['hourly_forecast']:
            if hourly['rain_type'] != '없음':
                rain_expected = True
                rain_details.append(f"오늘 {hourly['hour']}에 {hourly['rain_type']} 예상")
                print(f"비 예보 감지: 오늘 {hourly['hour']}에 {hourly['rain_type']}")
        
        # 비 예측 시 SNS 메시지 전송
        if rain_expected:
            print("비 예보 감지됨, SNS 메시지 전송")
            sns = boto3.client('sns')
            message = "날씨 알림: 비 예보가 있습니다!\n\n"
            message += "\n".join(rain_details)
            message += "\n우산 챙기세요!"
            
            try:
                response = sns.publish(
                    TopicArn='arn:aws:sns:ap-northeast-2:385264830286:Lambda_send_SMS',
                    Message=message,
                    Subject='금일 비 예보 알림'
                )
                print("SNS 메시지 전송 성공:", response)
                
                return {
                    'status': 'RAIN_ALERT_SENT',
                    'rain_details': rain_details
                }
            except Exception as e:
                print(f"SNS 메시지 전송 중 오류 발생: {e}")
                import traceback
                print(f"상세 오류 정보: {traceback.format_exc()}")
                return {
                    'statusCode': 500, 
                    'body': json.dumps({
                        'error': True,
                        'message': f'SNS 메시지 전송 중 오류 발생: {str(e)}'
                    }, ensure_ascii=False)
                }
        
        # 비 예보 없을 경우
        print("비 예보가 없습니다")
        return {
            'status': 'NO_RAIN',
            'message': '비 예보가 없습니다.'
        }
        
    except Exception as e:
        print(f"Lambda 실행 중 오류 발생: {e}")
        import traceback
        print(f"상세 오류 정보: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': True,
                'message': f'오류 발생: {str(e)}'
            }, ensure_ascii=False)
        }