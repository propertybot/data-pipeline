import json
import boto3


def show_custom_labels(model, bucket, photo, min_confidence, region_name):
    client = boto3.client('rekognition', region_name=region_name)

    # Call DetectCustomLabels
    response = client.detect_custom_labels(Image={'S3Object': {'Bucket': bucket, 'Name': photo}},
                                           MinConfidence=min_confidence,
                                           ProjectVersionArn=model)

    # For object detection use case, uncomment below code to display image.
    # display_image(bucket,photo,response)

    return response['CustomLabels']


def mark_image_as_unknown_room(image_id):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('analyzed_images')
    response = table.put_item(
        Item={"id": image_id, "labels": {}}
    )
    return response


def send_image_for_specific_labeling(photo, queue_url, room):
    sqs = boto3.client('sqs')
    sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageBody=(json.dumps({"photo": photo, "room": room}))
    )


def determine_room(bucket, photo):
    bucket = bucket
    photo = photo
    model = 'arn:aws:rekognition:us-east-1:735074111034:project/PropertyBot-v3-room-rekognition/version/PropertyBot-v3-room-rekognition.2021-09-04T22.57.53/1630821474130'
    min_confidence = 80
    labels = show_custom_labels(
        model, bucket, photo, min_confidence, region_name='us-east-1')
    label = next(iter(labels or []), None)
    if label:
        return label['Name']
    else:
        return None


def determine_room_to_label(url):
    photo = url.replace("s3://propertybot-v3/", "")
    bucket = "propertybot-v3"
    room = determine_room(bucket, photo)
    GENERAL_ROOMS = ['Bedroom', 'Living Room', 'Dining Room', 'Living Room']
    EXTERIOR = ['Front Yard', 'Back yard']
    if room == None:
        mark_image_as_unknown_room(photo)
        return
    elif room == 'Kitchen':
        queue_url = 'https://sqs.us-east-1.amazonaws.com/735074111034/kitchen-labeler-queue'
    elif room in GENERAL_ROOMS:
        room = 'general'
        queue_url = 'https://sqs.us-east-1.amazonaws.com/735074111034/general-room-queue'
    elif room == 'Bathroom':
        queue_url = 'https://sqs.us-east-1.amazonaws.com/735074111034/bathroom-labeler-queue'
    elif room in EXTERIOR:
        room = 'exterior'
        queue_url = 'https://sqs.us-east-1.amazonaws.com/735074111034/exterior-labeler-queue'
    else:
        mark_image_as_unknown_room(photo)
        return

    send_image_for_specific_labeling(photo, queue_url, room)


def lambda_handler(event, context):
    for record in event['Records']:
        body = json.loads(record["body"])
        determine_room_to_label(body['url'])
