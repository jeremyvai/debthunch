import json
import requests
import os
from word2number import w2n
from datetime import datetime
ENDPOINT = os.getenv('ENDPOINT', 'staging.api.inboundprospect.com') # 'api.inboundprospect.com'


def phone_to_words(phone):
    '''
    Convert a phone number to words.
    '''
    p = phone.replace('+1', '').replace('-', '').replace(' ', '')
    # Map digits to words
    number_words = {
        '0': 'zero',
        '1': 'one', 
        '2': 'two',
        '3': 'three',
        '4': 'four',
        '5': 'five',
        '6': 'six',
        '7': 'seven',
        '8': 'eight',
        '9': 'nine'
    }
    
    # Convert each digit to its word representation
    words = [number_words[digit] for digit in p]
    
    # Join with spaces
    return ' '.join(words)

def lambda_handler(event, context):
    path = event.get('rawPath', '')
    if path == '/submit/lead':
        return submit_lead_handler(event)
    elif path == '/lead/lookup':
        return lead_lookup_handler(event)
    if path == '/taalk/dnc':
        return dnc_handler(event, context)
    if path == '/taalk/check/dnc':
        return check_dnc_handler(event, context)
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Not found'})
        }

def check_dnc_handler(event, context):
    try:
        body = json.loads(event['body'])
        phone = body.get('phone', None)
        if not phone:
            return {
                'statusCode': 200,  
                'body': json.dumps({
                    'dnc': False
                })
            }
        first_name = body.get('first_name')
        last_name = body.get('last_name')
        phone = body.get('phone', None)
        person_found = body.get('person_found', False)
        response = requests.get(
            f'https://{ENDPOINT}/lead/blacklisted',  
            params={
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone
            }
        )
        api_response = response.json()

        if api_response.get('blacklisted', False):
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'script': (
                        "Thank you for holding. At the moment, "
                        "I am unable to transfer you, "
                        "but I will send a message to the debt "
                        "consolidation expert to notify them that you called."
                        " Thank you for calling and enjoy your day! Bye."),
                    'black_listed': True
                })
            }
        else:
            the_script = f"Thank you {first_name}! To get started, May I ask how much unsecured debt you have?"
            if person_found:
                the_script = f"Thank you for that {first_name}! And just to confirm, is {phone_to_words(phone)} the best mobile number to reach you with?"
            
            return {
                'statusCode': 200, 
                'body': json.dumps({
                    'script': the_script,
                    'black_listed': False,
                    'dbg_url_used' : f'https://{ENDPOINT}/lead/blacklisted'
                })
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

def clean_up_to_zipcode(zip_code):
    '''
    '''
    if isinstance(zip_code, str):
        zip_code = zip_code.replace('(', '').replace(')', '').replace('-', '')
        number_map = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9'
        }
        for word, digit in number_map.items():
            zip_code = zip_code.replace(word, digit)
        zip_code = zip_code.replace('-', '')
        zip_code = zip_code.replace(' ', '')
        try:
            zip_code = int(zip_code)
            return zip_code
        except Exception as e:
            print("Error converting number to int", zip_code)
            return 0
    else:
        return zip_code
        
def clean_up_money_number(money_number):
    '''
    Convert word numbers like "sixty thousand" to digits
    '''
    if isinstance(money_number, str):
        money_number = money_number.replace('(', '').replace(')', '').replace('-', '')
        # Convert word numbers like "sixty thousand" to digits
        try:
            money_number = w2n.word_to_num(money_number)
            money_number = int(money_number)
            return money_number
        except Exception as e:
            import traceback
            print("Traceback:")
            print(traceback.format_exc())
            print("Error converting number to int", money_number)
            return 0
    else:
        return money_number

def clean_phone_number(phone):
    '''
    If the customer mentions the plus one one the phone, don't add it. 
    Most customer will not say +1. 
    '''
    clean_phone=0
    if isinstance(phone, int):
        clean_phone = str(phone)
    else:
        phone = phone.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
        try:
            clean_phone = int(phone)
        except Exception as e:
            print("Error converting phone number to int", phone)
            print(f"Exception occurred: {str(e)}")
            return phone
    # Add +1 prefix if missing
    if isinstance(clean_phone, str):
        if not clean_phone.startswith('+1'):
            clean_phone = '+1' + clean_phone
    else:
        str_phone = str(clean_phone)
        if not str_phone.startswith('+1'):
            clean_phone = '+1' + str_phone
    return clean_phone

