import json
import boto3

sqs = boto3.client('sqs')
queue_url = 'https://sqs.us-east-1.amazonaws.com/735074111034/property-for-area-trigger'


def start_model(project_arn, model_arn, version_name, min_inference_units):
    print('Attempting to start: ', version_name)
    client = boto3.client('rekognition')
    # Start the model
    try:
        client.start_project_version(
            ProjectVersionArn=model_arn, MinInferenceUnits=min_inference_units)
        # Wait for the model to be in the running state

    except Exception as e:
        print("FAILING BECAUSE", e)

    describe_response = client.describe_project_versions(ProjectArn=project_arn,
                                                         VersionNames=[version_name])
    start_status = describe_response['ProjectVersionDescriptions'][0]['Status']
    if start_status != 'RUNNING':
        print(start_status)
        raise Exception('NOT STARTED')
    print('Succesfull start: ', version_name)


def main_start_model(room):
    min_inference_units = 1
    if room == 'bathroom':
        # Start Bathroom Labeling
        project_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/bathroom-labels-full/1644725406862'
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/bathroom-labels-full/version/bathroom-labels-full.2022-02-23T09.26.05/1645637165819'
        version_name = 'bathroom-labels-full.2022-02-23T09.26.05'
        start_model(project_arn, model_arn, version_name, min_inference_units)
    elif room == 'kitchen':
        # Start Kitchen Labeling
        project_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/kitchen-labeling/1638974621927'
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/kitchen-labeling/version/kitchen-labeling.2022-02-11T14.16.28/1644617789083'
        version_name = 'kitchen-labeling.2022-02-11T14.16.28'
        start_model(project_arn, model_arn, version_name, min_inference_units)
    elif room == 'exterior':
        # Start Exterior Labeling
        project_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/propertybot-v3-rehab-rekognition/1631041410077'
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/propertybot-v3-rehab-rekognition/version/propertybot-v3-rehab-rekognition.2021-09-07T12.03.54/1631041434161'
        version_name = 'propertybot-v3-rehab-rekognition.2021-09-07T12.03.54'
        start_model(project_arn, model_arn, version_name, min_inference_units)
    elif room == 'all':
        main_start_model('kitchen')
        main_start_model('general')
        main_start_model('bathroom')
        main_start_model('exterior')
    else:
        project_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/propertybot-v3-rehab-rekognition/1631041410077'
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/propertybot-v3-rehab-rekognition/version/propertybot-v3-rehab-rekognition.2021-09-07T12.03.54/1631041434161'
        version_name = 'propertybot-v3-rehab-rekognition.2021-09-07T12.03.54'
        start_model(project_arn, model_arn, version_name, min_inference_units)


def kick_off_get_properties_for_area(room):
    sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageBody=(json.dumps({"room": room, "type": "stop"}))
    )


def stop_model(model_arn):
    client = boto3.client('rekognition')

    print('Stopping model:' + model_arn)

    # Stop the model
    try:
        response = client.stop_project_version(ProjectVersionArn=model_arn)
        status = response['Status']
        print('Status: ' + status)
    except Exception as e:
        print(e)

    print('Stopped model:' + model_arn)


def main_stop_model(room):
    if room == 'bathroom':
        # STOP Bathroom Labeling
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/bathroom-labels-full/version/bathroom-labels-full.2022-02-23T09.26.05/1645637165819'
        stop_model(model_arn)
    elif room == 'kitchen':
        # STOP Kitchen Labeling
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/kitchen-labeling/version/kitchen-labeling.2022-02-11T14.16.28/1644617789083'
        stop_model(model_arn)
    else:
        # STOP GENERIC LABELS
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/propertybot-v3-rehab-rekognition/version/propertybot-v3-rehab-rekognition.2021-09-07T12.03.54/1631041434161'
        stop_model(model_arn)


def lambda_handler(event, context):
    for record in event['Records']:
        payload = json.loads(record["body"])
        if payload['type'] == 'start':
            main_start_model(payload['room'])
        else:
            main_stop_model(payload['room'])
