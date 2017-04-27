# pjgranahan.com Lambda
An AWS Lambda Python 3.6 function that, when triggered by a GitHub push webhook, builds [my website](https://github.com/pjgranahan/pjgranahan.com) and deploys it at [pjgranahan.com](https://www.pjgranahan.com).

## Initialization
AWS Lambda functions can perform some initialization that is then shared between Lambda invocations that are run while the function is still "hot" ([read more](https://aws.amazon.com/blogs/compute/container-reuse-in-lambda/)) .
This function uses this opportunity to download and set up the following programs:
 - [Hugo](https://gohugo.io/)
 - git
 - [AWS CLI](https://aws.amazon.com/cli/)
 - [Pygments](http://pygments.org/)
 
For AWS CLI and Pygments, I followed [Eric Hammond's directions](https://alestic.com/2016/11/aws-lambda-awscli/) to package them into ZIPs.
Hugo, Git, AWS CLI, and Pygments are all stored in an S3 bucket and pulled down to the Lambda function during initialization.
They are also placed on the $PATH, so Hugo can run with [GitInfo](https://gohugo.io/extras/gitinfo/) and [syntax highlighting](https://gohugo.io/extras/highlighting/)!

## Security
I host this function using AWS API Gateway at the endpoint https://api.pjgranahan.com/site/build. 
This is a public endpoint, so there are a few countermeasures in place to prevent excessive spam:
 - API Gateway is throttled down to 1 request per second. This should be fine for normal usage, as I don't ever expect to commit more than once per second to my website repo.
 - [Payloads are validated](https://developer.github.com/webhooks/securing/). GitHub uses an HMAC hexdigest to compute the hash of the payload of the webhook they send. Using a shared secret that I set, I can verify that this is a valid signature, and that the webhook actually came from Github. If the request is illegitimate, the function errors out immediately and I'm only billed for a 100ms Lambda call, the cheapest.

## Configuration
This function is written in Python 3.6, and benefits from running with the most powerful environment (1536 MB) ([read more about Lambda compute resources](https://aws.amazon.com/lambda/faqs/)).
For context, here are some one-off rough timing results from different resources settings with cold-starts:
 - 128  MB: ~14 seconds total, 11102.67 ms function duration, 128 MB max memory used
 - 512  MB: ~6  seconds total, 2991.05  ms function duration, 223 MB max memory used
 - 896  MB: ~4  seconds total, 1596.80  ms function duration, 213 MB max memory used
 - 1216 MB: ~4  seconds total, 1291.17  ms function duration, 219 MB max memory used
 - 1536 MB: ~3  seconds total, 1123.91  ms function duration, 220 MB max memory used
 
You can see that even though memory usage quickly plateaus, increasing compute resources continues to speed up the function.
There is also a non-trivial amount of initialization time which I'm not billed for.

Just for fun, I also tried disabling all logging and outputs and got comparable timing results.

## Cost to run
To be determined...
