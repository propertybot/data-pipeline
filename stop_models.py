import json
import boto3


sqs = boto3.client('sqs')
queue_url = 'https://sqs.us-east-1.amazonaws.com/735074111034/rekognition-models'


def stop_model(room):
    sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageBody=(json.dumps({"room": room, "type": "stop"}))
    )


def lambda_handler(event, context):
    alarm = event['Records'][0]['Sns']['Subject']
    if 'kitchen' in alarm:
        stop_model('kitchen')
        alarm_name = 'kitchen-labeler-queue-empty'
    elif 'general' in alarm:
        stop_model('general')
        alarm_name = 'exterior-labeler-queue-empty'
    elif 'exterior' in alarm:
        stop_model('exterior')
        alarm_name = 'general-labeler-queue-empty'
    elif 'bathroom' in alarm:
        stop_model('bathroom')
        alarm_name = 'bathrom-queue-empty'

    cloudwatch = boto3.client('cloudwatch')

    cloudwatch.delete_alarms(
        AlarmNames=[alarm_name]
    )

    return {
        'statusCode': 200,
        'body': json.dumps('Stopped all models!')
    }
