
# Validate IHEC Data Hub Tracks

```sh
./validate_datahub_tracks.py ./hub.json
```

```
usage: validate_datahub_tracks.py [-h] [-f] [-d DOWNLOAD] [-c CHROM_COUNT]
                                  [-b BASES_COVERED] [-s BIN_SIZE]
                                  [-t TOP_BINS]
                                  input

positional arguments:
  input                 Input IHEC Data Hub JSON file

optional arguments:
  -h, --help            show this help message and exit
  -f, --force           Force redownload of tracks
  -d DOWNLOAD, --download DOWNLOAD
                        Directory to store downloaded tracks
  -c CHROM_COUNT, --chrom CHROM_COUNT
                        Minimum chrom count
  -b BASES_COVERED, --bases BASES_COVERED
                        Minimum bases covered
  -s BIN_SIZE, --bin-size BIN_SIZE
                        Bin size
  -t TOP_BINS, --top-bins TOP_BINS
                        Top bins to check, in percentage
```

### Installation

```sh
sudo pip install -r requirements.txt
```
