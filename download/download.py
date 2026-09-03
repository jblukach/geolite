import base64
import boto3
import hashlib
import json
import os
import tarfile
import zipfile
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import requests

REGIONS = (
    ('us-east-1', 'S3_USE1', 'LAMBDA_FUNCTION_USE1'),
    ('us-east-2', 'S3_USE2', 'LAMBDA_FUNCTION_USE2'),
    ('us-west-2', 'S3_USW2', 'LAMBDA_FUNCTION_USW2')
)

def handler(event, context):
    del event, context

    pending_parameters = []

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

        pending_parameters.append((os.environ['SSM_PARAMETER_CITY'], city_timestamp_utc))

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

        pending_parameters.append((os.environ['SSM_PARAMETER_ASN'], asn_timestamp_utc))

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

    for mmdb in ('/tmp/GeoLite2-ASN.mmdb', '/tmp/GeoLite2-City.mmdb'):
        if os.path.getsize(mmdb) == 0:
            raise RuntimeError(f'{mmdb} is empty')

    with zipfile.ZipFile('/tmp/maxminddb.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:

        zipf.write('/tmp/asn.updated','asn.updated')
        zipf.write('/tmp/city.updated','city.updated')
        zipf.write('/tmp/search.py','search.py')
        zipf.write('/tmp/GeoLite2-ASN.mmdb','GeoLite2-ASN.mmdb')
        zipf.write('/tmp/GeoLite2-City.mmdb','GeoLite2-City.mmdb')

    zipf.close()

    s3_client.upload_file('/tmp/maxminddb.zip', os.environ['S3_STAGED'], 'maxminddb.zip')

    digest = hashlib.sha256()
    with open('/tmp/maxminddb.zip', 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    expected_sha256 = base64.b64encode(digest.digest()).decode('utf-8')

    print('Package SHA256:', expected_sha256)

    failures = []

    for region, bucket_variable, function_variable in REGIONS:

        bucket = os.environ[bucket_variable]
        function = os.environ[function_variable]

        try:

            boto3.client('s3', region_name = region).upload_file(
                '/tmp/maxminddb.zip', bucket, 'maxminddb.zip'
            )

            print('Updating '+function)

            client = boto3.client('lambda', region_name = region)

            client.update_function_code(
                FunctionName = function,
                S3Bucket = bucket,
                S3Key = 'maxminddb.zip'
            )

            # update_function_code is asynchronous, so a failed apply is only visible here.
            client.get_waiter('function_updated_v2').wait(FunctionName = function)

            configuration = client.get_function_configuration(FunctionName = function)

            status = configuration.get('LastUpdateStatus')

            if status != 'Successful':
                raise RuntimeError(
                    f"LastUpdateStatus {status}: "
                    f"{configuration.get('LastUpdateStatusReasonCode')} "
                    f"{configuration.get('LastUpdateStatusReason')}"
                )

            if configuration.get('CodeSha256') != expected_sha256:
                raise RuntimeError(
                    f"CodeSha256 {configuration.get('CodeSha256')} "
                    f"does not match packaged {expected_sha256}"
                )

            print('Updated '+function)

        except Exception as error:

            print('Failed '+function+': '+repr(error))
            failures.append(f'{region}: {error!r}')

    if failures:
        raise RuntimeError('Regional deployment failed -> ' + ' | '.join(failures))

    for name, value in pending_parameters:

        ssm.put_parameter(
            Name = name,
            Value = value,
            Type = 'String',
            Overwrite = True
        )

    return {
        'statusCode': 200,
        'body': json.dumps('This product includes GeoLite2 data created by MaxMind, available from https://www.maxmind.com.')
    }