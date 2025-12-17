import boto3
import datetime
import json
import os
import requests
import tarfile
import zipfile

def handler(event, context):

    secret = boto3.client('secretsmanager')

    getsecret = secret.get_secret_value(
        SecretId = os.environ['SECRET_MGR_ARN']
    )

    login = json.loads(getsecret['SecretString'])

    ssm = boto3.client('ssm')

    asn = ssm.get_parameter(
        Name = os.environ['SSM_PARAMETER_ASN'], 
        WithDecryption = False
    )

    city = ssm.get_parameter(
        Name = os.environ['SSM_PARAMETER_CITY'], 
        WithDecryption = False
    )

    s3_client = boto3.client('s3')

    year = datetime.datetime.now().strftime('%Y')
    month = datetime.datetime.now().strftime('%m')
    day = datetime.datetime.now().strftime('%d')
    hour = datetime.datetime.now().strftime('%H')

    url = 'https://download.maxmind.com/geoip/databases/GeoLite2-City/download?suffix=tar.gz'
    update = requests.head(url, auth=(login['api'], login['key']))

    print('City:', update.headers['last-modified'])
    with open('/tmp/city.updated', 'w') as f:
        f.write(update.headers['last-modified'])
    f.close()

    if city['Parameter']['Value'] != update.headers['last-modified']:

        print("Downloading GeoLite2-City.mmdb")

        url = 'https://download.maxmind.com/geoip/databases/GeoLite2-City/download?suffix=tar.gz'
        response = requests.get(url, auth=(login['api'], login['key']))
        with open('/tmp/maxmind.tar.gz', 'wb') as f:
            f.write(response.content)
        f.close()

        with open('/tmp/GeoLite2-City.mmdb', 'wb') as w:
            with tarfile.open('/tmp/maxmind.tar.gz', 'r:gz') as tar:
                for member in tar.getmembers():
                    if os.path.splitext(member.name)[1] == '.mmdb':
                        r = tar.extractfile(member)
                        if r is not None:
                            content = r.read()
                            r.close()
                            w.write(content)
            tar.close()
        w.close()

        response = s3_client.upload_file('/tmp/city.updated',os.environ['S3_STAGED'],'city.updated')
        response = s3_client.upload_file('/tmp/GeoLite2-City.mmdb',os.environ['S3_STAGED'],'GeoLite2-City.mmdb')
        response = s3_client.upload_file('/tmp/city.updated',os.environ['S3_RESEARCH'],year+'/'+month+'/'+day+'/'+hour+'/city.updated')
        response = s3_client.upload_file('/tmp/GeoLite2-City.mmdb',os.environ['S3_RESEARCH'],year+'/'+month+'/'+day+'/'+hour+'/GeoLite2-City.mmdb')

        ssm.put_parameter(
            Name = os.environ['SSM_PARAMETER_CITY'],
            Value = update.headers['last-modified'],
            Type = 'String',
            Overwrite = True
        )

    url = 'https://download.maxmind.com/geoip/databases/GeoLite2-ASN/download?suffix=tar.gz'
    update = requests.head(url, auth=(login['api'], login['key']))

    print('ASN:', update.headers['last-modified'])
    with open('/tmp/asn.updated', 'w') as f:
        f.write(update.headers['last-modified'])
    f.close()

    if asn['Parameter']['Value'] != update.headers['last-modified']:

        print("Downloading GeoLite2-ASN.mmdb")

        url = 'https://download.maxmind.com/geoip/databases/GeoLite2-ASN/download?suffix=tar.gz'
        response = requests.get(url, auth=(login['api'], login['key']))
        with open('/tmp/maxmind2.tar.gz', 'wb') as f:
            f.write(response.content)
        f.close()

        with open('/tmp/GeoLite2-ASN.mmdb', 'wb') as w:
            with tarfile.open('/tmp/maxmind2.tar.gz', 'r:gz') as tar:
                for member in tar.getmembers():
                    if os.path.splitext(member.name)[1] == '.mmdb':
                        r = tar.extractfile(member)
                        if r is not None:
                            content = r.read()
                            r.close()
                            w.write(content)
            tar.close()
        w.close()

        response = s3_client.upload_file('/tmp/asn.updated',os.environ['S3_STAGED'],'asn.updated')
        response = s3_client.upload_file('/tmp/GeoLite2-ASN.mmdb',os.environ['S3_STAGED'],'GeoLite2-ASN.mmdb')
        response = s3_client.upload_file('/tmp/asn.updated',os.environ['S3_RESEARCH'],year+'/'+month+'/'+day+'/'+hour+'/asn.updated')
        response = s3_client.upload_file('/tmp/GeoLite2-ASN.mmdb',os.environ['S3_RESEARCH'],year+'/'+month+'/'+day+'/'+hour+'/GeoLite2-ASN.mmdb')

        ssm.put_parameter(
            Name = os.environ['SSM_PARAMETER_ASN'],
            Value = update.headers['last-modified'],
            Type = 'String',
            Overwrite = True
    )

    print("Copying GeoLite2-ASN.mmdb")

    with open('/tmp/GeoLite2-ASN.mmdb', 'wb') as f:
        s3_client.download_fileobj(os.environ['S3_STAGED'], 'GeoLite2-ASN.mmdb', f) 
    f.close()

    print("Copying GeoLite2-City.mmdb")

    with open('/tmp/GeoLite2-City.mmdb', 'wb') as f:
        s3_client.download_fileobj(os.environ['S3_STAGED'], 'GeoLite2-City.mmdb', f) 
    f.close()

    print("Copying search.py")

    with open('/tmp/search.py', 'wb') as f:
        s3_client.download_fileobj(os.environ['S3_STAGED'], 'search.py', f) 
    f.close()

    print("Packaging geoip2.zip")

    with zipfile.ZipFile('/tmp/geoip2.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:

        zipf.write('/tmp/asn.updated','asn.updated')
        zipf.write('/tmp/city.updated','city.updated')
        zipf.write('/tmp/search.py','search.py')
        zipf.write('/tmp/GeoLite2-ASN.mmdb','GeoLite2-ASN.mmdb')
        zipf.write('/tmp/GeoLite2-City.mmdb','GeoLite2-City.mmdb')

        for root, dirs, files in os.walk('/tmp/geoip2'):
            for file in files:
                fullpath = os.path.join(root, file)
                zipf.write(fullpath, fullpath[5:])

        for root, dirs, files in os.walk('/tmp/maxminddb'):
            for file in files:
                fullpath = os.path.join(root, file)
                zipf.write(fullpath, fullpath[5:])

    zipf.close()

    response = s3_client.upload_file('/tmp/geoip2.zip',os.environ['S3_STAGED'],'geoip2.zip')

    s3_client = boto3.client('s3', region_name = 'us-east-1')

    response = s3_client.upload_file('/tmp/geoip2.zip',os.environ['S3_USE1'],'geoip2.zip')
 
    s3_client = boto3.client('s3', region_name = 'us-west-2')

    response = s3_client.upload_file('/tmp/geoip2.zip',os.environ['S3_USW2'],'geoip2.zip')

    client = boto3.client('lambda', region_name = 'us-east-1')

    print("Updating "+os.environ['LAMBDA_FUNCTION_USE1'])

    response = client.update_function_code(
        FunctionName = os.environ['LAMBDA_FUNCTION_USE1'],
        S3Bucket = os.environ['S3_USE1'],
        S3Key = 'geoip2.zip'
    )

    client = boto3.client('lambda', region_name = 'us-west-2')

    print("Updating "+os.environ['LAMBDA_FUNCTION_USW2'])

    response = client.update_function_code(
        FunctionName = os.environ['LAMBDA_FUNCTION_USW2'],
        S3Bucket = os.environ['S3_USW2'],
        S3Key = 'geoip2.zip'
    )

    return {
        'statusCode': 200,
        'body': json.dumps('This product includes GeoLite2 data created by MaxMind, available from https://www.maxmind.com.')
    }