import requests
import json
from smart_open import open
import boto3
from tqdm import tqdm
import json
import decimal
import re

CURRENT_YEAR = 2022

# Helper class to convert a DynamoDB item to JSON.

dynamodb = boto3.resource('dynamodb')
properties_table = dynamodb.Table('properties')
BUCKET = "propertybot-v3"
PREFIX = "data/raw/listings/"


s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
sqs = boto3.client('sqs')


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

# Wrapper helper class to do regex matching


def regex_handler(description, regex):
    result = re.findall(regex, description)
    if result:
        return True

# Determine if a given item(roof, hvac) is "younger" than a cut off age


def item_is_new(description, item, year_cut_off):
    is_new = False
    age = False
    new = regex_handler(description, '.*new[a-z0-9\s]{1,}'+item)

    completed_in_pref_format = re.findall(
        '.*' + item + '[a-z\s\(\,\+\&\)]{0,}(20[0-9][0-9]|19[0-9][0-9]|[0-9]{2})', description)

    completed_in_secondary = re.findall(
        '.*' + item + '[a-z\s\(\,\+\&\)]{0,}([0-9]{2})', description)
    completed_in_tertiary_format = re.findall('([0-9]{4})\s'+item, description)

    completed_in_forth = re.findall('([0-9]{2})\s'+item, description)

    years_old = re.findall(
        '.*' + item + '[a-z\s\(\,\+\&\)]{0,}([0-9]|[0-9]{2})[a-z0-9\s\(\,\+\&\)]{0,}(years|yrs|old)', description)
    if new:
        is_new = True
    elif completed_in_pref_format:
        age = int(completed_in_pref_format[0])
        is_new = CURRENT_YEAR - age <= year_cut_off
    elif completed_in_secondary:
        age = int(completed_in_secondary[0])
        is_new = CURRENT_YEAR - age <= year_cut_off
    elif completed_in_tertiary_format:
        age = int(completed_in_tertiary_format[0])
        is_new = CURRENT_YEAR - age <= year_cut_off
    elif completed_in_forth:
        age = int(completed_in_forth[0])
        is_new = CURRENT_YEAR - age <= year_cut_off
    elif years_old:
        age = int(years_old[0][0])
        is_new = age <= year_cut_off
    elif regex_handler(description, '(updated|remodeled|new)[a-z\s\(\,\+\&\)\:\-]{0,}' + item):
        is_new = False
        age = False
    elif regex_handler(description, item+'[a-z\s\(\,\+\&\)]{0,}(updated|remodeled|new)'):
        is_new = False
        age = False
    return {'is_new': is_new, 'age': age}


# Determine if a given item(roof, hvac) is "older" than a cut off age
def item_is_old(description, item, year_cut_off):
    completed_in_pref_format = re.findall(
        '.*' + item + '[a-z\s\(\,\+\&\)]{0,}(20[0-9][0-9]|19[0-9][0-9]|[0-9]{2})', description)
    if completed_in_pref_format:
        return CURRENT_YEAR - int(completed_in_pref_format[0]) > year_cut_off
    completed_in_secondary = re.findall(
        '.*' + item + '[a-z\s\(\,\+\&\)]{0,}([0-9]{2})', description)
    if completed_in_secondary:
        return CURRENT_YEAR - int(completed_in_secondary[0]) > year_cut_off
    completed_in_tertiary_format = re.findall('([0-9]{4})\s'+item, description)
    if completed_in_tertiary_format:
        return CURRENT_YEAR - int(completed_in_tertiary_format[0]) > year_cut_off
    completed_in_forth = re.findall('([0-9]{2})\s'+item, description)
    if completed_in_forth:
        return CURRENT_YEAR - int(completed_in_forth[0]) > year_cut_off
    years_old = re.findall(
        '.*' + item + '[a-z\s\(\,\+\&\)]{0,}([0-9]|[0-9]{2})[a-z0-9\s\(\,\+\&\)]{0,}(years|yrs|old)', description)
    if years_old:
        return int(years_old[0][0]) > year_cut_off
    if regex_handler(description, '(older|previous)[a-z\s\(\,\+\&\)\:\-]{0,}' + item):
        return True
    if regex_handler(description, item+'[a-z\s\(\,\+\&\)]{0,}(older previous)'):
        return True

# Get tag with parsed age for item.


def get_tag_for_item(description, item, max_age, include_base_item):
    if regex_handler(description, item):
        new_score = item_is_new(description, item, max_age)
        label = ''
        if new_score['is_new']:
            label = 'new_' + item.replace(" ", "_")
        elif item_is_old(description, item, max_age):
            label = 'old_'+item.replace(" ", "_")
        elif include_base_item:
            label = item
        return {'label': label,  'age': new_score['age']}

# Get CAP rate or ROI if defined


