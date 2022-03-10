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


def save_labels(image_id, labels, room):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('analyzed_images')
    ddb_data = json.loads(json.dumps(
        {"id": image_id, "labels": labels, 'room': room}), parse_float=decimal.Decimal)

    response = table.put_item(
        Item=ddb_data
    )
    return response


def analyze_image(room, photo):
    bucket = "propertybot-v3"
    region_name = 'us-east-1'
    min_confidence = 20
    ALLOWED_LABELS = ['modern/remodeled', 'old/dated', 'destroyed/mess']
    if room == 'kitchen':
        model = 'arn:aws:rekognition:us-east-1:735074111034:project/kitchen-labeling/version/kitchen-labeling.2022-02-11T14.16.28/1644617789083'
    elif room == 'general' or room == 'exterior':
        model = 'arn:aws:rekognition:us-east-1:735074111034:project/propertybot-v3-rehab-rekognition/version/propertybot-v3-rehab-rekognition.2021-09-07T12.03.54/1631041434161'
        labels = show_custom_labels(
            model, bucket, photo, min_confidence, region_name)
        filtered_labels = [tag for tag in labels
                           if tag['Name'] in ALLOWED_LABELS]
        save_labels(photo, filtered_labels, room)
        return
    elif room == 'bathroom':
        model = 'arn:aws:rekognition:us-east-1:735074111034:project/bathroom-labels-full/version/bathroom-labels-full.2022-02-23T09.26.05/1645637165819'
    labels = show_custom_labels(
        model, bucket, photo, min_confidence, region_name)
    save_labels(photo, labels, room)


def lambda_handler(event, context):
    for record in event['Records']:
        body = json.loads(record["body"])
        print("ANALYZING")
        print(body)
        analyze_image(body['room'], body['photo'])
        print("DONE")
