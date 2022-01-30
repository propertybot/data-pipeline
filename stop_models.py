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
    stop_model('kitchen')
    stop_model('general')
    stop_model('room')
    stop_model('bathroom')
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
