import requests
import boto3
import json

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
cloudwatch = boto3.client('cloudwatch')

properties_table = dynamodb.Table('properties')


def send_property_to_queue(message):
    sqs.send_message(
        QueueUrl='https://sqs.us-east-1.amazonaws.com/735074111034/new-listings',
        DelaySeconds=10,
        MessageBody=(json.dumps(message))
    )


def create_cloudwatch_alarm(alarmName, queueName):
    cloudwatch.put_metric_alarm(
        AlarmName=alarmName,
        AlarmActions=[
            'arn:aws:sns:us-east-1:735074111034:remodel-queues-empty'],
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=1,
        MetricName='ApproximateNumberOfMessagesVisible',
        Namespace='AWS/SQS',
        Dimensions=[
            {
                'Name': 'QueueName',
                'Value': queueName
            },
        ],
        Period=300,
        Unit='Seconds',
        Statistic='Maximum',
        Threshold=0,
        ActionsEnabled=True,
        AlarmDescription='Alarm when the bathroom queue is empty and we need to turn model off'
    )


cloudwatch.delete_alarms(
    AlarmNames=[
        'bathroom-queue-empty',
    ]
)


def start_model(room, alarm_name, queue_name):
    create_cloudwatch_alarm(alarm_name, queue_name)
    sqs.send_message(
        QueueUrl='https://sqs.us-east-1.amazonaws.com/735074111034/rekognition-models',
        DelaySeconds=10,
        MessageBody=(json.dumps({"room": room, "type": "start"}))
    )


def start_all_models():
    start_model('kitchen', 'kitchen-labeler-queue-empty',
                'kitchen-labeler-queue')
    start_model('general', 'general-labeler-queue-empty', 'general-room-queue')
    start_model('bathroom', 'bathrom-queue-empty', 'bathroom-labeler-queue')
    start_model('exterior', 'exterior-labeler-queue-empty',
                'exterior-labeler-queue')


def get_listing(city, state_code, offset):
    url = "https://realty-in-us.p.rapidapi.com/properties/v2/list-for-sale"

    querystring = {"city": city, "state_code": state_code, "offset": offset,
                   "limit": 200, "sort": "newest", "prop_type": "single_family, multi_family"}
    headers = {
        'x-rapidapi-key': "4519f6dcffmshfadff8b94661096p1989c5jsn14919517996b",
        'x-rapidapi-host': "realty-in-us.p.rapidapi.com"
    }

    response = requests.request(
        "GET", url, headers=headers, params=querystring)
    return response.json()


def run_areas():
    areas = [['Los Angeles', 'CA'], ['Cleveland', 'OH'], [
        'Austin', 'TX'], ["Phoenix", "AZ"], ["Charlotte", "NC"]]
    messages = 0
    for area in areas:
        identifier = area[0]
        pull_more_properties = True
        offset = 200
        properties = []
        while pull_more_properties:
            info = get_listing(identifier, area[1], offset)
            properties = properties + info['properties']
            index = len(properties)
            last_property = properties[index - 1]
            fetched_item = properties_table.get_item(
                Key={'property_id': last_property['property_id']})
            if 'Item' in fetched_item:
                pull_more_properties = False
            else:
                pull_more_properties = False
            offset += 200
        for property in properties:
            property['area_identifier'] = identifier
            messages += 1
            send_property_to_queue(property)
    start_all_models()
    return messages


def lambda_handler(event, context):
    messages = run_areas()
    return {
        'statusCode': 200,
        'body': json.dumps('Enqueued ' + str(messages) + ' messages on: ' + queue_url)
    }
