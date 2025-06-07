#!/usr/bin/env python3

import argparse
import io
import os
import zipfile
import subprocess

import PIL.Image, PIL.ImageDraw

def main():
    p = argparse.ArgumentParser()

    p.add_argument('gtfs', type=os.path.realpath, nargs='+', help='Path to gtfs directory')
    p.add_argument('output', help='Image file to save')
    p.add_argument('--maxdim', type=int, default=1000)
    p.add_argument('--color', action='store_true')
    p.add_argument('--open', action='store_true')

    args = p.parse_args()

    bounding_box = None
    for gtfs in args.gtfs:
        bounding_box = get_bounding_box(gtfs, bounding_box)

    image = make_image(args.maxdim, bounding_box)

    for gtfs in args.gtfs:
        if args.color:
            colors = get_colors(gtfs)
        else:
            colors = {}
        draw_gtfs(gtfs, bounding_box, image, colors)

    image.save(args.output)

    if args.open:
        subprocess.Popen(['feh', args.output])

def get_colors(gtfs):
    with open_file(gtfs, 'routes.txt') as routes:
        route_colors = {}
        for line in routes:
            items = [stripquote(item) for item in line.rstrip('\n').split(',')]
            if len(items) > 7 and items[7]:
                if len(items[7]) == 6:
                    route_colors[items[0]] = items[7]
    shape_colors = {}
    with open_file(gtfs, 'trips.txt') as trips:
        for line in trips:
            items = [stripquote(item) for item in line.rstrip('\n').split(',')]
            if len(items) > 7 and items[7] and items[0] in route_colors:
                shape_colors[items[7]] = '#' + route_colors[items[0]]
    return shape_colors

def stripquote(item):
    if item and item[0] == '"' and item[-1] == '"':
        return item[1:-1]
    else:
        return item

def get_bounding_box(gtfs, bounding_box=None):
    with open_file(gtfs, 'shapes.txt') as shapefile:
        shapefile.readline()
        if bounding_box is not None:
            minlat = bounding_box[0]
            maxlat = bounding_box[1]
            minlon = bounding_box[2]
            maxlon = bounding_box[3]
        else:
            _, (lat, lon) = parse_shape_line(shapefile.readline())
            minlat = lat
            maxlat = lat
            minlon = lon
            maxlon = lon
        for line in shapefile:
            _, (lat, lon) = parse_shape_line(line)
            if lat < minlat:
                minlat = lat
            if lat > maxlat:
                maxlat = lat
            if lon < minlon:
                minlon = lon
            if lon > maxlon:
                maxlon = lon
    return (minlat, maxlat, minlon, maxlon)

def make_image(maxdim, bounding_box):
    minlat = bounding_box[0]
    maxlat = bounding_box[1]
    minlon = bounding_box[2]
    maxlon = bounding_box[3]

    width = maxdim
    height = int((width-10) * (maxlon - minlon) / (maxlat - minlat))+10

    if height > width:
        height = maxdim
        width = int((height-10) * (maxlat - minlat) / (maxlon - minlon))+10

    image = PIL.Image.new('RGB', (width, height), color=(255,255,255))

    return image

def draw_gtfs(gtfs, bounding_box, image, colors):
    minlat = bounding_box[0]
    maxlat = bounding_box[1]
    minlon = bounding_box[2]
    maxlon = bounding_box[3]
    with open_file(gtfs, 'shapes.txt') as shapefile:
        draw = PIL.ImageDraw.Draw(image)
        lastid = None
        px = None
        py = None
        shapefile.readline() # CSV header
        for line in shapefile:
            id, (lat, lon) = parse_shape_line(line)
            x = int((lat - minlat) * (image.width-10) / (maxlat - minlat))+5
            y = int((lon - minlon) * (image.height-10) / (maxlon - minlon))+5
            if id == lastid:
                draw.line((px, py, x, y), fill=colors.get(id, '#000000'))
            px = x
            py = y
            lastid = id

def parse_shape_line(line):
    parts = line.rstrip('\n').split(',')
    # ID, (lat, lon), seqnum
    return parts[0], (float(stripquote(parts[2])), -float(stripquote(parts[1])))

def open_file(gtfs, name):
    if os.path.isdir(gtfs):
        return open(os.path.join(gtfs, name), encoding='utf-8')
    elif zipfile.is_zipfile(gtfs):
        return io.TextIOWrapper(zipfile.ZipFile(gtfs).open(name), encoding='utf-8')

if __name__ == '__main__':
    main()

