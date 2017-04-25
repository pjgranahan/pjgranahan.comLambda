from __future__ import print_function

import json
import logging
import traceback
from subprocess import getoutput

import boto3

SOURCE_TMP = "/tmp/source/"
SOURCE_DEST = "/tmp/source/public/"
GITHUB_REPO_URL = "https://github.com/pjgranahan/pjgranahan.com.git"
RESOURCE_BUCKET = "pjgranahan-com-hugo-build-lambda-resources"
SITE_BUCKET = "pjgranahan-com-static-site-bucket"
GIT_TARBALL = "git-2.4.3.tar"
GIT_TARBALL_DIRECTORY = "/tmp/git.tar"
GIT_DIRECTORY = "/tmp/git/"
HUGO_BINARY = "hugo_0.20.2_linux_amd64"
HUGO_BINARY_PATH = "/tmp/hugo"
AWSCLI_ZIP = "awscli.zip"
AWSCLI_ZIP_PATH = "/tmp/awscli.zip"
AWSCLI_BINARY_DIR = "/tmp/"


def cl(command):
    log_context = f"Running command '{command}'\n"
    output = getoutput(command)
    logging.info(log_context + output)
    return output


def set_up_hugo():
    resource_bucket.download_file(HUGO_BINARY, HUGO_BINARY_PATH)
    make_executable(HUGO_BINARY_PATH)


def set_up_git():
    resource_bucket.download_file(GIT_TARBALL, GIT_TARBALL_DIRECTORY)
    untar(GIT_TARBALL_DIRECTORY, GIT_DIRECTORY)


def set_up_awscli():
    resource_bucket.download_file(AWSCLI_ZIP, AWSCLI_ZIP_PATH)
    cl(f"unzip {AWSCLI_ZIP_PATH} -d {AWSCLI_BINARY_DIR}")


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


def lambda_handler(event, context):
    # logger.info("Received event: " + json.dumps(event, indent=2))
    try:
        # Clone source
        cl(f"git clone -v {GITHUB_REPO_URL} {SOURCE_TMP}")

        # Build site
        cl(f"hugo -v --source {SOURCE_TMP} --destination {SOURCE_DEST}")

        # Sync to s3
        cl(f"aws s3 sync {SOURCE_DEST} s3://{SITE_BUCKET} --delete")

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
set_up_awscli()
