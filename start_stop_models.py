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
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/bathroom-labeling/version/bathroom-labeling.2021-12-22T10.29.21/1640197758406'
        version_name = 'bathroom-labeling.2021-12-22T10.29.21'
        start_model(project_arn, model_arn, version_name, min_inference_units)
    elif room == 'kitchen':
        # Start Kitchen Labeling
        project_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/kitchen-labeling/1638974621927'
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/kitchen-labeling/version/kitchen-labeling.2022-01-03T10.07.41/1641233261997'
        version_name = 'kitchen-labeling.2022-01-03T10.07.41'
        start_model(project_arn, model_arn, version_name, min_inference_units)
    elif room == 'exterior':
        # Start Exterior Labeling
        project_arn = 'arn:aws:rekognition:us-east-2:735074111034:project/exterior-labeling/1643260707294'
        model_arn = 'arn:aws:rekognition:us-east-2:735074111034:project/exterior-labeling/version/exterior-labeling.2022-02-03T22.48.55/1643957335334'
        version_name = 'exterior-labeling.2022-02-03T22.48.55'
        start_model(project_arn, model_arn, version_name, min_inference_units)
    else:
        project_arn = 'arn:aws:rekognition:us-east-2:735074111034:project/general-labeling/1644182798393'
        model_arn = 'arn:aws:rekognition:us-east-2:735074111034:project/general-labeling/version/general-labeling.2022-02-08T15.00.43/1644361243238'
        version_name = 'general-labeling.2022-02-08T15.00.43'
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
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/bathroom-labeling/version/bathroom-labeling.2021-12-22T10.29.21/1640197758406'
        stop_model(model_arn)
    elif room == 'kitchen':
        # Start Kitchen Labeling
        model_arn = 'arn:aws:rekognition:us-east-1:735074111034:project/kitchen-labeling/version/kitchen-labeling.2022-01-03T10.07.41/1641233261997'
        stop_model(model_arn)
    elif room == 'exterior':
        model_arn = 'arn: aws: rekognition: us-east-2: 735074111034: project/exterior-labeling/version/exterior-labeling.2022-02-03T22.48.55/1643957335334'
        stop_model(model_arn)
    else:
        model_arn = 'arn:aws:rekognition:us-east-2:735074111034:project/general-labeling/version/general-labeling.2022-02-08T15.00.43/1644361243238'
        stop_model(model_arn)


def lambda_handler(event, context):
    for record in event['Records']:
        payload = json.loads(record["body"])
        if payload['type'] == 'start':
            main_start_model(payload['room'])
        else:
            main_stop_model(payload['room'])
