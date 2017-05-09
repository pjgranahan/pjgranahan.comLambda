from __future__ import print_function

import json
import logging
import traceback
from base64 import b64decode
from os import environ

import boto3
import requests

RECAPTCHA_VERIFICATION_SITE = "https://www.google.com/recaptcha/api/siteverify"
RECAPTCHA_DOMAIN_NAME = "www.pjgranahan.com"

ACCESS_CONTROL_ALLOW_ORIGIN_DOMAIN_NAME = "https://www.pjgranahan.com"

CONTACT_INFO_RESPONSE = {"email_address": environ["EMAIL_ADDRESS"],
                         "phone_number": environ["PHONE_NUMBER"]}


def respond(err=None, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ACCESS_CONTROL_ALLOW_ORIGIN_DOMAIN_NAME,
            'Access-Control-Allow-Methods': "POST,OPTIONS",
            'Access-Control-Allow-Headers': "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        },
    }


class VerificationUnsuccessfulError(Exception):
    pass


class UnrecognizedDomainNameError(Exception):
    def __init__(self, expected_domain, actual_domain):
        self.expected_domain = expected_domain
        self.actual_domain = actual_domain


def verify_verification_response(verification_response):
    logger.info("Received verification response: " + json.dumps(verification_response, indent=2))

    if not verification_response["success"]:
        raise VerificationUnsuccessfulError
    if not verification_response["hostname"] == RECAPTCHA_DOMAIN_NAME:
        raise UnrecognizedDomainNameError(RECAPTCHA_DOMAIN_NAME, verification_response["hostname"])


def lambda_handler(event, context):
    """
    Assumes that the following environment variables are set:
        RECAPTCHA_SECRET_KEY={the secret token you got when setting up reCaptcha}
    """
    logger.info("Received event: " + json.dumps(event, indent=2))
    try:
        # Get user response token from reCaptcha
        user_response_token = json.loads(event["body"])["g-captcha-response"]

        # Verify response token with Google
        verification_params = {
            "secret": DECRYPTED_RECAPTCHA_SECRET,
            "response": user_response_token
        }
        verification_response = requests.post(RECAPTCHA_VERIFICATION_SITE, data=verification_params)

        # Act on verification results
        verify_verification_response(verification_response.json())

        return respond(err=None, res=CONTACT_INFO_RESPONSE)

    except Exception as err:
        err_str = f"{str(err)}\n{traceback.print_exc()}"
        logger.error(err_str)
        return respond(err=err_str)


# Initialize function
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.info('Loading function')

ENCRYPTED_RECAPTCHA_SECRET = environ['RECAPTCHA_SECRET']
DECRYPTED_RECAPTCHA_SECRET = boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED_RECAPTCHA_SECRET))['Plaintext']
