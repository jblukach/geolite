import boto3
import json
import os
import tarfile
import zipfile
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import requests

def handler(event, context):
    del event, context

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

    def _utc_iso_timestamp(timestamp_value):
        if not timestamp_value:
            return datetime.now(UTC).isoformat().replace('+00:00', 'Z')
        parsed = parsedate_to_datetime(timestamp_value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).isoformat().replace('+00:00', 'Z')

    def _download_mmdb_archive(url, archive_path, output_mmdb_path):
        response = requests.get(url, auth=(login['api'], login['key']), timeout=300)
        response.raise_for_status()
        with open(archive_path, 'wb') as file_handle:
            file_handle.write(response.content)

        with open(output_mmdb_path, 'wb') as output_handle:
            with tarfile.open(archive_path, 'r:gz') as tar_handle:
                for member in tar_handle.getmembers():
                    if os.path.splitext(member.name)[1] == '.mmdb':
                        extracted = tar_handle.extractfile(member)
                        if extracted is not None:
                            output_handle.write(extracted.read())
                            extracted.close()
                            return

        raise RuntimeError(f'MMDB file not found in archive from {url}')

    url = 'https://download.maxmind.com/geoip/databases/GeoLite2-City/download?suffix=tar.gz'
    update = requests.head(url, auth=(login['api'], login['key']), timeout=60)
    update.raise_for_status()

    city_timestamp_utc = _utc_iso_timestamp(update.headers.get('last-modified'))

    print('City:', city_timestamp_utc)
    with open('/tmp/city.updated', 'w', encoding='utf-8') as f:
        f.write(city_timestamp_utc)
    f.close()

    if city['Parameter']['Value'] != city_timestamp_utc:

        print("Downloading GeoLite2-City.mmdb")

        _download_mmdb_archive(
            url = url,
            archive_path = '/tmp/maxmind-city.tar.gz',
            output_mmdb_path = '/tmp/GeoLite2-City.mmdb'
        )

        s3_client.upload_file('/tmp/city.updated', os.environ['S3_STAGED'], 'city.updated')
        s3_client.upload_file('/tmp/GeoLite2-City.mmdb', os.environ['S3_STAGED'], 'GeoLite2-City.mmdb')

        ssm.put_parameter(
            Name = os.environ['SSM_PARAMETER_CITY'],
            Value = city_timestamp_utc,
            Type = 'String',
            Overwrite = True
        )

    url = 'https://download.maxmind.com/geoip/databases/GeoLite2-ASN/download?suffix=tar.gz'
    update = requests.head(url, auth=(login['api'], login['key']), timeout=60)
    update.raise_for_status()

    asn_timestamp_utc = _utc_iso_timestamp(update.headers.get('last-modified'))

    print('ASN:', asn_timestamp_utc)
    with open('/tmp/asn.updated', 'w', encoding='utf-8') as f:
        f.write(asn_timestamp_utc)
    f.close()

    if asn['Parameter']['Value'] != asn_timestamp_utc:

        print("Downloading GeoLite2-ASN.mmdb")

        _download_mmdb_archive(
            url = url,
            archive_path = '/tmp/maxmind-asn.tar.gz',
            output_mmdb_path = '/tmp/GeoLite2-ASN.mmdb'
        )

        s3_client.upload_file('/tmp/asn.updated', os.environ['S3_STAGED'], 'asn.updated')
        s3_client.upload_file('/tmp/GeoLite2-ASN.mmdb', os.environ['S3_STAGED'], 'GeoLite2-ASN.mmdb')

        ssm.put_parameter(
            Name = os.environ['SSM_PARAMETER_ASN'],
            Value = asn_timestamp_utc,
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

    print("Packaging maxminddb.zip")

    with zipfile.ZipFile('/tmp/maxminddb.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:

        zipf.write('/tmp/asn.updated','asn.updated')
        zipf.write('/tmp/city.updated','city.updated')
        zipf.write('/tmp/search.py','search.py')
        zipf.write('/tmp/GeoLite2-ASN.mmdb','GeoLite2-ASN.mmdb')
        zipf.write('/tmp/GeoLite2-City.mmdb','GeoLite2-City.mmdb')

    zipf.close()

    s3_client.upload_file('/tmp/maxminddb.zip', os.environ['S3_STAGED'], 'maxminddb.zip')

    s3_client = boto3.client('s3', region_name = 'us-east-1')

    s3_client.upload_file('/tmp/maxminddb.zip', os.environ['S3_USE1'], 'maxminddb.zip')

    s3_client = boto3.client('s3', region_name = 'us-east-2')

    s3_client.upload_file('/tmp/maxminddb.zip', os.environ['S3_USE2'], 'maxminddb.zip')
 
    s3_client = boto3.client('s3', region_name = 'us-west-2')

    s3_client.upload_file('/tmp/maxminddb.zip', os.environ['S3_USW2'], 'maxminddb.zip')

    client = boto3.client('lambda', region_name = 'us-east-1')

    print("Updating "+os.environ['LAMBDA_FUNCTION_USE1'])

    client.update_function_code(
        FunctionName = os.environ['LAMBDA_FUNCTION_USE1'],
        S3Bucket = os.environ['S3_USE1'],
        S3Key = 'maxminddb.zip'
    )

    client = boto3.client('lambda', region_name = 'us-east-2')

    print("Updating "+os.environ['LAMBDA_FUNCTION_USE2'])

    client.update_function_code(
        FunctionName = os.environ['LAMBDA_FUNCTION_USE2'],
        S3Bucket = os.environ['S3_USE2'],
        S3Key = 'maxminddb.zip'
    )

    client = boto3.client('lambda', region_name = 'us-west-2')

    print("Updating "+os.environ['LAMBDA_FUNCTION_USW2'])

    client.update_function_code(
        FunctionName = os.environ['LAMBDA_FUNCTION_USW2'],
        S3Bucket = os.environ['S3_USW2'],
        S3Key = 'maxminddb.zip'
    )

    return {
        'statusCode': 200,
        'body': json.dumps('This product includes GeoLite2 data created by MaxMind, available from https://www.maxmind.com.')
    }