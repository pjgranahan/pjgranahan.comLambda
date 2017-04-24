from __future__ import print_function

import json
import logging
import traceback
from pathlib import Path
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
    logger.info(getoutput(command))


def set_up_hugo():
    # Pull hugo binary from s3
    resource_bucket.download_file(HUGO_BINARY, HUGO_BINARY_PATH)

    # Make the binary executable
    make_executable(HUGO_BINARY_PATH)


def set_up_git():
    # Pull git tarball from s3
    resource_bucket.download_file(GIT_TARBALL, GIT_TARBALL_DIRECTORY)

    # Untar the tarball
    untar(GIT_TARBALL_DIRECTORY, GIT_DIRECTORY)


def make_executable(path_to_binary):
    cl(f"chmod -v 755 {path_to_binary}")


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


def upload_dir_to_s3(directory):
    for file_path in Path(directory).glob('**/*.*'):
        site_bucket.upload_file(file_path.__str__(), file_path.relative_to(directory).__str__())


def lambda_handler(event, context):
    # logger.info("Received event: " + json.dumps(event, indent=2))
    try:
        # Clone source
        cl(f"git clone -v {GITHUB_REPO_URL} {SOURCE_TMP}")

        # Build site
        cl(f"hugo -v --source {SOURCE_TMP} --destination {SOURCE_DEST}")

        # Sync to s3
        site_bucket.objects.all().delete()
        upload_dir_to_s3(SOURCE_DEST)

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
site_bucket = s3.Bucket(SITE_BUCKET)

# Set up hugo and git
set_up_hugo()
set_up_git()
