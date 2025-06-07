#!/usr/bin/env python3

import argparse
import io
import os
import zipfile

import PIL.Image, PIL.ImageDraw

def main():
    p = argparse.ArgumentParser()

    p.add_argument('gtfs', type=os.path.realpath, help='Path to gtfs directory')
    p.add_argument('output', help='Image file to save')
    p.add_argument('--width', type=int, default=800)

    args = p.parse_args()

    draw_shapes(args)

def draw_shapes(args):
    with open_file(args, 'shapes.txt') as shapefile:
        shapefile.readline()
        _, (lat, lon), _ = parse_shape_line(shapefile.readline())
        minlat = lat
        maxlat = lat
        minlon = lon
        maxlon = lon
        for line in shapefile:
            _, (lat, lon), _ = parse_shape_line(line)
            if lat < minlat:
                minlat = lat
            if lat > maxlat:
                maxlat = lat
            if lon < minlon:
                minlon = lon
            if lon > maxlon:
                maxlon = lon
        shapefile.seek(0)
        shapefile.readline()
        width = args.width
        height = int(args.width * (maxlon - minlon) / (maxlat - minlat))

        image = PIL.Image.new('RGB', (width, height), color=(255,255,255))
        draw = PIL.ImageDraw.Draw(image)
        lastid = None
        px = None
        py = None
        for line in shapefile:
            id, (lat, lon), _ = parse_shape_line(line)
            x = int((lat - minlat) * width / (maxlat - minlat))
            y = int((lon - minlon) * width / (maxlon - minlon))
            if id == lastid:
                draw.line((px, py, x, y), fill=128)
            px = x
            py = y
            lastid = id

    image.save(args.output)

def parse_shape_line(line):
    parts = line.rstrip('\n').split(',')
    # ID, (lat, lon), seqnum
    return parts[0], (float(parts[1]), float(parts[2])), int(parts[3])

def open_file(args, name):
    if os.path.isdir(args.gtfs):
        return open(os.path.join(args.gtfs, name), encoding='utf-8')
    elif zipfile.is_zipfile(args.gtfs):
        return io.TextIOWrapper(zipfile.ZipFile(args.gtfs).open(name), encoding='utf-8')
    

if __name__ == '__main__':
    main()

