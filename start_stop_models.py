import json
import boto3


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
    if room == 'room':
        # Start main model
        project_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/PropertyBot-v3-room-rekognition/1630820983471'
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/PropertyBot-v3-room-rekognition/version/PropertyBot-v3-room-rekognition.2021-09-04T22.57.53/1630821474130'
        version_name = 'PropertyBot-v3-room-rekognition.2021-09-04T22.57.53'
        start_model(project_arn, model_arn, version_name, min_inference_units)
    elif room == 'bathroom':
        # Start Bathroom Labeling
        project_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/bathroom-labeling/1638976937496'
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/bathroom-labeling/version/bathroom-labeling.2022-02-11T14.24.45/1644618286005'
        version_name = 'bathroom-labeling.2022-02-11T14.24.45'
        start_model(project_arn, model_arn, version_name, min_inference_units)
    elif room == 'kitchen':
        # Start Kitchen Labeling
        project_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/kitchen-labeling/1638974621927'
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/kitchen-labeling/version/kitchen-labeling.2022-02-11T14.16.28/1644617789083'
        version_name = 'kitchen-labeling.2022-02-11T14.16.28'
        start_model(project_arn, model_arn, version_name, min_inference_units)
    elif room == 'exterior':
        # Start Exterior Labeling
        project_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/exterior-labeling/1644389231271'
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/exterior-labeling/version/exterior-labeling.2022-02-11T13.57.21/1644616642106'
        version_name = 'exterior-labeling.2022-02-11T13.57.21'
        start_model(project_arn, model_arn, version_name, min_inference_units)
    else:
        project_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/general-labeling-full/1645029203985'
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/general-labeling-full/version/general-labeling-full.2022-02-16T10.57.45/1645037865178'
        version_name = 'general-labeling-full.2022-02-16T10.57.45'
        start_model(project_arn, model_arn, version_name, min_inference_units)


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
    if room == 'room':
        # Start main model
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/PropertyBot-v3-room-rekognition/version/PropertyBot-v3-room-rekognition.2021-09-04T22.57.53/1630821474130'
        stop_model(model_arn)
    elif room == 'bathroom':
        # Start Bathroom Labeling
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/bathroom-labeling/version/bathroom-labeling.2022-02-11T14.24.45/1644618286005'
        stop_model(model_arn)
    elif room == 'kitchen':
        # Start Kitchen Labeling
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/kitchen-labeling/version/kitchen-labeling.2022-02-11T14.16.28/1644617789083'
        stop_model(model_arn)
    elif room == 'exterior':
        model_arn = 'arn: aws: rekognition: us-east-2: 735074111034:project/exterior-labeling/version/exterior-labeling.2022-02-03T22.48.55/1643957335334'
        stop_model(model_arn)
    else:
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/general-labeling-full/version/general-labeling-full.2022-02-16T10.57.45/1645037865178'
        stop_model(model_arn)


def lambda_handler(event, context):
    for record in event['Records']:
        payload = json.loads(record["body"])
        if payload['type'] == 'start':
            main_start_model(payload['room'])
        else:
            main_stop_model(payload['room'])
