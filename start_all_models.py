import json
import boto3


sqs = boto3.client('sqs')
queue_url = 'https://sqs.us-east-1.amazonaws.com/735074111034/rekognition-models'


def start_model(room):
    sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageBody=(json.dumps({"room": room, "type": "start"}))
    )


def lambda_handler(event, context):
    start_model('kitchen')
    start_model('general')
    start_model('room')
    start_model('bathroom')
    start_model('exterior')
    return {
        'statusCode': 200,
        'body': json.dumps('Started all models')
    }
