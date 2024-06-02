"""Utilities processes."""

from bs4 import BeautifulSoup


def clean_html(html):
    """Clean the HTML."""
    soup = BeautifulSoup(html, features="html.parser")
    if body := soup.find("body"):
        # get text
        text = body.get_text()

        # break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # drop blank lines
        text = "\n".join(chunk for chunk in chunks if chunk)
        return text.replace("\xa0", " ")

    return html


def add_attribute_to_item(item, user_input, attribute):
    """Add an attribute to an item."""
    if user_input.get(attribute) is not None:
        item[attribute] = user_input[attribute]
    elif attribute in item:
        del item[attribute]
