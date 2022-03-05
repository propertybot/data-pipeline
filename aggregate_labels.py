import json
import boto3
from tqdm import tqdm
import decimal

sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')
analyzed_images_table = dynamodb.Table('analyzed_images')


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
    response = table.put_item(
        Item={"id": image_id, "labels": labels}
    )
    return response


def send_image_for_specific_labeling(photo, queue_url, room):
    sqs = boto3.client('sqs')
    sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageBody=(json.dumps({"photo": photo, "room": room}))
    )


def get_base_label(label):
    words_to_strip = ['neutral', 'ugly', 'new', 'nice', 'old', 'dark']
    for word in words_to_strip:
        label = label.replace(word, '')
    if 'light-fix' not in label:
        label = label.replace('light', '')
    return label.replace('--', '')


def get_setiment(label, confidence):
    negative_identifers = ['old', 'ugly']
    positive_identifers = ['nice', 'neutral', 'new']
    for identifier in negative_identifers:
        if identifier in label:
            return -1 * confidence

    for identifier in positive_identifers:
        if identifier in label:
            return confidence

    return 0


def exists(hash_key):
    try:
        item = analyzed_images_table.get_item(Key={'id': hash_key})
        item = item['Items']
    except boto3.dynamodb.exceptions.DynamoDBKeyNotFoundError:
        item = None
    return item


def ai_on_images(image_url_dict, listings_dict):

    tagged_image_dict = {}
    counter = 0
    for k, v in tqdm(image_url_dict.items()):
        aggregated_labels = {}
        all_labels = []
        for url in v:
            temp_labels = []
            prefix = url.replace("s3://propertybot-v3/", "")
            print("FETCHING")
            print(prefix)
            fetched_item = exists(prefix)
            if not fetched_item:
                print("Image not already in dynamo")
                print(prefix)
                raise Exception('Image not already in dynamo')
            else:
                print("FETCHED ITEM")
                print(fetched_item)
                print(prefix)

            labels = fetched_item['labels']
            room = next(iter(labels.keys() or []), None)
            if room == None:
                continue
            all_labels.append(labels)
            if room not in aggregated_labels:
                sentiment = {}
            else:
                sentiment = aggregated_labels[room]

            for v in labels[room]:
                strippedName = v['Name'].replace(room, '')
                baseLabel = get_base_label(strippedName)
                if baseLabel.startswith('-'):
                    baseLabel = baseLabel[1:]
                if baseLabel.endswith('-'):
                    baseLabel = baseLabel[:-1]
                if baseLabel not in sentiment:
                    sentiment[baseLabel] = 0
                sentiment[baseLabel] += get_setiment(
                    strippedName, v['Confidence'])

            aggregated_labels[room] = sentiment

            tagged_image_dict[url] = temp_labels
        print(str(counter) + '/' + str(len(image_url_dict.items())))

    for k, v in listings_dict.items():
        big_dict = {}

        for url in listings_dict[k]['s3_image_urls']:
            try:
                big_dict[url] = tagged_image_dict[url]

            except:  # this should never happeng because all of the urls in the tagged_image_dict come from the listing_dict, so there should always be a match
                big_dict[url] = None

        listings_dict[k]['labeled_photos'] = big_dict
        listings_dict[k]['aggregated_labels'] = aggregated_labels
        # listings_dict[k]['all_labels'] = all_labels
    save_finalized_data(listings_dict)

# In[14]:


def save_finalized_data(listings_dict):
    for k, v in listings_dict.items():
        payload = {}
        payload['property_id'] = k
        payload['property_info'] = v
        print("INFO: saving data for property_id: {0}".format(k))

        # had to parse float decimal because files could not be saved to DynamoDB
        ddb_data = json.loads(json.dumps(payload), parse_float=decimal.Decimal)
        put_property(record=ddb_data)
        print("INFO: PUT PROPERTY data for property_id: {0}".format(k))

        send_property_to_server(payload)
        print("INFO: SENT PROPERTY for property_id: {0}".format(k))
    return None


def put_property(record):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('properties')
    response = table.put_item(
        Item=record
    )
    return response


# # Main Function that Does the Ingestion

# In[15]:
def send_property_to_server(property):
    sqs.send_message(
        QueueUrl='https://sqs.us-east-1.amazonaws.com/735074111034/cleaned_properties_test',
        DelaySeconds=10,
        MessageBody=(json.dumps(property))
    )


def lambda_handler(event, context):
    for record in event['Records']:
        body = json.loads(record["body"])
        print("BODY LIKE A BACKROAD")
        print(body)
        ai_on_images(body['image_url_dict'], body['listings_dict'])