def get_percentage_description(description, item, high_cutoff, medium_cutoff):
    if regex_handler(description, "([0-9]{1,})\% "+item):
        percent = re.findall("([0-9]{1,})\% "+item, description)
        if percent:
            if float(percent[0]) >= high_cutoff:
                'high_' + item
            elif float(percent[0]) >= medium_cutoff:
                'mid_tier_'+item
            else:
                'low_'+item


# Parse and tag the MLS descriptions with out metadata
def fetch_description_metadata(item):
    description = str(item['properties'][0]['description']).lower()
    items = []
    aged_items = ['forced air', 'central air', 'roof', 'laundry',
                  'furnace', 'air cond', 'a/c', ' ac ', 'plumbing', 'electrical']
    # THEY LAST            15              17       30       10         20          15      15      15         24             50

    max_ages = [6,             6,       10,      4,         7,
                7,      7,      7,         10,           20]

    for i in range(len(aged_items)):
        tag = get_tag_for_item(description, aged_items[i], max_ages[i], True)
        if tag:
            items.append(tag)

    water_heaters = ['water heater', 'water tank', 'h20 tank', 'h20 heater']
    for i in range(len(water_heaters)):
        tag = get_tag_for_item(description, water_heaters[i], 4, True)
        if tag:
            items.append(tag)

    if regex_handler(description, '(remodeled|move-in-ready|move-in ready|move in ready| movein ready)'):
        items.append('turnkey')
    elif regex_handler(description, '(tlc|fixer|needs[\s]work|investment[\s]opportunity|investors|handyman|as\-is|potential|value-add|value add|as is|needs repairs)'):
        items.append('remodel')

    appliances = ['washer', 'dryer', 'stove', 'new appliances']
    for i in range(len(appliances)):
        match = regex_handler(description, appliances[i])
        if match:
            items.append(appliances[i].replace(" ", "_") + '_included')

    kitchen_features = ['ceramic tile backsplash', 'maytag', 'whirlpool',
                        'granite counter', 'tile counter', 'slate flooring', 'stainless steel appliances']
    for i in range(len(kitchen_features)):
        match = regex_handler(description, kitchen_features[i])
        if match:
            items.append(kitchen_features[i].replace(" ", "_"))

    bathroom_features = ['tile floor', 'jacuzzi tub', 'tub']
    for i in range(len(bathroom_features)):
        match = regex_handler(description, bathroom_features[i])
        if match:
            items.append(bathroom_features[i].replace(" ", "_"))

    flooring = ['carpet', 'wood floor', 'laminate floor', 'vinyl flooring', ]
    for i in range(len(flooring)):
        match = regex_handler(description, flooring[i])
        if match:
            items.append(flooring[i].replace(" ", "_"))

    walls = ['freshly painted', 'large windows',
             'vinyl windows', 'natural light']
    for i in range(len(walls)):
        match = regex_handler(description, walls[i])
        if match:
            items.append(walls[i].replace(" ", "_"))

    general = ['ocean breeze', 'ocean view', 'ocean-breeze', 'balcony', 'fireplace',
               'basement', 'attic', 'cash flow', 'auction', 'porch', 'recent cosmetic upgrades']
    for i in range(len(general)):
        match = regex_handler(description, general[i])
        if match:
            items.append(general[i].replace(" ", "_"))

    percentage_calculations = ['roi', 'cap']
    for i in range(len(percentage_calculations)):
        tag = get_percentage_description(
            description, percentage_calculations[i], 5.0, 3.0)
        if tag:
            items.append(tag)
    print("NEW ITEMS", items)
    return items


def get_property_details(property_id):
    """
    Gets property details from a listing

    Args:
        property_id: the property id from the listing agreements.

    Returns:
        JSON document with rich property details.

    """
    querystring = {"property_id": property_id}

    headers = {
        'x-rapidapi-key': "4519f6dcffmshfadff8b94661096p1989c5jsn14919517996b",
        'x-rapidapi-host': "realty-in-us.p.rapidapi.com"
    }

    response = requests.request(
        "GET", "https://realty-in-us.p.rapidapi.com/properties/v2/detail", headers=headers, params=querystring)

    return response.json()


# ## Creating Listing Dictionary with Property Listings AND Details

def create_listing_dict(properties):
    listings_dict = {}

    for item in tqdm(properties):
        try:
            # gettign necessary data
            property_id = item['property_id']
            listing = dict(item)
            property_details = dict(
                get_property_details(property_id=property_id))

            # merging two dictionary responses
            listing.update(property_details)

            # adding entry into master listing dictionary
            listings_dict[property_id] = listing
        except:
            print("ERROR: not able to retrieve last item")
    return listings_dict


# ## Extracting Images from Listing Dictionary, Downloading Images, Saving to S3, and Recording S3 Location in Listing Dictionary for Computer Vision Model to Work off S3 Data

