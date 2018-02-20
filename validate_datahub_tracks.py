#!/usr/bin/env python
from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib2
from colorama import Fore as FG
from colorama import Back as BG
from colorama import Style

from background_noise import get_top_bins_percentage

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f',    '--force',    dest='force',         help='Force redownload of tracks',           default=False,    action='store_true')
    parser.add_argument('-d',    '--download', dest='download',      help='Directory to store downloaded tracks', default='./tracks')
    parser.add_argument('-c',    '--chrom',    dest='chrom_count',   help='Minimum chrom count',                  default=23,       type=int)
    parser.add_argument('-b',    '--bases',    dest='bases_covered', help='Minimum bases covered',                default=75000000, type=int)
    parser.add_argument('-s',    '--bin-size', dest='bin_size',      help='Bin size',                             default=25,       type=int)
    parser.add_argument('-t',    '--top-bins', dest='top_bins',      help='Top bins to check, in percentage',     default=10,       type=int)
    parser.add_argument('input', help='Input IHEC Data Hub JSON file')

    options = parser.parse_args()

    tracks = get_tracks(options)

    create_directory(options.download)

    print(Style.BRIGHT + 'Input: ' + FG.YELLOW + options.input + Style.RESET_ALL)
    print(Style.BRIGHT + 'Download dir: ' + FG.YELLOW + options.download + Style.RESET_ALL)
    print(Style.BRIGHT + 'Tracks: ' + FG.YELLOW + str(len(tracks)) + Style.RESET_ALL)


    # Run each step

    apply_step(options, tracks, download_track)
    apply_step(options, tracks, validate_md5)
    apply_step(options, tracks, check_track_info)
    apply_step(options, tracks, check_background_noise)

    # Print final report

    print('')
    print(Style.BRIGHT + 'Report:' + Style.RESET_ALL)
    print('')

    has_messages = False
    for track in tracks:
        if len(track['messages']) == 0:
            continue
        has_messages = True

        print('{style}{dataset}:{type}:'.format(style=Style.NORMAL, dataset=track['dataset'], type=track['track_type']) + Style.RESET_ALL)
        for message in track['messages']:
            print(FG.LIGHTBLACK_EX + indent(2, '%s' % message) + Style.RESET_ALL)

    if not has_messages:
        print(Style.BRIGHT + FG.GREEN + 'All tracks have been succesfully validated' + Style.RESET_ALL)

    print('')

# end

def apply_step(options, tracks, fn):
    print(Style.BRIGHT + '\nStep: ' + fn.__name__ + Style.RESET_ALL)
    for track in tracks:
        if track['skip']:
            continue
        fn(options, track)
    log('Done')

#
# Steps: Each function here takes the options and a single track as argument,
#  and can run any operation on it. If track['skip'] is set to True, it will
#  be skipped by subsequent steps.
#

def download_track(options, track):
    """
    Download the track.url into track.path
    """

    if os.path.isfile(track['path']) and options.force is False:
        # Skip redownloading the file if already present
        return

    try:
        download_bigwig(track['url'], track['path'])
    except Exception as exception:
        message = 'Failed to download: %s' % (repr(exception))
        track['messages'].append(message)
        track['skip'] = True
        log_error(FG.RED + message + Style.RESET_ALL)

def validate_md5(options, track):
    """
    Validates the md5 of the file
    """

    md5 = get_file_md5(track['path'])

    if md5 != track['md5']:
        track['messages'].append(
            'File md5 sum is different than the specified value:\n  Specified:  %s\n  Real:       %s' % (track['md5'], md5)
        )

