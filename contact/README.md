# contact.py
Handles server-side verification logic for reCaptcha protected contact information.

## Security
I host this function using AWS API Gateway at the endpoint https://api.pjgranahan.com/site/recaptcha/verify.
This is a public endpoint, so there are a few countermeasures in place to prevent excessive spam:
 - [CORS Access-Control-Allow-Origin](https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS#Access-Control-Allow-Origin). The API can only be called from pjgranahan.com without throwing CORS errors.
 - [reCaptcha requests are verified](https://developers.google.com/recaptcha/docs/verify). I pass the response token from reCaptcha alongside the secret I've shared with Google, and Google tells me if the reCaptcha attempt succeeded. I then also validate the domain name that Google thinks the reCaptcha attempt is for.
 - API Gateway is throttled down to 1 request per second. This should be fine for normal usage, as I don't ever expect people trying to contact me more than once per second.

## Configuration
This function is written in Python 3.6. Speed is primarily bound by network latency and Google's response time, so there is only very marginal benefit to running with more compute resources.
