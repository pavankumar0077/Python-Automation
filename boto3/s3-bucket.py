import boto3

client = boto3.client('s3')
# s3 = boto3.client('s3') #Above code is also can we written as.

# THIS IS A COMMON SYNTAX IF WE WANT TO TALK TO ANY SERVICE WE CAN DO IT BY REPLACING THE ' '. INSTEAD OF S3 WE CAN GO WITH OTHER SERVICE WICH
# WE WANT TO TALK OR WORK WITH

#botocore # Handles the exceptions



s3.create_bucket(
    Bucket='boto3-testing-pavan-account',
    CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'}
)

# response = client.get_bucket_acl(
#     Bucket='boto3-testing-pavan-account',
# )

print("Bucket created!")
# print(response)