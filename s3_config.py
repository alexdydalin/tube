import boto3
import botocore


def s3_form_field():
    aws_access_key_id = 'YCAJEFJ3M9_0-1HtwTzDx9vmM'
    aws_secret_access_key = 'YCNv0AroQBpLdcYFsSX7SNBpoJMao85Vdxog7aOp'
    endpoint = 'https://storage.yandexcloud.net'

    s3 = boto3.client('s3',
                      aws_access_key_id=aws_access_key_id,
                      aws_secret_access_key=aws_secret_access_key,
                      region_name='ru-central1',
                      endpoint_url=endpoint,
                      config=botocore.client.Config(signature_version='s3v4'),
                      )

    key = 'videos/${filename}'
    bucket = 'rtf-tube'

    conditions = [
                  {"acl":"public-read"},
                  ["starts-with", "$key", "videos/"]
                 ]
    #fields = {'success_action_redirect': 'https://example.com'}

    form_fields = s3.generate_presigned_post(Bucket=bucket,
                                                      Key=key,
                                                      Conditions=conditions,
                                                      #Fields=fields,
                                                      ExpiresIn=600000000 * 60 )

    return (form_fields)