from __future__ import print_function

import hashlib
import hmac
import json
import logging
import traceback
from os import environ
from subprocess import getoutput

import boto3

GITHUB_REPO_URL = "https://github.com/pjgranahan/pjgranahan.com.git"
RESOURCE_BUCKET = "pjgranahan-com-hugo-build-lambda-resources"
SITE_BUCKET = "pjgranahan-com-static-site-bucket"

SITE_SOURCE_DIR = "/tmp/source/"
SITE_BUILD_DIR = "/tmp/source/public/"

GIT_TAR = "git-2.4.3.tar"
GIT_TAR_DIR = "/tmp/git.tar"
GIT_DIR = "/tmp/git/"  # Actual binary 'git' is at /tmp/git/usr/bin/git

HUGO_BINARY = "hugo_0.20.2_linux_amd64"
HUGO_BINARY_DIR = "/tmp/"
HUGO_BINARY_PATH = HUGO_BINARY_DIR + "hugo"

AWSCLI_ZIP = "awscli.zip"
AWSCLI_ZIP_PATH = "/tmp/awscli.zip"
AWSCLI_BINARY_DIR = "/tmp/awscli/"

PYGMENTS_ZIP = "pygments.zip"
PYGMENTS_ZIP_PATH = "/tmp/pygments.zip"
PYGMENTS_BINARY_DIR = "/tmp/pygments/"


def cl(command):
    log_context = f"Running command '{command}'\n"
    output = getoutput(command)
    logging.info(log_context + output)
    return output


def set_up_hugo():
    """
    Assumes that the following environment variables are set:
        PATH=$PATH:{HUGO_BINARY_DIR}
    """
    resource_bucket.download_file(HUGO_BINARY, HUGO_BINARY_PATH)
    make_executable(HUGO_BINARY_PATH)


def set_up_git():
    """
    Assumes that the following environment variables are set:
        GIT_EXEC_PATH={GIT_DIR}usr/libexec/git-core
        GIT_TEMPLATE_DIR={GIT_DIR}usr/share/git-core/templates
        PATH=$PATH:{GIT_DIR}usr/bin
    """
    resource_bucket.download_file(GIT_TAR, GIT_TAR_DIR)
    untar(GIT_TAR_DIR, GIT_DIR)


def set_up_python_package(zip_name, zip_download_path, unzipped_binary_dir):
    """
    Sets up Python packages prepared using the alestic approach: https://alestic.com/2016/11/aws-lambda-awscli/
    Assumes that the following environment variables are set:
        PATH=$PATH:{unzipped_binary_dir}
    """
    resource_bucket.download_file(zip_name, zip_download_path)
    cl(f"unzip {zip_download_path} -d {unzipped_binary_dir}")


def make_executable(path_to_binary):
    cl(f"chmod -v +x {path_to_binary}")


def untar(tarball, dest_dir):
    cl(f"mkdir -v {dest_dir}")
    cl(f"tar -xf {tarball} -C {dest_dir}")


def respond(err=None, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def verify_webhook(payload_body, header_signature):
    """
    Verifies a webhook is from Github by comparing secrets. See https://developer.github.com/webhooks/securing/
    Assumes that the following environment variables are set:
        GITHUB_SECRET={the same secret token you used when you setup your Github webhook}
    """
    signature = "sha1=" + hmac.new(str.encode(environ['GITHUB_SECRET']),
                                   msg=str.encode(payload_body),
                                   digestmod=hashlib.sha1).hexdigest()
    if not hmac.compare_digest(signature, header_signature):
        raise PermissionError


def lambda_handler(event, context):
    logger.info("Received event: " + json.dumps(event, indent=2))
    try:
        # Verify that the webhook was from GitHub
        verify_webhook(event["body"], event["headers"]["X-Hub-Signature"])

        # Update source
        cl(f"( cd {SITE_SOURCE_DIR}; git pull -v )")

        # Build site
        cl(f"hugo -v --source {SITE_SOURCE_DIR} --destination {SITE_BUILD_DIR}")

        # Sync to s3
        cl(f"aws s3 sync {SITE_BUILD_DIR} s3://{SITE_BUCKET} "
           f"--delete --cache-control max-age=10 --storage-class REDUCED_REDUNDANCY")

        return respond(err=None, res="Success")

    except Exception as err:
        err_str = f"{str(err)}\n{traceback.print_exc()}"
        logger.error(err_str)
        return respond(err=err_str)


# Initialize function
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.info('Loading function')

# Set up the s3 client and buckets
s3 = boto3.resource('s3')
resource_bucket = s3.Bucket(RESOURCE_BUCKET)

# Set up needed binaries
set_up_hugo()
set_up_git()
set_up_python_package(AWSCLI_ZIP, AWSCLI_ZIP_PATH, AWSCLI_BINARY_DIR)
set_up_python_package(PYGMENTS_ZIP, PYGMENTS_ZIP_PATH, PYGMENTS_BINARY_DIR)

# Clone source
cl(f"git clone -v {GITHUB_REPO_URL} {SITE_SOURCE_DIR}")
