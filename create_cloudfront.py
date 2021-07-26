#!/usr/bin/env python3

import boto3
import sys
import json
import datetime
import time
import botocore

time_now = str(datetime.datetime.now())


boto3.setup_default_session(profile_name=sys.argv[4])
client = boto3.client('cloudfront')
s3_client = boto3.client('s3')

list_buckets_response = s3_client.list_buckets()


# sending subsequent requests to get all distributions
paginator = client.get_paginator('list_distributions')



def create_cloudfront(bucket_name, bucket_path, customer_name, origin_id):

    cloudfront_response = client.create_distribution_with_tags(
        DistributionConfigWithTags={
            'DistributionConfig':{
                'CallerReference' : time_now,
                'Comment': 'Cloudfront url for the S3 bucket with '+bucket_path+' path',
                'Enabled': True,
                'Origins': {
                    'Quantity': 1,
                    'Items': [
                        {
                            'Id': origin_id,
                            'DomainName': bucket_name+'.s3.amazonaws.com',
                            'OriginPath': '/'+bucket_path,
                            'S3OriginConfig': {
                                'OriginAccessIdentity': 'origin-access-identity/cloudfront/XXXXXXXXXXXX'
                            }
                        }
                    ]
                },
                'DefaultCacheBehavior': {
                    'TargetOriginId': origin_id,
                    'ViewerProtocolPolicy' : 'redirect-to-https',
                    'MinTTL': 1000,
                    'ForwardedValues':{
                        'QueryString': False,
                        'Cookies': {
                            'Forward': 'all'
                        }
                    }
                    }
                },
                'Tags':{
                    'Items': [
                        {
                            'Key': 'Customer',
                            'Value': customer_name
                        },
                    ]
                }
            }
        )
    waiter = client.get_waiter('distribution_deployed')
    waiter.wait(Id=cloudfront_response['Distribution']['Id'])
    return cloudfront_response['Distribution']['DomainName']


def main():

    customer_name = sys.argv[1]
    bucket_path= sys.argv[3]

    bucket_name=sys.argv[2]
    origin_id="S3-"+bucket_name+"/"+bucket_path
        
    for bucket in list_buckets_response['Buckets']:
        if bucket['Name'] == bucket_name:
            for distributionlist in paginator.paginate():
                if distributionlist['DistributionList']['Quantity'] > 0:
                    for origin in distributionlist['DistributionList']['Items']:
                        for item in origin['Origins']['Items']:
                            if item['Id'] == origin_id:
                                print("Cloudfront URL is already exists for the given path!!")
                                print("Cloudfront URL:- https://"+origin['DomainName'])
                                sys.exit(0)

            cloudfront_domain = create_cloudfront(bucket_name, bucket_path, customer_name, origin_id)

            policy = s3_client.get_bucket_policy(Bucket=bucket_name)

            json_policy = json.loads(policy['Policy'])

            statement_policy = json_policy['Statement']

            print("Existing Bucket Policy:")
            print(json_policy)

            # prinicpal_id = 'arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity '+origin_access_id
            json_user_policy =  {
                            'Sid':bucket_path.partition('/')[0]+'Perm',
                            'Effect':'Allow',
                            'Principal':
                                {
                                'AWS':'arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity XXXXXXXXXXXX'
                            },
                            'Action':'s3:GetObject',
                            'Resource':'arn:aws:s3:::'+bucket_name+'/'+bucket_path+'/*'
                        }
            # user_policy = json.dumps(json_user_policy, indent=4)

            statement_policy.append(json_user_policy)

            bucket_policy = {
                'Version': json_policy['Version'],
                'Statement': statement_policy
                }
            json_bucket_policy = json.dumps(bucket_policy)


            print("Updated bucket policy:")
            print(json_bucket_policy)

            try:
                s3_client.put_bucket_policy(
                        Bucket=bucket_name,
                        Policy=json_bucket_policy
                    )
            
            except botocore.exceptions.ClientError as Error:
                raise Error

            print("Cloudfront Domain has generated")
            print("Cloudfront URL: https://"+cloudfront_domain)
            sys.exit(0)


    print("Error: Given s3 Bucket doesn't exist in aws account")
    print("Error: Please provide valid bucket name")
    sys.exit(1)
    
if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Please provide the proper format as like below")
        print("Usage: python3 create_cloudfront.py <name> <bucket_name> <bucket_path> <aws_profile>")
        print("EX: python3 create_cloudfront.py gokula gokula-bucket Images/S3 dev-account")
        sys.exit(1)

    main()
