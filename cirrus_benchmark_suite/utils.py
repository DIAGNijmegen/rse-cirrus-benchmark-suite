import contextlib
import os
import re
import subprocess
import time
from contextlib import ContextDecorator

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


DEBUG = str(os.getenv("DEBUG", False)).lower() == "true"

if DEBUG:
    print("!! Running in DEBUG mode, benchmarks might be unreliable !!")


class Timer(ContextDecorator):
    start_time = None
    end_time = None
    elapsed_time = None  # ms

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *_, **__):
        self.end_time = time.perf_counter()
        self.elapsed_time = round((self.end_time - self.start_time) * 1000)


@contextlib.contextmanager
def new_page(ctx):
    page = ctx.new_page()
    yield page
    page.close()


def getenv(name):
    value = os.getenv(name)
    if not value:
        raise ValueError(f"No {name} environment variable provided")
    return value


def get_git_hash():
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"])
            .strip()
            .decode("utf-8")
        )
    except subprocess.CalledProcessError:
        return None


def get_cirrus_version(page):
    # Close the Error message
    page.locator("#message-modal").get_by_text("Close").click()

    # Navigate to the help and extract the version
    page.get_by_role("button", name="Help").click()

    version_el = page.locator("li").filter(has_text=re.compile(r"^Version:"))
    version_text = version_el.text_content()

    if version_text:
        match = re.search(r"Version: (v\d+\.\d+\.\d+)", version_text)
        if match:
            return match.group(1)

    raise RuntimeError("Could not find CIRRUS version")


def generate_markdown_table(headers, rows):
    # Create the header row
    header_row = "| " + " | ".join(headers) + " |"

    # Create the separator row (for alignment)
    separator_row = "| " + " | ".join(["---"] * len(headers)) + " |"

    # Create the data rows
    data_rows = []
    for row in rows:
        data_row = "| " + " | ".join(str(cell) for cell in row) + " |"
        data_rows.append(data_row)

    # Combine all parts into the final markdown table
    markdown_table = "\n".join([header_row, separator_row] + data_rows)

    return markdown_table
