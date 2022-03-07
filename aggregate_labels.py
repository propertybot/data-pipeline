import json
import boto3
from tqdm import tqdm
import decimal

sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')
analyzed_images_table = dynamodb.Table('analyzed_images')


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


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
        item = item['Item']
    except:
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
            fetched_item = exists(prefix)
            if not fetched_item:
                print("Image not already in dynamo")
                print(prefix)
                raise Exception('Image not already in dynamo')
            labels = fetched_item['labels']
            room = fetched_item['room']
            if room == None:
                continue
            if room not in aggregated_labels:
                sentiment = {}
            else:
                sentiment = aggregated_labels[room]
            for v in labels:
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
        ddb_data = json.loads(json.dumps(payload), cls=DecimalEncoder)
        print("LOADED")
        put_property(record=ddb_data)
        print("INFO: PUT PROPERTY data for property_id: {0}".format(k))

        send_property_to_server(ddb_data)
        print("INFO: SENT PROPERTY for property_id: {0}".format(k))
    return None


def put_property_to_s3(json_data):
    s3 = boto3.resource('s3')
    s3object = s3.Object('completed_properties', json_data['property_id'])

    s3object.put(
        Body=(bytes(json.dumps(json_data, cls=DecimalEncoder).encode('UTF-8')))
    )


def put_property(record):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('properties')
    response = table.put_item(
        Item=record
    )
    print("PUT IN DYNAMO")
    put_property_to_s3(record)
    print("PUT IN s3")
    return response


# # Main Function that Does the Ingestion

# In[15]:
def send_property_to_server(property):
    sqs.send_message(
        QueueUrl='https://sqs.us-east-1.amazonaws.com/735074111034/cleaned_properties_test',
        DelaySeconds=10,
        MessageBody=(json.dumps(property, cls=DecimalEncoder))
    )


def lambda_handler(event, context):
    for record in event['Records']:
        body = json.loads(record["body"])
        print("BODY LIKE A BACKROAD")
        print(body)
        try:
            ai_on_images(body['image_url_dict'], body['listings_dict'])
        except Exception as inst:
            print("FUCKKKKKK")
            print(inst)
            raise Exception('fucking it up in here')