def clean_up_pin(pin):
    '''
    If the customer mentions the plus one one the phone, don't add it. 
    Most customer will not say +1.  And sticky may store the phone number
    with the +1 or without.  So we try both cases. 
    '''
    if isinstance(pin, int):
        return pin
    elif pin is None:
        return None
    else:
        pin = pin.replace('(', '').replace(')', '').replace('-', '').replace(',', '')
        number_map = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9'
        }
        for word, digit in number_map.items():
            pin = pin.replace(word, digit)
        pin = pin.replace('-', '')
        pin = pin.replace(' ', '')
        return pin

def lead_lookup_handler(event):
    try:
        # Parse request body
        params = event.get('queryStringParameters', {}) or {}
        pin = clean_up_pin(params.get('pin', None))
        if not pin:
            return {
                'statusCode': 200,
                'body': json.dumps(
                    {
                        'script': 'No personal key provided'
                    }
                )
            }
        # Extract parameters    
        print("pin", pin)
        print("ENDPOINT", f'https://{ENDPOINT}/lead/lookup')
        response = requests.get(
            f'https://{ENDPOINT}/lead/lookup',
            params={
                'pin': pin
            }
        )
        api_response = response.json()
        data = api_response.get('data', [])
        if len(data) == 0:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'script': '~I did not find a record.  I can still assist you. Do you currently have at least fifteen thousand dollars in debt?',
                    'personFound' : False
                })
            }
        else:
            data = data[0]
            return {
                'statusCode': 200,
                'body': json.dumps(
                    {
                    'first_name': data.get('first_name', ''),
                    'last_name': data.get('last_name', ''),
                    'phone_number': data.get('phone_numbers', [{}])[0].get('number',''),
                    'email_address': data.get('email_addresses', [{}])[0].get('email_address'),
                    'address': data.get('addresses', [{}])[0].get('address'),
                    'script' : "Got it! I found your personal key.That's all I needed. Please hold the line while I get you connected to a debt consolidation expert. I am transferring you now.",
                    'personFound' : True,
                    'dbg_url_used' : f'https://{ENDPOINT}/lead/lookup'
                    }
                )
            }
    except Exception as e:
        import traceback
        print(f"Exception occurred: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def clean_up_date_of_birth(date_of_birth):
    '''
    Convert word numbers like "sixty thousand" to digits
    '''
    if not date_of_birth:
        return ""
    
    try:
        # Try to parse the date to validate format
        datetime.strptime(date_of_birth, '%m/%d/%Y')
        return date_of_birth
    except ValueError:
        return ""

def submit_lead_handler_no_pin(event):
    try:
        body = json.loads(event['body'])

        required_fields = [
            'campaign_id', 
            'pin', 
            'first_name', 
            'last_name', 
            'annual_income', 
            'email', 
            'phone'
        ]
        
        # Check if all required fields are present
        for field in required_fields:
            if field not in body:
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'script': f'Missing required field: {field}'
                    })
                }
        url = f'https://{ENDPOINT}/taalk/submit'
        body['pin'] = clean_up_pin(body['pin'])
        body['annual_income'] = clean_up_money_number(body['annual_income'])
        body['date_of_birth'] = clean_up_date_of_birth(body.get('date_of_birth', ''))
        response = requests.post(
            url,
            json=body
        )
        print(url)
        print( body)

        api_response = response.json()
        return {
            'statusCode': 200,
            'body': json.dumps({
                'transferNumber' : clean_phone_number(api_response.get('buyer', {}).get("transfer_number", "")),
                'buyerName' : api_response.get('buyer', {}).get("name", ""),
                'message' : api_response.get('message', ""),
                'success' : api_response.get('success', False),
                'script': 'Thank you for waiting.  I am transfering you now.',
                'dbg_url_used' : url,
                'dbg_body_used' : body
            })
        }
    except Exception as e:
        import traceback
        print(f"Exception occurred: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }   
    
def submit_lead_handler(event):
    try:
        body = json.loads(event['body'])

        required_fields = [
            'campaign_id', 
            'phone'
        ]
        
        # Check if all required fields are present
        for field in required_fields:
            if field not in body:
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'script': f'Missing required field: {field}'
                    })
                }
        url = f'https://{ENDPOINT}/taalk/submit'
        if 'pin' in body and body['pin']:
            body['pin'] = clean_up_pin(body['pin'])
        if 'annual_income' in body:
            body['annual_income'] = clean_up_money_number(body['annual_income'])
        if 'unsecured_debt' in body:
            body['unsecured_debt'] = clean_up_money_number(body['unsecured_debt'])
        if 'postcode' in body:
            body['postcode'] = clean_up_to_zipcode(body['postcode'])
        if 'date_of_birth' in body:
            body['date_of_birth'] = clean_up_date_of_birth(body.get('date_of_birth', ''))

        default_transfer_number = event.get('queryStringParameters', {}).get('default_transfer_number', '+19498286101')

        print( "url for taalk/submit", url)
        print("body for taalk/submit", body)
        
        response = requests.post(
            url,
            json=body
        )
        api_response = response.json()
        
        print("status code for taalk/submit", response.status_code)

        print("response body for taalk/submit", api_response)
        try: 
            phoneNumber = clean_phone_number(api_response.get('buyer', {}).get("transfer_number", ""))
            if not phoneNumber:
                phoneNumber = default_transfer_number
        except Exception as et: 
            import traceback
            phoneNumber = default_transfer_number
            print(f"Exception occurred: {str(et)}")
            print("Traceback:")
            print(traceback.format_exc())
        return {
            'statusCode': 200,
            'body': json.dumps({
                'transferNumber' : phoneNumber,
                'buyerName' : api_response.get('buyer', {}).get("name", ""),
                'message' : api_response.get('message', ""),
                'success' : api_response.get('success', False),
                'script': 'Thank you for waiting.  I am transfering you now.',
                'dbg_url_used' : url,
                'dbg_body_used' : body
            })
        }
    except Exception as e:
        import traceback
        print(f"Exception occurred: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        return {
            'statusCode': 200,
            'body': json.dumps({'error': str(e)}),  
            'transferNumber' : default_transfer_number,
            'script': 'Thank you for waiting.  I am going to connect with a specialist.  I am transfering you now.'
        }    