def extract_images_from_listings(listings_dict):
    image_url_dict = {}
    image_public_url_dict = {}
    s3_urls = []
    s3_public_urls = []
    urls = [{}]
    rooms = []

    for key, value in tqdm(listings_dict.items()):

        # extractign simple property
        try:
            property_details = value['properties'][0]
        except:
            print("Not all properties have details")

        try:  # not all listing have pictures, so this try/except block is needed
            photo_data = property_details['photos']

            # creating a list of urls for external images
            for item in photo_data:

                ALLOWED_ROOMS = ['exterior', 'living_room',
                                 'dining_room', 'kitchen', 'bedroom', 'bathroom']
                tags = [tag for tag in item['tags']
                        if tag['label'] in ALLOWED_ROOMS]
                room = None
                if tags:
                    max_prob = max((tag['probability'] for tag in tags) or [])
                    print("MAX PROB")
                    print(max_prob)
                    if max_prob and max_prob > 0.8:
                        room = [tag['label']
                                for tag in tags if tag['probability'] == max_prob][0]
                        print("VALID MAX PROB")
                        print(room)
                urls.append({"url": item['href'], "room": room})

            # downloading images from urls and creating a list of urls in s3 where data are to be stored
            counter = 0
            for url in urls:
                response = requests.get(url['url'], stream=True)
                s3url = "s3://propertybot-v3/data/raw/images/{0}_{1}.png".format(
                    key, counter)
                with open(s3url, 'wb') as fout:
                    fout.write(response.content)
                s3_url = "s3://propertybot-v3/data/raw/images/{0}_{1}.png".format(
                    key, counter)
                s3_urls.append(s3_url)
                s3_public_urls.append(
                    "https://propertybot-v3.s3.amazonaws.com/data/raw/images/{0}_{1}.png".format(key, counter))
                send_image_for_specific_labeling(s3_url, room)
                counter = counter + 1
            image_url_dict[key] = s3_urls
            image_public_url_dict[key] = s3_public_urls
            rooms[key] = urls['room']

        except BaseException as err:
            print("No photo data")
            print(err)
            image_url_dict[key] = s3_urls

    for k, v in tqdm(listings_dict.items()):
        listings_dict[k]['s3_image_urls'] = image_url_dict.get(k)
        listings_dict[k]['s3_public_urls'] = image_public_url_dict.get(k)

    return listings_dict, image_url_dict


def send_image_for_specific_labeling(s3_url, room):
    sqs = boto3.client('sqs')
    GENERAL_ROOMS = ['living_room', 'dining_room']
    photo = s3_url.replace("s3://propertybot-v3/", "")
    print("SENDING")
    print(s3_url, room)
    if room == None:
        mark_image_as_unknown_room(photo)
        return
    elif room == 'kitchen':
        queue_url = 'https://sqs.us-east-1.amazonaws.com/735074111034/kitchen-labeler-queue'
    elif room in GENERAL_ROOMS:
        room = 'general'
        queue_url = 'https://sqs.us-east-1.amazonaws.com/735074111034/general-room-queue'
    elif room == 'bathroom':
        queue_url = 'https://sqs.us-east-1.amazonaws.com/735074111034/bathroom-labeler-queue'
    elif room in 'exterior':
        queue_url = 'https://sqs.us-east-1.amazonaws.com/735074111034/exterior-labeler-queue'
    else:
        mark_image_as_unknown_room(photo)
        return
    sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageBody=(json.dumps({"photo": photo, "room": room}))
    )


def mark_image_as_unknown_room(image_id):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('analyzed_images')
    response = table.put_item(
        Item={"id": image_id, "labels": {}}
    )
    return response


def attach_metadata(listings_dict):
    for k, v in listings_dict.items():
        listings_dict[k]['description_metadata'] = fetch_description_metadata(
            v)

    return listings_dict


def send_property_for_labeling_aggregation(image_url_dict, listings_dict):
    sqs.send_message(
        QueueUrl='https://sqs.us-east-1.amazonaws.com/735074111034/labeling-aggreagtion-queue',
        DelaySeconds=10,
        MessageBody=(json.dumps(
            {"image_url_dict": image_url_dict, 'listings_dict': listings_dict}))
    )


def handle_property(property):
    # fetched_item = properties_table.get_item(
    #     Key={'property_id': property['property_id']})
    # if 'Item' in fetched_item:
    #     print("Property already in dynamo")
    #     return
    listings_dict = create_listing_dict(properties=[property])

    print("INFO: using NLP to extract metadata from listings...")
    listings_dict = attach_metadata(listings_dict)
    print("Done...")

    print("INFO: extracting images from listings...")
    listings_dict, image_url_dict = extract_images_from_listings(
        listings_dict)
    print("Done...")

    print("INFO: sending property for labeling aggregation...")
    send_property_for_labeling_aggregation(image_url_dict, listings_dict)
    print("Done...")


# In[ ]:

def lambda_handler(event, context):
    for record in event['Records']:
        property = json.loads(record["body"])
        try:
            handle_property(property)

        except Exception as inst:
            print("FUCKKKKKK")

            print(inst)
            raise Exception('fucking it up in here')

        print("Property is completed")
    return
