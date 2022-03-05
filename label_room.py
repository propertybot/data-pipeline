import json
import boto3
import decimal


def show_custom_labels(model, bucket, photo, min_confidence, region_name):
    client = boto3.client('rekognition', region_name=region_name)

    # Call DetectCustomLabels
    response = client.detect_custom_labels(Image={'S3Object': {'Bucket': bucket, 'Name': photo}},
                                           MinConfidence=min_confidence,
                                           ProjectVersionArn=model)

    # For object detection use case, uncomment below code to display image.
    # display_image(bucket,photo,response)

    return response['CustomLabels']


def save_labels(image_id, labels):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('analyzed_images')
    ddb_data = json.loads(json.dumps(
        {"id": image_id, "labels": labels}), parse_float=decimal.Decimal)

    response = table.put_item(
        Item=ddb_data
    )
    return response


def send_image_for_specific_labeling(photo, queue_url, room):
    sqs = boto3.client('sqs')
    sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageBody=(json.dumps({"photo": photo, "room": room}))
    )


def analyze_image(room, photo):
    bucket = "propertybot-v3"
    region_name = 'us-east-1'
    if room == 'kitchen':
        model = 'arn:aws:rekognition:us-east-1:735074111034:project/kitchen-labeling/version/kitchen-labeling.2022-02-11T14.16.28/1644617789083'
    elif room == 'general':
        model = 'arn:aws:rekognition:us-east-1:735074111034:project/general-labeling-full/version/general-labeling-full.2022-02-16T10.57.45/1645037865178'
    elif room == 'bathroom':
        model = 'arn:aws:rekognition:us-east-1:735074111034:project/bathroom-labels-full/version/bathroom-labels-full.2022-02-23T09.26.05/1645637165819'
    elif room == 'exterior':
        model = 'arn:aws:rekognition:us-east-1:735074111034:project/exterior-labeling/version/exterior-labeling.2022-02-11T13.57.21/1644616642106'
    min_confidence = 20
    labels = show_custom_labels(
        model, bucket, photo, min_confidence, region_name)
    save_labels(photo, labels)


def lambda_handler(event, context):
    for record in event['Records']:
        body = json.loads(record["body"])
        print("ANALYZING")
        print(body)
        analyze_image(body['room'], body['photo'])
        print("DONE")