def dnc_handler(event, context):
    try:
        # Parse request body
        body = json.loads(event['body'])
        
        # Extract parameters
        first_name = body.get('first_name')
        last_name = body.get('last_name')
        phone = body.get('phone', None)
        person_found = body.get('person_found', False)
        campaign_id = body.get('campaign_id', 4)
        # Validate required fields
        if not first_name or not last_name or not phone:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required fields: first_name, last_name, and phone are required'
                })
            }

        # Capitalize first letter of names
        first_name = first_name.capitalize()
        last_name = last_name.capitalize()
        # Call blacklist API
        response = requests.post(
            f'https://{ENDPOINT}/taalk/dnc',
            json={
                'campaign_id': campaign_id,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone
            }
        )
        
        api_response = response.json()
        
        if api_response.get('success'):
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'script': (
                        "Thank you for holding. At the moment, "
                        "I am unable to transfer you, "
                        "but I will send a message to the debt "
                        "consolidation expert to notify them that you called."
                        " Thank you for calling and enjoy your day! Bye."),
                    'black_listed': True,
                    'dbg_url_used' : f'https://{ENDPOINT}/taalk/dnc'
                })
            }
        else:
            the_script = f"Thank you {first_name}! To get started, May I ask how much unsecured debt you have?"
            if person_found:
                the_script = f"Thank you for that {first_name}! And just to confirm, is {phone_to_words(phone)} the best mobile number to reach you with?"
            
            return {
                'statusCode': 200, 
                'body': json.dumps({
                    'script': the_script,
                    'black_listed': False,
                    'dbg_url_used' : f'https://{ENDPOINT}/taalk/dnc'
                })
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

