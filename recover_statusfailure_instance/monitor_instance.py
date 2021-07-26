import json
import boto3
import time
import datetime
import os
import logging
from trigger_sns import trigger_sns_topic


success_sns_notify_topic_name=os.environ['SNS_SUCCESS_NOTIFY_TOPIC']
recovery_failure_sns_topic_name=os.environ['SNS_EC2_RECOVERY_FAILURE_NOTIFY_TOPIC']
recovery_failure_sns_notify_topic_name=os.environ['SNS_SUCCESS_NOTIFY_TOPIC']
region=os.environ['REGION']
pending_in_minutes=3

def lambda_handler(event, context):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.debug("main.lambda_handler : Incoming event is \n {}".format(event))
    logger.info(event)
    message = event['Records'][0]['Sns']['Message']
    #Converting string message in to json
    json_obj=json.loads(message)
    instance_id = json_obj['Trigger']['Dimensions'][0]['value']
    logger.info("Status Check failed for the instance: {}".format(instance_id))
    client_sns = boto3.client('sns', region_name=region)
    client = boto3.client('ec2')

    time.sleep(2)
    response=client.describe_instances(
        InstanceIds=[instance_id]
        )
    logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state". \
        format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))

    
    #Verifying it whether it is in stopping state or not
    if response['Reservations'][0]['Instances'][0]['State']['Name'] == 'stopping':
        
        
        response=client.describe_instances(
            InstanceIds=[instance_id]
            )
            
        while response['Reservations'][0]['Instances'][0]['State']['Name'] == 'stopping':
            time.sleep(2)
            logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state". \
                format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))
            response=client.describe_instances(
                        InstanceIds=[instance_id]
                )
                
            if response['Reservations'][0]['Instances'][0]['State']['Name'] == 'stopped':
                response=client.describe_instances(
                    InstanceIds=[instance_id]
                    )

                # When instanse goes to stopped state
                while response['Reservations'][0]['Instances'][0]['State']['Name'] == 'stopped':
                    logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state". \
                        format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))
                    time.sleep(1)
                    response=client.describe_instances(
                            InstanceIds=[instance_id]
                        )

                    endTime = datetime.datetime.now() + datetime.timedelta(minutes=pending_in_minutes)        
                    if response['Reservations'][0]['Instances'][0]['State']['Name'] == 'pending':

                        while response['Reservations'][0]['Instances'][0]['State']['Name'] == 'pending':
                            time.sleep(2)
                            logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state". \
                                format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))
                            response=client.describe_instances(
                                InstanceIds=[instance_id]
                                )
        
                            if response['Reservations'][0]['Instances'][0]['State']['Name'] == 'running':
                                logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state". \
                                    format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))
                                current_instance_status_details={"InstanceId": instance_id, \
                                    "Status" : response['Reservations'][0]['Instances'][0]['State']['Name'] }
                                
                                topic_response=client_sns.create_topic(
                                    Name=success_sns_notify_topic_name
                                    )
                                success_topic_arn=topic_response['TopicArn']
                                mail_subject='Instance '+str(instance_id)+' is Successfully recovered'
                                trigger_sns_response=trigger_sns_topic(success_topic_arn,current_instance_status_details,mail_subject)
                                logging.info(trigger_sns_response)
                                break
                            
                            elif datetime.datetime.now() >= endTime:
                                logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state. \
                                    It might have some issues". \
                                    format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))
                                current_instance_status_details={
                                    "InstanceId": instance_id, 
                                    "Status": response['Reservations'][0]['Instances'][0]['State']['Name'],
                                    "Message": "Unable to start instance "+str(instance_id)+", Please do necessary action manually" 
                                    
                                }
                                
                                topic_response=client_sns.create_topic(
                                    Name=recovery_failure_sns_notify_topic_name
                                    )
                                topic_arn=topic_response['TopicArn']
                                mail_subject='Unable to start the instance '+str(instance_id)+', \
                                         It is on pending state only since long time'
                                trigger_sns_response=trigger_sns_topic(topic_arn,current_instance_status_details,mail_subject)
                                logging.info(trigger_sns_response)
                                break
                        
                        while response['Reservations'][0]['Instances'][0]['State']['Name'] == 'stopping':
                            time.sleep(1)
                            response=client.describe_instances(
                                InstanceIds=[instance_id]
                            )

                            if response['Reservations'][0]['Instances'][0]['State']['Name'] == 'stopped':
                                logger.info("main.lambda_handler : Instance \"{}\" went to \"{}\" state". \
                                    format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))

                                current_instance_status_details={"InstanceId": instance_id, \
                                    "Status": response['Reservations'][0]['Instances'][0]['State']['Name'], \
                                        "Message": "Instance went to stopped state, Instance is having issues to start. \
                                        Please do necessary action to function normally" }
                                
                                topic_response=client_sns.create_topic(
                                    Name=recovery_failure_sns_notify_topic_name
                                    )
                                topic_arn=topic_response['TopicArn']
                                mail_subject='Instance '+str(instance_id)+' went to ' \
                                        +str(response['Reservations'][0]['Instances'][0]['State']['Name'])+' \
                                        state again, Having issues to launch'
                                trigger_sns_response=trigger_sns_topic(topic_arn,current_instance_status_details,mail_subject)
                                logging.info(trigger_sns_response)
                                break
    
    elif response['Reservations'][0]['Instances'][0]['State']['Name'] != 'stopping':
        response=client.describe_instances(
            InstanceIds=[instance_id]
            )
        endTime = datetime.datetime.now() + datetime.timedelta(minutes=1)  
        logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state. \
            It might have some issues".format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))    
        
        while response['Reservations'][0]['Instances'][0]['State']['Name'] != 'stopping':
            logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state. \
                It might have some issues".format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))
            response=client.describe_instances(
              InstanceIds=[instance_id]
                )
            time.sleep(5)
    
            if datetime.datetime.now() >= endTime:
                logger.info("main.lambda_handler : Instance \"{}\" is still in \"{}\" state. \
                    It might have some issues".format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))    

                current_instance_status_details={
                    "InstanceId": instance_id, 
                    "Status": response['Reservations'][0]['Instances'][0]['State']['Name'],
                    "Message": "Instance is not in recoverable Position. Now it is going to be stopped forcefully" 
                    
                }
                topic_response=client_sns.create_topic(
                        Name=recovery_failure_sns_topic_name
                    )
                topic_arn=topic_response['TopicArn']
                mail_subject='Unable to recover the instance '+str(instance_id)+', Instance is going to be stopped forcefully'
                trigger_sns_response=trigger_sns_topic(topic_arn,current_instance_status_details,mail_subject)
                logging.info(trigger_sns_response)
                break