def check_track_info(options, track):
    """
    Download the track.url into track.path
    """

    if not os.path.isfile(track['path']):
        # If the URL was invalid, the file has not been downloaded
        log(FG.LIGHTBLACK_EX + 'Skipping %s' % track['url'])
        return

    try:
        process = subprocess.Popen(
            [get_program_for_file(track['path']), track['path']],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        returncode = process.returncode
    except Exception as e:
        message = repr(e)
        track['messages'].append(message)
        log_error(message)
        return

    if returncode != 0:
        message = stderr.strip()
        track['messages'].append(message)
        log_error(message)
        return

    result = parse_entries(stdout)
    chrom_count   = parse_number(result['chromCount'])
    bases_covered = parse_number(result['basesCovered'])

    if chrom_count < options.chrom_count:
        message = 'Not enough chroms: %s (min %s)' % (chrom_count, options.chrom_count)
        track['messages'].append(message)
        log_error(message)

    if bases_covered < options.bases_covered:
        message = 'Not enough bases: %s (min %s)' % (bases_covered, options.bases_covered)
        track['messages'].append(message)
        log_error(message)

def check_background_noise(options, track):
    """
    Check if there is backgrond noise in the track
    """

    if not is_bigwig(track['path']):
        # Skip bigBed files
        return

    try:
        print(get_top_bins_percentage(options.bin_size, options.top_bins, track['path']))
    except Exception as e:
        track['messages'].append(repr(e))


#
# Utilities
#

def log(message):
    print(Style.BRIGHT + '==> ' + Style.RESET_ALL + message + Style.RESET_ALL)

def log_error(message):
    print(Style.BRIGHT + '==> ' + Style.RESET_ALL + FG.RED + message + Style.RESET_ALL)

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def read_json(filepath):
    with open(filepath) as input_file:
        result = json.load(input_file)
    return result

def get_tracks(options):
    hub = read_json(options.input)
    tracks = []
    for dataset_id, dataset in hub['datasets'].items():
        for track_type, typeTracks in dataset['browser'].items():
            for track in typeTracks:
                tracks.append({
                    'dataset': dataset_id,
                    'track_type': track_type,
                    'url': track['big_data_url'],
                    'path': os.path.join(options.download, sanitize_filename(track['big_data_url'])),
                    'md5': track['md5sum'],
                    'skip': False,
                    'messages': []
                })

def sanitize_filename(filename):
    return re.sub(r'[^\w\s\-.]', '_', filename)

def download_bigwig(url, path=None):
    response = urllib2.urlopen(url)
    meta = response.info()
    content_type = meta.getheaders('Content-Type')[0]

    if content_type != 'application/octet-stream':
        raise Exception('Response content-type is not application/octet-stream')

    file_name = path or url.split('/')[-1]
    file_handle = open(file_name, 'wb')
    file_size = int(meta.getheaders('Content-Length')[0])

    log('Downloading: %s\t[%s]' % (file_name, file_size))

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = response.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        file_handle.write(buffer)
        status = r'%10d  [%3.2f%%]' % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)

        if sys.stdout.isatty():
            sys.stdout.write(status)
            sys.stdout.flush()

    if sys.stdout.isatty():
        sys.stdout.write(' ' * len(status) + chr(8)*(len(status)+1))
        sys.stdout.flush()

    file_handle.close()

def get_file_md5(filepath):
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_program_for_file(file):
    if is_bigwig(file):
        return 'bigWigInfo'
    return 'bigBedInfo'

def is_bigwig(filename):
    clean_filename = filename.lower()
    m = re.search('\?.*', clean_filename)
    if m:
        clean_filename = clean_filename.replace(m.group(0), '')
    return clean_filename[-2:] == 'bw' or clean_filename[-6:] == 'bigwig'

def parse_entries(output):
    lines = output.split('\n')
    entries = [line.split(':') for line in lines if line.strip() != '']
    result = {}
    for entry in entries:
        result[entry[0]] = entry[1].strip()
    return result

def parse_number(string):
    return int(re.sub(r',', '', string))

def indent(n, string):
    return re.sub(r'^', ' ' * n, string, 0, re.MULTILINE)

if __name__ == '__main__':
    main()
