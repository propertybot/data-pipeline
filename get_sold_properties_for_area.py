from decimal import Decimal
import requests
import boto3
import json

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

properties_table = dynamodb.Table('properties')
queue_url = 'https://sqs.us-east-1.amazonaws.com/735074111034/sold-properties'


def send_property_to_queue(message):
    sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageBody=(json.dumps(message))
    )


def get_sales(city, state_code, offset):
    url = "https://realty-in-us.p.rapidapi.com/properties/v2/list-sold"

    querystring = {"city": city, "state_code": state_code, "offset": offset,
                   "limit": 2, "sort": "sold_date", "prop_type": "single_family, multi_family"}
    headers = {
        'x-rapidapi-key': "4519f6dcffmshfadff8b94661096p1989c5jsn14919517996b",
        'x-rapidapi-host': "realty-in-us.p.rapidapi.com"
    }

    response = requests.request(
        "GET", url, headers=headers, params=querystring)
    return response.json()


def write_updated_property_to_dynamo(record):
    ddb_data = json.loads(json.dumps(record), parse_float=Decimal)
    properties_table.put_item(
        Item=ddb_data
    )


def run_areas():
    areas = [['Los Angeles', 'CA'], ['Cleveland', 'OH'], [
        'Austin', 'TX'], ["Phoenix", "AZ"], ["Charlotte", "NC"]]

    messages = 0
    for area in areas:
        pull_more_properties = True
        offset = 200
        properties = []
        while pull_more_properties:
            area_identifier = area[0]
            info = get_sales(area[0], area[1], offset)
            properties = properties + info['properties']
            index = len(properties)
            last_property = properties[index - 1]
            fetched_item = properties_table.get_item(
                Key={'property_id': last_property['property_id']})
            if 'Item' in fetched_item:
                property = fetched_item['Item']
                if 'sold_date' in property:
                    pull_more_properties = False
                else:
                    pull_more_properties = True
            else:
                pull_more_properties = False
            offset += 200
        for property in properties:
            property['area_identifier'] = area_identifier
            property['sold_date'] = property['last_update']
            messages += 1
            send_property_to_queue(property)

    return messages


def lambda_handler(event, context):
    print(event)
    messages = run_areas()
    return {
        'statusCode': 200,
        'body': json.dumps('Enqueued ' + str(messages) + ' messages on: ' + queue_url)
    }
