import time
from functools import wraps
from slack_sdk.errors import SlackApiError


def retry(exception_to_check, tries=4, delay=3, backoff=2, logger=None):
    """
    Retry calling the decorated function using an exponential backoff.

    :param exception_to_check: the exception to check. may be a tuple of exceptions to check
    :param tries: number of times to try (not retry) before giving up
    :param delay: initial delay between retries in seconds
    :param backoff: backoff multiplier e.g. value of 2 will double the delay each retry
    :param logger: logger to use. If None, print.
    """

    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exception_to_check as e:
                    msg = f"{str(e)}, Retrying in {mdelay} seconds..."
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry

    return deco_retry


# Apply the retry decorator to the say function
@retry(SlackApiError, tries=5, delay=2, backoff=3)
def safe_say(say, *args, **kwargs):
    say(*args, **kwargs)


def extract_plain_text_from_blocks(blocks):
    """
    Extracts plain text from the given blocks of a Slack event.

    :param blocks: A list of blocks from a Slack event.
    :return: A string containing all the plain text extracted from the blocks.
    """
    plain_text = ""
    for block in blocks:
        for element in block.get("elements", []):
            for item in element.get("elements", []):
                if item.get("type") == "text":
                    plain_text += item.get("text", "")
    return plain_text
