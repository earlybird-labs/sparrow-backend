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
