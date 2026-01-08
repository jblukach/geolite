import geoip2.database
import ipaddress
import json
import os

def handler(event, context):

    try:
        ip = ipaddress.ip_address(event['rawQueryString'])
        ip = str(event['rawQueryString'])
    except ValueError:
        ip = ipaddress.ip_address(event['requestContext']['http']['sourceIp'])
        ip = str(event['requestContext']['http']['sourceIp'])

    try:
        with geoip2.database.Reader('GeoLite2-City.mmdb') as reader:
            response = reader.city(ip)
            country_code = response.country.iso_code
            country_name = response.country.name
            state_code = response.subdivisions.most_specific.iso_code
            state_name = response.subdivisions.most_specific.name
            city_name = response.city.name
            zip_code = response.postal.code
            latitude = response.location.latitude
            longitude = response.location.longitude
            cidr = response.traits.network
    except:
        country_code = None
        country_name = None
        state_code = None
        state_name = None
        city_name = None
        zip_code = None
        latitude = None
        longitude = None
        cidr = None

    try:
        with geoip2.database.Reader('GeoLite2-ASN.mmdb') as reader2:
            response2 = reader2.asn(ip)
            asn = response2.autonomous_system_number
            org = response2.autonomous_system_organization
            net = response2.network
    except:
        asn = None
        org = None
        net = None

    f = open('asn.updated', 'r')
    asnupdated = f.read()
    f.close()

    f = open('city.updated', 'r')
    cityupdated = f.read()
    f.close()

    desc = 'This product includes GeoLite2 data created by MaxMind, available from https://www.maxmind.com.'

    code = 200
    msg = {
        'ip':str(ip),
        'geo': {
            'country':country_name,
            'c_iso':country_code,
            'state':state_name,
            's_iso':state_code,
            'city':city_name,
            'zip':zip_code,
            'latitude':latitude,
            'longitude':longitude,
            'cidr':str(cidr)
        },
        'asn': {
            'id': asn,
            'org': org,
            'net': str(net)
        },
        'attribution':desc,
        'geolite2-asn.mmdb':asnupdated,
        'geolite2-city.mmdb':cityupdated,
        'region': os.environ['AWS_REGION']
    }

    return {
        'statusCode': code,
        'body': json.dumps(msg, indent = 4)
    }