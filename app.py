#!/usr/bin/env python3
import os

import aws_cdk as cdk

from geo.geo_download import GeoDownload
from geo.geo_search_use1 import GeoSearchUSE1
from geo.geo_search_use2 import GeoSearchUSE2
from geo.geo_search_usw2 import GeoSearchUSW2
from geo.geo_stack import GeoStack

app = cdk.App()

geo_download = GeoDownload(
    app,
    'GeoDownload',
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region='us-east-2',
    ),
    synthesizer=cdk.DefaultStackSynthesizer(
        qualifier='lukach',
    ),
)

geo_search_use1 = GeoSearchUSE1(
    app,
    'GeoSearchUSE1',
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region='us-east-1',
    ),
    synthesizer=cdk.DefaultStackSynthesizer(
        qualifier='lukach',
    ),
)

geo_search_usw2 = GeoSearchUSW2(
    app,
    'GeoSearchUSW2',
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region='us-west-2',
    ),
    synthesizer=cdk.DefaultStackSynthesizer(
        qualifier='lukach',
    ),
)

geo_search_use2 = GeoSearchUSE2(
    app,
    'GeoSearchUSE2',
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region='us-east-2',
    ),
    synthesizer=cdk.DefaultStackSynthesizer(
        qualifier='lukach',
    ),
)

geo_stack = GeoStack(
    app,
    'GeoStack',
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region='us-east-1',
    ),
    synthesizer=cdk.DefaultStackSynthesizer(
        qualifier='lukach',
    ),
)

geo_download.add_stack_dependency(geo_search_use1)
geo_download.add_stack_dependency(geo_search_usw2)
geo_download.add_stack_dependency(geo_search_use2)
geo_download.add_stack_dependency(geo_stack)

cdk.Tags.of(app).add('Alias', 'geo')
cdk.Tags.of(app).add('GitHub', 'https://github.com/jblukach/geo')
cdk.Tags.of(app).add('Org', 'lukach.io')

app.synth()