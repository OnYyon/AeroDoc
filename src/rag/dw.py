import requests
from pathlib import Path


# Get the file path
output_folder = "documents"
filename = "think_python_guide.pdf"
url = "https://greenteapress.com/thinkpython/thinkpython.pdf"
file_path = Path(output_folder) / filename


def download_file(url: str, file_path: Path):
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()
    file_path.write_bytes(response.content)


# Download the file if it doesn't exist
if not file_path.exists():
    download_file(
        url=url,
        file_path=file_path,
    )
