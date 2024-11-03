# scanner-cli
A MacOS CLI client for scanning documents using a network scanner supporting the [Mopria Alliance eSCL Scan Technical Specification](https://mopria.org/MopriaeSCLSpecDownload.php)

Known to work with at least:
- Brother MFC-L2710DW
- Canon Pixma G3260
- HP DeskJet 4640 series
- HP OfficeJet Pro 9000 series

## Installation
From PyPI:
```
pipx install escl-scanner-cli
```

Locally:
```
pip install .
```

## Usage
```
usage: scanner.py [-h] [--source {feeder,flatbed,automatic}] [--format {pdf,jpeg}] [--grayscale] [--resolution {75,100,200,300,600}] [--debug] [--no-open]
                  [--quiet] [--duplex]
                  filename

positional arguments:
  filename

optional arguments:
  -h, --help            show this help message and exit
  --source {feeder,flatbed,automatic}, -S {feeder,flatbed,automatic}
  --format {pdf,jpeg}, -f {pdf,jpeg}
  --grayscale, -g
  --resolution {75,100,200,300,600}, -r {75,100,200,300,600}
  --debug, -d
  --no-open, -o
  --quiet, -q
  --duplex, -D
  ```
